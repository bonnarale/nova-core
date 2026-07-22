"""Simple in-memory event bus for task state changes."""

import asyncio
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

EventListener = Callable[[str, dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._listeners: dict[str, list[EventListener]] = {}

    def on(self, event_type: str, listener: EventListener) -> None:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)
        logger.debug("EventBus: listener registered for '%s'", event_type)

    def off(self, event_type: str, listener: EventListener) -> None:
        if event_type in self._listeners:
            self._listeners[event_type] = [
                l for l in self._listeners[event_type] if l is not listener
            ]

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        logger.info("EventBus: %s %s", event_type, data.get("task_id", ""))
        listeners = self._listeners.get(event_type, [])
        for listener in listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event_type, data)
                else:
                    listener(event_type, data)
            except Exception:
                logger.exception("EventBus listener failed for '%s'", event_type)
