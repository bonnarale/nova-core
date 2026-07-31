"""Observability events — lifecycle event tracking for observability subsystem."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4


class ObservabilityEvent:
    """A single observability lifecycle event."""

    def __init__(
        self,
        event_type: str,
        source: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.event_id = str(uuid4())
        self.event_type = event_type
        self.source = source
        self.data = data or {}
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class ObservabilityEventBus:
    """In-memory event bus for observability events."""

    def __init__(self, max_events: int = 1000) -> None:
        self._max_events = max_events
        self._events: list[ObservabilityEvent] = []
        self._handlers: dict[str, list[Any]] = {}

    @property
    def event_count(self) -> int:
        return len(self._events)

    def publish(self, event_type: str, source: str, data: dict[str, Any] | None = None) -> ObservabilityEvent:
        event = ObservabilityEvent(event_type=event_type, source=source, data=data)
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass
        return event

    def subscribe(self, event_type: str, handler: Any) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Any) -> bool:
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                return True
            except ValueError:
                pass
        return False

    def get_events(self, event_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        events = self._events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [e.to_dict() for e in events[-limit:]]

    def clear(self) -> int:
        count = len(self._events)
        self._events.clear()
        return count

    def to_dict(self, limit: int = 100) -> dict[str, Any]:
        events = self.get_events(limit=limit)
        return {"events": events, "total": len(self._events)}
