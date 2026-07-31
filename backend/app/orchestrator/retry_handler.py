"""RetryHandler — retries failed tasks with exponential backoff.

Subscribes to `task.failed` events via InMemoryEventBus. When a task fails
with a retryable reason (agent_error, timeout), increments retry_count and
re-queues after an exponential backoff delay. When retries are exhausted,
marks the task as FAILED permanently and emits `task.retry_exhausted`.

Configuration:
- Default max retries: 3 (override via NOVA_TASK_MAX_RETRIES env var)
- Backoff formula: min(30 * 2^retry_count, 120) seconds
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import os
from typing import Any

from app.db.task_repository import TaskRepository
from app.events.bus import InMemoryEventBus
from app.events.schemas import Event

logger = logging.getLogger(__name__)

# Failure reasons that trigger retry
_RETRYABLE_REASONS = frozenset({"agent_error", "timeout", "unknown"})
_NON_RETRYABLE_REASONS = frozenset({"validation_error", "cancelled", "dependency_failed"})

# Backoff parameters
_BASE_DELAY = 30  # seconds
_MAX_DELAY = 120  # seconds cap


class RetryHandler:
    """Handles task retry logic with exponential backoff.

    Subscribes to task.failed events and decides whether to retry the task
    or mark it as permanently failed.
    """

    def __init__(
        self,
        bus: InMemoryEventBus,
        task_repo: TaskRepository,
        default_max_retries: int | None = None,
    ) -> None:
        self._bus = bus
        self._repo = task_repo
        self._default_max_retries = default_max_retries or int(
            os.environ.get("NOVA_TASK_MAX_RETRIES", "3")
        )

    async def subscribe_to(self) -> None:
        """Register as event listener on the bus for task.failed events."""
        await self._bus.subscribe("task.failed", self._handle_failure)
        logger.info("RetryHandler: subscribed to task.failed (max_retries=%d)", self._default_max_retries)

    async def _handle_failure(self, event: Event) -> None:
        """Handle task.failed event. Decide whether to retry or mark FAILED."""
        try:
            await self.handle_failure(event)
        except Exception:
            logger.exception("RetryHandler: error handling task.failed for %s", event.aggregate_id)

    async def handle_failure(self, event: Event) -> None:
        """Process a task failure event.

        Args:
            event: The task.failed event from InMemoryEventBus
        """
        task_id_str = event.aggregate_id
        if not task_id_str:
            logger.warning("RetryHandler: task.failed event with no task_id")
            return

        from uuid import UUID

        task_id = UUID(task_id_str)
        task = await self._repo.get(task_id)
        if task is None:
            logger.warning("RetryHandler: task %s not found", task_id_str)
            return

        # Extract retry_count and failure reason from event payload
        payload = event.payload if isinstance(event.payload, dict) else {}
        failure_reason = payload.get("failure_reason", "unknown")
        retry_count = self._extract_retry_count(task)
        max_retries = self._get_max_retries(task)

        logger.info(
            "RetryHandler: task %s failed (reason=%s, retry_count=%d/%d)",
            task_id_str, failure_reason, retry_count, max_retries,
        )

        # Check if failure is retryable
        if failure_reason in _NON_RETRYABLE_REASONS:
            logger.info(
                "RetryHandler: task %s failure reason '%s' is not retryable",
                task_id_str, failure_reason,
            )
            return

        # Check retry limit
        if retry_count >= max_retries:
            logger.info(
                "RetryHandler: task %s retry exhausted (%d/%d), marking FAILED",
                task_id_str, retry_count, max_retries,
            )
            await self._mark_failed_permanently(task_id, task, retry_count)
            return

        # Retry: increment count, emit retry event, schedule re-queue
        new_retry_count = retry_count + 1
        await self._increment_retry_count(task, new_retry_count)

        backoff_delay = self._calculate_backoff(retry_count)
        logger.info(
            "RetryHandler: retrying task %s (attempt %d/%d, delay=%ds)",
            task_id_str, new_retry_count, max_retries, backoff_delay,
        )

        # Emit retry event
        await self._bus.publish(Event(
            event_type="task.retrying",
            aggregate_id=task_id_str,
            payload={
                "task_id": task_id_str,
                "retry_count": new_retry_count,
                "max_retries": max_retries,
                "delay_seconds": backoff_delay,
                "failure_reason": failure_reason,
            },
            source="retry_handler",
        ))

        # Schedule delayed re-queue
        requeue_event = Event(
            event_type="task.created",
            aggregate_id=task_id_str,
            payload={
                "task_id": task_id_str,
                "retry": True,
                "retry_count": new_retry_count,
            },
            source="retry_handler",
        )
        await self._bus.publish_delayed(requeue_event, backoff_delay)

    def _extract_retry_count(self, task) -> int:
        """Extract retry_count from task's events JSON field."""
        events = task.events or []
        for event_data in reversed(events):
            if isinstance(event_data, dict) and "retry_count" in event_data:
                return event_data["retry_count"]
        return 0

    def _get_max_retries(self, task) -> int:
        """Get max_retries for a task. Check task events, fall back to default."""
        events = task.events or []
        for event_data in reversed(events):
            if isinstance(event_data, dict) and "max_retries" in event_data:
                return event_data["max_retries"]
        return self._default_max_retries

    async def _increment_retry_count(self, task, new_count: int) -> None:
        """Persist incremented retry_count in task's events field."""
        from uuid import UUID

        task_id = UUID(str(task.id)) if isinstance(task.id, str) else task.id
        events = list(task.events or [])
        events.append({
            "type": "task.retry_incremented",
            "retry_count": new_count,
            "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        })
        await self._repo.update(task_id, events=events)

    async def _mark_failed_permanently(
        self, task_id, task, retry_count: int
    ) -> None:
        """Mark task as permanently FAILED and emit retry_exhausted event."""
        from uuid import UUID

        uid = UUID(str(task_id)) if not isinstance(task_id, UUID) else task_id
        events = list(task.events or [])
        events.append({
            "type": "task.retry_exhausted",
            "retry_count": retry_count,
            "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        })
        await self._repo.update(uid, status="FAILED", events=events)

        await self._bus.publish(Event(
            event_type="task.retry_exhausted",
            aggregate_id=str(task_id),
            payload={
                "task_id": str(task_id),
                "retry_count": retry_count,
                "status": "FAILED",
            },
            source="retry_handler",
        ))

    @staticmethod
    def _calculate_backoff(retry_count: int) -> int:
        """Calculate exponential backoff delay: min(30 * 2^retry_count, 120)."""
        return min(_BASE_DELAY * (2 ** retry_count), _MAX_DELAY)
