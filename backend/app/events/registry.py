"""Event handler registry — auto-registers handlers by event type."""

from __future__ import annotations

import logging
from typing import Any

from app.events.base import EventHandler

logger = logging.getLogger(__name__)


class EventHandlerRegistry:
    """Registry for event handlers, indexed by event type."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._handler_map: dict[str, EventHandler] = {}

    def register(self, handler: EventHandler) -> None:
        et = handler.event_type
        if et not in self._handlers:
            self._handlers[et] = []
        self._handlers[et].append(handler)
        self._handler_map[handler.__class__.__name__] = handler
        logger.debug("Registered handler %s for event_type=%s", handler.__class__.__name__, et)

    def unregister(self, handler: EventHandler) -> bool:
        et = handler.event_type
        handlers = self._handlers.get(et, [])
        if handler in handlers:
            handlers.remove(handler)
            self._handler_map.pop(handler.__class__.__name__, None)
            return True
        return False

    def get_handlers(self, event_type: str) -> list[EventHandler]:
        return list(self._handlers.get(event_type, []))

    def get_handler(self, name: str) -> EventHandler | None:
        return self._handler_map.get(name)

    def get_all_handlers(self) -> dict[str, list[EventHandler]]:
        return dict(self._handlers)

    def get_registered_types(self) -> list[str]:
        return list(self._handlers.keys())

    def get_handler_count(self) -> int:
        return sum(len(hs) for hs in self._handlers.values())

    def clear(self) -> int:
        count = self.get_handler_count()
        self._handlers.clear()
        self._handler_map.clear()
        return count

    def has_handlers(self, event_type: str) -> bool:
        return bool(self._handlers.get(event_type))
