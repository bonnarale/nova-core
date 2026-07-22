"""Event types and event bus for workflow lifecycle events."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from app.workflows.models import WorkflowEvent, WorkflowEventType

logger = logging.getLogger(__name__)

EventHandler = Callable[[WorkflowEvent], Any]


class WorkflowEventBus:
    """Simple in-memory event bus for workflow lifecycle events."""

    def __init__(self) -> None:
        self._subscribers: dict[WorkflowEventType, list[EventHandler]] = {}
        self._events: list[WorkflowEvent] = []

    def subscribe(self, event_type: WorkflowEventType, handler: EventHandler) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: WorkflowEventType, handler: EventHandler) -> None:
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(
        self,
        event_type: WorkflowEventType,
        execution_id: str,
        step_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> WorkflowEvent:
        event = WorkflowEvent(
            id=str(uuid4()),
            execution_id=execution_id,
            event_type=event_type,
            step_id=step_id,
            payload=payload or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._events.append(event)

        for handler in self._subscribers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                logger.exception("Event handler failed for %s", event_type.value)

        return event

    def get_events(self, execution_id: str | None = None) -> list[WorkflowEvent]:
        if execution_id:
            return [e for e in self._events if e.execution_id == execution_id]
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()
