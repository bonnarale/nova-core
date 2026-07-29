"""Event publisher — high-level publish API wrapping the event bus."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.events.base import EventBus as EventBusABC, EventMiddleware
from app.events.schemas import Event, EventPriority, EventStatus

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publishes events through the bus with middleware support."""

    def __init__(
        self,
        bus: EventBusABC,
        middlewares: list[EventMiddleware] | None = None,
        default_source: str = "",
    ) -> None:
        self._bus = bus
        self._middlewares: list[EventMiddleware] = sorted(
            middlewares or [], key=lambda m: m.priority
        )
        self._default_source = default_source

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        aggregate_id: str = "",
        aggregate_type: str = "",
        source: str = "",
        correlation_id: str = "",
        causation_id: str = "",
        session_id: str = "",
        user_id: str = "",
        priority: EventPriority = EventPriority.NORMAL,
        metadata: dict[str, Any] | None = None,
    ) -> Event:
        event = Event(
            event_id=str(uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            source=source or self._default_source,
            timestamp=datetime.now(timezone.utc),
            correlation_id=correlation_id,
            causation_id=causation_id,
            session_id=session_id,
            user_id=user_id,
            payload=payload or {},
            metadata=metadata or {},
            priority=priority,
            status=EventStatus.PENDING,
        )
        return await self.publish_event(event)

    async def publish_event(self, event: Event) -> Event:
        for mw in self._middlewares:
            try:
                event = await mw.before_publish(event)
            except Exception as e:
                logger.error("Middleware %s before_publish failed: %s", mw.name, e)
                raise
        try:
            result = await self._bus.publish(event)
        except Exception as e:
            for mw in self._middlewares:
                try:
                    await mw.on_error(event, e)
                except Exception:
                    logger.exception("Middleware %s on_error failed", mw.name)
            raise
        for mw in self._middlewares:
            try:
                await mw.after_publish(event, result)
            except Exception as e:
                logger.error("Middleware %s after_publish failed: %s", mw.name, e)
        return result

    async def publish_many(self, events: list[Event]) -> list[Event]:
        results: list[Event] = []
        for event in events:
            results.append(await self.publish_event(event))
        return results

    async def broadcast(self, event: Event) -> Event:
        for mw in self._middlewares:
            try:
                event = await mw.before_publish(event)
            except Exception as e:
                logger.error("Middleware %s before_publish failed: %s", mw.name, e)
                raise
        result = await self._bus.broadcast(event)
        for mw in self._middlewares:
            try:
                await mw.after_publish(event, result)
            except Exception:
                pass
        return result
