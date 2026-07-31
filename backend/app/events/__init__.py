"""Event system — async event-driven architecture for NOVA CORE."""

from app.events.base import (
    EventHandler,
    EventMiddleware,
    EventPersistence,
    EventPublisher as EventPublisherABC,
    EventSerializer,
    EventSubscriber as EventSubscriberABC,
    EventBus as EventBusABC,
)
from app.events.bus import InMemoryEventBus
from app.events.dispatcher import EventDispatcher
from app.events.factory import EventSystemFactory
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
from app.events.persistence import InMemoryEventPersistence, PostgresEventPersistence
from app.events.publisher import EventPublisher
from app.events.replay import EventReplay
from app.events.schemas import (
    DeadLetterEvent,
    DelayedEvent,
    DispatchType,
    Event,
    EventFilter,
    EventPriority,
    EventResponse,
    EventStatus,
    EventStatistics,
    EventType,
    EventsListResponse,
    PublishRequest,
    ReplayRequest,
    ReplayResult,
    ScheduledEvent,
    Subscription,
)
from app.events.serializer import JSONEventSerializer
from app.events.subscriber import EventSubscriber
from app.events.tracing import EventTracer, get_event_tracer

__all__ = [
    "EventBusABC",
    "EventPublisherABC",
    "EventSubscriberABC",
    "EventHandler",
    "EventMiddleware",
    "EventPersistence",
    "EventSerializer",
    "InMemoryEventBus",
    "EventDispatcher",
    "EventPublisher",
    "EventSubscriber",
    "EventFilterEngine",
    "EventReplay",
    "JSONEventSerializer",
    "EventLifecycle",
    "EventLifecycleState",
    "EventMetrics",
    "get_event_metrics",
    "EventTracer",
    "get_event_tracer",
    "InMemoryEventPersistence",
    "PostgresEventPersistence",
    "EventSystemFactory",
    "LoggingMiddleware",
    "TracingMiddleware",
    "MetricsMiddleware",
    "ValidationMiddleware",
    "RetryMiddleware",
    "AuthorizationMiddleware",
    "TransformationMiddleware",
    "DEFAULT_HANDLERS",
    "Event",
    "EventType",
    "EventPriority",
    "EventStatus",
    "DispatchType",
    "EventFilter",
    "Subscription",
    "ScheduledEvent",
    "DelayedEvent",
    "DeadLetterEvent",
    "ReplayRequest",
    "ReplayResult",
    "PublishRequest",
    "EventResponse",
    "EventsListResponse",
    "EventStatistics",
]
