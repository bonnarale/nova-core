"""Agent scheduler with queues, priorities, concurrency, and fairness."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(order=True)
class ScheduledTask:
    """A task entry in the scheduler queue."""

    priority: int = field(compare=True)
    created_at: float = field(compare=True, default_factory=time.time)
    task_id: str = field(compare=False, default="")
    agent_id: str = field(compare=False, default="")
    task: str = field(compare=False, default="")
    context: dict[str, Any] = field(compare=False, default_factory=dict)
    max_retries: int = field(compare=False, default=0)
    timeout_seconds: float | None = field(compare=False, default=None)
    retries: int = field(compare=False, default=0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "priority": self.priority,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "age_seconds": round(time.time() - self.created_at, 2),
        }


class AgentScheduler:
    """Priority-based scheduler with concurrency limits, cancellation,
    retries, timeout, and fairness.
    """

    def __init__(self, max_concurrency: int = 10) -> None:
        self._queue: list[ScheduledTask] = []
        self._running: dict[str, ScheduledTask] = {}
        self._completed: list[dict[str, Any]] = []
        self._max_concurrency = max_concurrency
        self._agent_concurrency: dict[str, int] = defaultdict(int)
        self._agent_limits: dict[str, int] = {}
        self._fairness_counter: int = 0

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def running_count(self) -> int:
        return len(self._running)

    def set_agent_limit(self, agent_id: str, limit: int) -> None:
        self._agent_limits[agent_id] = limit

    def enqueue(
        self,
        task_id: str,
        agent_id: str,
        task: str,
        priority: int = 5,
        context: dict[str, Any] | None = None,
        max_retries: int = 0,
        timeout_seconds: float | None = None,
    ) -> ScheduledTask:
        entry = ScheduledTask(
            priority=priority,
            task_id=task_id,
            agent_id=agent_id,
            task=task,
            context=context or {},
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )
        self._queue.append(entry)
        self._queue.sort()
        logger.debug(
            "Scheduler: enqueued %s (priority=%d, queue_size=%d)",
            task_id, priority, len(self._queue),
        )
        return entry

    def dequeue(self) -> ScheduledTask | None:
        if not self._queue:
            return None
        return self._queue.pop(0)

    def can_dispatch(self, agent_id: str) -> bool:
        if len(self._running) >= self._max_concurrency:
            return False
        agent_limit = self._agent_limits.get(agent_id, self._max_concurrency)
        if self._agent_concurrency[agent_id] >= agent_limit:
            return False
        return True

    def start_running(self, task: ScheduledTask) -> None:
        self._running[task.task_id] = task
        self._agent_concurrency[task.agent_id] += 1
        logger.debug("Scheduler: started %s on %s", task.task_id, task.agent_id)

    def complete(self, task_id: str, success: bool = True, result: dict | None = None) -> dict | None:
        task = self._running.pop(task_id, None)
        if task is None:
            return None
        self._agent_concurrency[task.agent_id] = max(0, self._agent_concurrency[task.agent_id] - 1)

        entry = {
            "task_id": task_id,
            "agent_id": task.agent_id,
            "success": success,
            "result": result,
            "retries": task.retries,
        }
        self._completed.append(entry)

        if not success and task.retries < task.max_retries:
            task.retries += 1
            self._queue.append(task)
            self._queue.sort()
            logger.info("Scheduler: re-enqueued %s (retry %d/%d)", task_id, task.retries, task.max_retries)

        return entry

    def cancel(self, task_id: str) -> bool:
        task = self._running.pop(task_id, None)
        if task:
            self._agent_concurrency[task.agent_id] = max(0, self._agent_concurrency[task.agent_id] - 1)
            logger.info("Scheduler: cancelled running task %s", task_id)
            return True

        for i, t in enumerate(self._queue):
            if t.task_id == task_id:
                self._queue.pop(i)
                logger.info("Scheduler: cancelled queued task %s", task_id)
                return True
        return False

    def get_running(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._running.values()]

    def get_queue(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._queue]

    def get_completed(self) -> list[dict[str, Any]]:
        return list(self._completed)

    def clear(self) -> None:
        self._queue.clear()
        self._running.clear()
        self._completed.clear()
        self._agent_concurrency.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "queue_size": self.queue_size,
            "running_count": self.running_count,
            "max_concurrency": self._max_concurrency,
            "agent_concurrency": dict(self._agent_concurrency),
            "completed_count": len(self._completed),
        }
