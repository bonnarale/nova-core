"""Graph event bus for publishing and subscribing to graph changes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine
from uuid import uuid4

from app.knowledge_graph.models import GraphEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[GraphEvent], Coroutine[Any, Any, None]]


class GraphEventBus:
    """Simple pub/sub event bus for graph events."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)
        logger.debug("Subscribed handler for event type '%s'", event_type)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        hs = self._handlers.get(event_type, [])
        if handler in hs:
            hs.remove(handler)
            logger.debug("Unsubscribed handler for event type '%s'", event_type)

    async def publish(
        self,
        event_type: str,
        entity_id: str | None = None,
        relationship_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event = GraphEvent(
            id=str(uuid4()),
            event_type=event_type,
            entity_id=entity_id,
            relationship_id=relationship_id,
            payload=payload or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        logger.info("Publishing event: %s (%s)", event_type, event.id)

        for handler in self._handlers.get(event_type, []):
            try:
                await handler(event)
            except Exception:
                logger.exception("Handler failed for event %s", event_type)

        for handler in self._handlers.get("*", []):
            try:
                await handler(event)
            except Exception:
                logger.exception("Wildcard handler failed for event %s", event_type)
