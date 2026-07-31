"""TimeoutHandler — detects and recovers from stuck tasks.

Subscribes to state transition events via InMemoryEventBus. When a task
transitions to RUNNING or has a state transition while running, checks if
the task has exceeded its configured timeout. If exceeded, marks the task
as FAILED and emits a `task.timeout` event.

Configuration:
- Default timeout: 300 seconds (override via NOVA_TASK_TIMEOUT_SECONDS env var)
- Per-task timeout: via task's timeout_seconds parameter
"""

from __future__ import annotations

import datetime
import logging
import os
from typing import Any

from app.db.task_repository import TaskRepository
from app.events.bus import InMemoryEventBus
from app.events.schemas import Event

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 300  # seconds


class TimeoutHandler:
    """Handles task timeout detection on state transitions.

    Subscribes to task.started and state transition events. Checks if a task
    has been running longer than its configured timeout and marks it FAILED
    if exceeded.
    """

    def __init__(
        self,
        bus: InMemoryEventBus,
        task_repo: TaskRepository,
        default_timeout: int | None = None,
    ) -> None:
        self._bus = bus
        self._repo = task_repo
        self._default_timeout = default_timeout or int(
            os.environ.get("NOVA_TASK_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT))
        )

    async def subscribe_to(self) -> None:
        """Register as event listener on the bus for relevant events."""
        await self._bus.subscribe("task.started", self._handle_started)
        await self._bus.subscribe("task.running", self._handle_started)
        await self._bus.subscribe("task.step_advanced", self._handle_transition)
        await self._bus.subscribe("task.retrying", self._handle_transition)
        logger.info(
            "TimeoutHandler: subscribed (default_timeout=%ds)", self._default_timeout
        )

    async def _handle_started(self, event: Event) -> None:
        """Handle task.started / task.running events — record start time and check timeout."""
        try:
            await self.check_timeout(event)
        except Exception:
            logger.exception(
                "TimeoutHandler: error checking timeout for %s", event.aggregate_id
            )

    async def _handle_transition(self, event: Event) -> None:
        """Handle state transition events — check if running task has timed out."""
        try:
            await self.check_timeout(event)
        except Exception:
            logger.exception(
                "TimeoutHandler: error on transition for %s", event.aggregate_id
            )

    async def check_timeout(self, event: Event) -> None:
        """Check if a task has exceeded its timeout.

        Args:
            event: The event that triggered the check
        """
        task_id_str = event.aggregate_id
        if not task_id_str:
            return

        from uuid import UUID

        task_id = UUID(task_id_str)
        task = await self._repo.get(task_id)
        if task is None:
            return

        # Only check tasks that are RUNNING
        if task.status != "RUNNING":
            return

        # Get timeout value (per-task or default)
        timeout_seconds = self._get_timeout(task)

        # Get started_at timestamp
        if task.started_at is None:
            return

        # Parse started_at
        started_at = task.started_at
        if isinstance(started_at, str):
            started_at = datetime.datetime.fromisoformat(started_at)

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        # Ensure started_at is timezone-aware
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=datetime.timezone.utc)

        elapsed = (now - started_at).total_seconds()

        if elapsed > timeout_seconds:
            logger.warning(
                "TimeoutHandler: task %s exceeded timeout (%.0fs > %ds)",
                task_id_str, elapsed, timeout_seconds,
            )
            await self._mark_timed_out(task_id, task, timeout_seconds, elapsed, event.event_type)
        else:
            logger.debug(
                "TimeoutHandler: task %s within timeout (%.0fs / %ds)",
                task_id_str, elapsed, timeout_seconds,
            )

    def _get_timeout(self, task) -> int:
        """Get timeout for a task. Check task events, fall back to default."""
        events = task.events or []
        for event_data in reversed(events):
            if isinstance(event_data, dict) and "timeout_seconds" in event_data:
                return event_data["timeout_seconds"]
        return self._default_timeout

    async def _mark_timed_out(
        self,
        task_id,
        task,
        timeout_seconds: int,
        actual_duration: float,
        triggering_transition: str,
    ) -> None:
        """Mark task as FAILED due to timeout and emit timeout event."""
        from uuid import UUID

        uid = UUID(str(task_id)) if not isinstance(task_id, UUID) else task_id
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        events = list(task.events or [])
        events.append({
            "type": "task.timeout",
            "timeout_seconds": timeout_seconds,
            "actual_duration": actual_duration,
            "timestamp": now.isoformat(),
        })

        await self._repo.update(uid, status="FAILED", events=events)

        await self._bus.publish(Event(
            event_type="task.timeout",
            aggregate_id=str(task_id),
            payload={
                "task_id": str(task_id),
                "timeout_seconds": timeout_seconds,
                "actual_duration": actual_duration,
                "triggering_transition": triggering_transition,
                "status": "FAILED",
            },
            source="timeout_handler",
        ))
