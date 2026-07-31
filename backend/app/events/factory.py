"""Event system factory — wires all components together."""

from __future__ import annotations

import logging
from typing import Any

from app.events.base import EventMiddleware, EventPersistence
from app.events.bus import InMemoryEventBus
from app.events.dispatcher import EventDispatcher
from app.events.filters import EventFilterEngine
from app.events.handlers import DEFAULT_HANDLERS
from app.events.lifecycle import EventLifecycle, EventLifecycleState
from app.events.metrics import EventMetrics, get_event_metrics
from app.events.middleware import (
    AuthorizationMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    RetryMiddleware,
    TracingMiddleware,
    TransformationMiddleware,
    ValidationMiddleware,
)
from app.events.persistence import InMemoryEventPersistence
from app.events.publisher import EventPublisher
from app.events.replay import EventReplay
from app.events.serializer import JSONEventSerializer
from app.events.subscriber import EventSubscriber
from app.events.tracing import EventTracer, get_event_tracer

logger = logging.getLogger(__name__)


class EventSystemFactory:
    """Creates and wires the complete event system."""

    def __init__(
        self,
        persistence: EventPersistence | None = None,
        middlewares: list[EventMiddleware] | None = None,
        default_source: str = "nova-core",
        max_concurrency: int = 10,
        max_retries: int = 3,
    ) -> None:
        self._persistence = persistence or InMemoryEventPersistence()
        self._middlewares = middlewares
        self._default_source = default_source
        self._max_concurrency = max_concurrency
        self._max_retries = max_retries

    def create_bus(self) -> InMemoryEventBus:
        return InMemoryEventBus(
            persistence=self._persistence,
            max_retries=self._max_retries,
        )

    def create_dispatcher(self) -> EventDispatcher:
        return EventDispatcher(max_concurrency=self._max_concurrency)

    def create_publisher(
        self,
        bus: InMemoryEventBus,
        middlewares: list[EventMiddleware] | None = None,
    ) -> EventPublisher:
        return EventPublisher(
            bus=bus,
            middlewares=middlewares or self._default_middlewares(),
            default_source=self._default_source,
        )

    def create_subscriber(self, bus: InMemoryEventBus) -> EventSubscriber:
        return EventSubscriber(bus=bus)

    def create_replay(self) -> EventReplay:
        return EventReplay(persistence=self._persistence)

    def create_serializer(self) -> JSONEventSerializer:
        return JSONEventSerializer()

    def create_filter_engine(self) -> EventFilterEngine:
        return EventFilterEngine()

    def create_lifecycle(self) -> EventLifecycle:
        return EventLifecycle()

    def _default_middlewares(self) -> list[EventMiddleware]:
        return [
            LoggingMiddleware(),
            TracingMiddleware(),
            MetricsMiddleware(),
            ValidationMiddleware(),
            RetryMiddleware(max_retries=self._max_retries),
        ]

    def register_default_handlers(self, subscriber: EventSubscriber) -> list[str]:
        import asyncio

        sub_ids: list[str] = []
        for handler_cls in DEFAULT_HANDLERS:
            handler = handler_cls()
            loop = asyncio.get_event_loop()
            if loop.is_running():
                task = asyncio.ensure_future(subscriber.subscribe_handler(handler))
                sub_ids.append("")
            else:
                sub_id = loop.run_until_complete(subscriber.subscribe_handler(handler))
                sub_ids.append(sub_id)
        return sub_ids

    def create_system(
        self,
        middlewares: list[EventMiddleware] | None = None,
    ) -> dict[str, Any]:
        bus = self.create_bus()
        dispatcher = self.create_dispatcher()
        publisher = self.create_publisher(bus, middlewares)
        subscriber = self.create_subscriber(bus)
        replay = self.create_replay()
        serializer = self.create_serializer()
        filter_engine = self.create_filter_engine()
        lifecycle = self.create_lifecycle()
        metrics = get_event_metrics()
        tracer = get_event_tracer()

        return {
            "bus": bus,
            "dispatcher": dispatcher,
            "publisher": publisher,
            "subscriber": subscriber,
            "replay": replay,
            "serializer": serializer,
            "filter_engine": filter_engine,
            "lifecycle": lifecycle,
            "metrics": metrics,
            "tracer": tracer,
            "persistence": self._persistence,
        }
