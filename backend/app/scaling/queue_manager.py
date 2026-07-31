"""Queue manager with priority, delayed, retry, and dead-letter queues."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from collections import deque
from typing import Any

from app.scaling.enums import QueuePriority, QueueState
from app.scaling.models import QueueInfo

logger = logging.getLogger(__name__)


class _QueueEntry:
    __slots__ = ("task", "priority", "created_at", "delay_until", "retries", "max_retries")

    def __init__(
        self,
        task: dict[str, Any],
        priority: str = "normal",
        delay: float = 0.0,
        max_retries: int = 3,
    ) -> None:
        self.task = task
        self.priority = priority
        self.created_at = time.time()
        self.delay_until = time.time() + delay if delay > 0 else 0.0
        self.retries = 0
        self.max_retries = max_retries


_PRIORITY_ORDER = {
    QueuePriority.CRITICAL.value: 0,
    QueuePriority.HIGH.value: 1,
    QueuePriority.NORMAL.value: 2,
    QueuePriority.LOW.value: 3,
}


class QueueManager:
    """Manages async queues with priorities, delays, retries, and dead-letter support."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._queues: dict[str, deque[_QueueEntry]] = {}
        self._dead_letter: dict[str, deque[_QueueEntry]] = {}
        self._queue_info: dict[str, QueueInfo] = {}
        self._retry_queue: deque[_QueueEntry] = deque()

    def create_queue(self, name: str, priority: str = "normal") -> QueueInfo:
        with self._lock:
            if name not in self._queues:
                self._queues[name] = deque()
                self._dead_letter[name] = deque()
                self._queue_info[name] = QueueInfo(
                    name=name,
                    state=QueueState.ACTIVE.value,
                    priority=priority,
                )
            return self._queue_info[name]

    async def enqueue(
        self,
        queue_name: str,
        task: dict[str, Any],
        priority: str = "normal",
        delay: float = 0.0,
    ) -> str:
        task_id = task.get("id", str(uuid.uuid4()))
        task_with_id = {**task, "id": task_id}
        entry = _QueueEntry(task_with_id, priority, delay)
        with self._lock:
            if queue_name not in self._queues:
                self.create_queue(queue_name, priority)
            self._queues[queue_name].append(entry)
            self._queue_info[queue_name].depth = len(self._queues[queue_name])
            self._queue_info[queue_name].total_enqueued += 1
        return task_id

    async def dequeue(self, queue_name: str) -> dict[str, Any] | None:
        with self._lock:
            if queue_name not in self._queues:
                return None
            q = self._queues[queue_name]
            now = time.time()

            entries = list(q)
            entries.sort(key=lambda e: _PRIORITY_ORDER.get(e.priority, 2))

            for entry in entries:
                if entry.delay_until > 0 and entry.delay_until > now:
                    continue
                q.remove(entry)
                self._queue_info[queue_name].depth = len(q)
                self._queue_info[queue_name].total_dequeued += 1
                return entry.task
        return None

    async def enqueue_retry(self, queue_name: str, task: dict[str, Any], max_retries: int = 3) -> None:
        entry = _QueueEntry(task, max_retries=max_retries)
        entry.retries = 0
        with self._lock:
            self._retry_queue.append(entry)

    async def process_retries(self, queue_name: str) -> int:
        processed = 0
        with self._lock:
            remaining: deque[_QueueEntry] = deque()
            for entry in self._retry_queue:
                if entry.retries < entry.max_retries:
                    entry.retries += 1
                    if queue_name in self._queues:
                        self._queues[queue_name].append(entry)
                        processed += 1
                else:
                    if queue_name in self._dead_letter:
                        self._dead_letter[queue_name].append(entry)
            self._retry_queue = remaining
        return processed

    async def send_to_dead_letter(self, queue_name: str, task: dict[str, Any]) -> None:
        entry = _QueueEntry(task)
        with self._lock:
            if queue_name not in self._dead_letter:
                self._dead_letter[queue_name] = deque()
            self._dead_letter[queue_name].append(entry)
            if queue_name in self._queue_info:
                self._queue_info[queue_name].total_failed += 1

    async def get_dead_letters(self, queue_name: str) -> list[dict[str, Any]]:
        with self._lock:
            if queue_name not in self._dead_letter:
                return []
            return [e.task for e in self._dead_letter[queue_name]]

    def get_queue_info(self, queue_name: str) -> QueueInfo | None:
        return self._queue_info.get(queue_name)

    def list_queues(self) -> list[dict[str, Any]]:
        with self._lock:
            return [qi.to_dict() for qi in self._queue_info.values()]

    def get_statistics(self) -> dict[str, Any]:
        with self._lock:
            total_depth = sum(qi.depth for qi in self._queue_info.values())
            total_enqueued = sum(qi.total_enqueued for qi in self._queue_info.values())
            total_dequeued = sum(qi.total_dequeued for qi in self._queue_info.values())
            total_failed = sum(qi.total_failed for qi in self._queue_info.values())
            dl_size = sum(len(dq) for dq in self._dead_letter.values())
            return {
                "total_queues": len(self._queues),
                "total_depth": total_depth,
                "total_enqueued": total_enqueued,
                "total_dequeued": total_dequeued,
                "total_failed": total_failed,
                "dead_letter_size": dl_size,
                "retry_queue_size": len(self._retry_queue),
            }
