"""Plugin events — event bus for plugin lifecycle events."""

from __future__ import annotations

import time
import uuid
from typing import Any

from app.plugins.enums import PluginEventType
from app.plugins.models import PluginEvent


class PluginEventBus:
    """Event bus for plugin lifecycle events."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Any]] = {}
        self._events: list[PluginEvent] = []
        self._event_count = 0

    def subscribe(self, event_type: str, handler: Any) -> str:
        sub_id = uuid.uuid4().hex[:12]
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append({"id": sub_id, "handler": handler})
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        for event_type, subs in self._subscribers.items():
            before = len(subs)
            self._subscribers[event_type] = [s for s in subs if s["id"] != subscription_id]
            if len(self._subscribers[event_type]) < before:
                return True
        return False

    def publish(self, event_type: str, plugin_id: str, data: dict[str, Any] | None = None) -> PluginEvent:
        event = PluginEvent(
            event_id=uuid.uuid4().hex[:16],
            event_type=event_type,
            plugin_id=plugin_id,
            timestamp=time.time(),
            data=data or {},
        )
        self._events.append(event)
        self._event_count += 1
        for handler_entry in self._subscribers.get(event_type, []):
            try:
                handler = handler_entry["handler"]
                if callable(handler):
                    handler(event)
            except Exception:
                pass
        return event

    async def publish_async(self, event_type: str, plugin_id: str, data: dict[str, Any] | None = None) -> PluginEvent:
        event = PluginEvent(
            event_id=uuid.uuid4().hex[:16],
            event_type=event_type,
            plugin_id=plugin_id,
            timestamp=time.time(),
            data=data or {},
        )
        self._events.append(event)
        self._event_count += 1
        for handler_entry in self._subscribers.get(event_type, []):
            try:
                handler = handler_entry["handler"]
                if callable(handler):
                    import asyncio
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
            except Exception:
                pass
        return event

    def get_events(self, event_type: str | None = None, limit: int = 100) -> list[PluginEvent]:
        events = self._events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def get_statistics(self) -> dict[str, Any]:
        return {
            "total_events": self._event_count,
            "total_subscribers": sum(len(s) for s in self._subscribers.values()),
            "event_types": list(self._subscribers.keys()),
        }

    def clear(self) -> None:
        self._events.clear()
        self._subscribers.clear()
        self._event_count = 0
