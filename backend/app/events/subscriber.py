"""Event subscriber — high-level subscribe/unsubscribe API wrapping the event bus."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from app.events.base import EventBus as EventBusABC, EventFilter, EventHandler

logger = logging.getLogger(__name__)


class EventSubscriber:
    """Subscribes to events from the bus with filtering and wildcard support."""

    def __init__(self, bus: EventBusABC) -> None:
        self._bus = bus
        self._subscriptions: dict[str, str] = {}

    async def subscribe(
        self,
        event_type: str,
        handler: Any,
        filter_expr: EventFilter | None = None,
    ) -> str:
        sub_id = await self._bus.subscribe(event_type, handler, filter_expr)
        self._subscriptions[sub_id] = event_type
        return sub_id

    async def subscribe_handler(self, handler: EventHandler) -> str:
        return await self.subscribe(handler.event_type, handler)

    async def subscribe_wildcard(
        self,
        handler: Any,
        filter_expr: EventFilter | None = None,
    ) -> str:
        return await self.subscribe("*", handler, filter_expr)

    async def unsubscribe(self, subscription_id: str) -> bool:
        result = await self._bus.unsubscribe(subscription_id)
        self._subscriptions.pop(subscription_id, None)
        return result

    async def get_subscriptions(self) -> list[dict[str, Any]]:
        return [
            {"subscription_id": sid, "event_type": et}
            for sid, et in self._subscriptions.items()
        ]

    @property
    def subscription_count(self) -> int:
        return len(self._subscriptions)
