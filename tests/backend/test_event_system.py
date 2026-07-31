"""Comprehensive tests for the Event System — Chapter 19."""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

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
from app.events.handlers import (
    ConversationCreatedHandler,
    GoalCreatedHandler,
    MessageStoredHandler,
    TaskCompletedHandler,
    TaskCreatedHandler,
    DEFAULT_HANDLERS,
)
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
from app.events.schemas import (
    DeadLetterEvent,
    DelayedEvent,
    DispatchType,
    Event,
    EventFilter,
    EventPriority,
    EventStatus,
    EventType,
    PublishRequest,
    ReplayRequest,
    ScheduledEvent,
    Subscription,
)
from app.events.serializer import JSONEventSerializer
from app.events.subscriber import EventSubscriber
from app.events.tracing import EventTracer, get_event_tracer


# ======================================================================
# Helper
# ======================================================================

def _make_event(event_type: str = "system.event", **kwargs: Any) -> Event:
    return Event(event_type=event_type, **kwargs)


# ======================================================================
# ABCs
# ======================================================================

class TestABCs:
    def test_event_bus_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            EventBusABC()

    def test_event_publisher_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            EventPublisherABC()

    def test_event_subscriber_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            EventSubscriberABC()

    def test_event_handler_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            EventHandler()

    def test_event_middleware_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            EventMiddleware()

    def test_event_persistence_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            EventPersistence()

    def test_event_serializer_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            EventSerializer()


# ======================================================================
# Event Model
# ======================================================================

class TestEventModel:
    def test_default_construction(self) -> None:
        event = Event()
        assert event.event_id
        assert event.event_type == ""
        assert event.version == 1
        assert event.priority == EventPriority.NORMAL
        assert event.status == EventStatus.PENDING
        assert event.retry_count == 0
        assert event.max_retries == 3

    def test_event_with_type(self) -> None:
        event = Event(event_type="task.created", aggregate_id="agg-1")
        assert event.event_type == "task.created"
        assert event.aggregate_id == "agg-1"

    def test_event_timestamp_is_utc(self) -> None:
        event = Event()
        assert event.timestamp.tzinfo == timezone.utc

    def test_event_payload(self) -> None:
        event = Event(payload={"key": "value", "count": 42})
        assert event.payload["key"] == "value"
        assert event.payload["count"] == 42

    def test_event_metadata(self) -> None:
        event = Event(metadata={"source": "test", "version": "1.0"})
        assert event.metadata["source"] == "test"

    def test_event_correlation_chain(self) -> None:
        event = Event(correlation_id="corr-1", causation_id="cause-1")
        assert event.correlation_id == "corr-1"
        assert event.causation_id == "cause-1"

    def test_event_session_and_user(self) -> None:
        event = Event(session_id="sess-1", user_id="user-1")
        assert event.session_id == "sess-1"
        assert event.user_id == "user-1"


# ======================================================================
# Schemas
# ======================================================================

class TestSchemas:
    def test_event_type_enum(self) -> None:
        assert EventType.CONVERSATION_CREATED.value == "conversation.created"
        assert EventType.TASK_COMPLETED.value == "task.completed"
        assert EventType.VECTOR_STORED.value == "vector.stored"

    def test_event_priority_enum(self) -> None:
        assert EventPriority.LOW.value == "low"
        assert EventPriority.CRITICAL.value == "critical"

    def test_event_status_enum(self) -> None:
        assert EventStatus.PENDING.value == "pending"
        assert EventStatus.DEAD_LETTER.value == "dead_letter"

    def test_publish_request(self) -> None:
        req = PublishRequest(event_type="task.created")
        assert req.event_type == "task.created"
        assert req.priority == EventPriority.NORMAL

    def test_replay_request(self) -> None:
        req = ReplayRequest(event_ids=["e1", "e2"])
        assert len(req.event_ids) == 2

    def test_event_filter(self) -> None:
        f = EventFilter(event_types=["task.created"])
        assert "task.created" in f.event_types

    def test_subscription_model(self) -> None:
        sub = Subscription(event_type="task.created", handler_name="test_handler")
        assert sub.active is True
        assert sub.subscription_id


# ======================================================================
# EventBus
# ======================================================================

class TestEventBus:
    @pytest.fixture
    def bus(self) -> InMemoryEventBus:
        return InMemoryEventBus(persistence=InMemoryEventPersistence())

    @pytest.mark.asyncio
    async def test_start_stop(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        health = await bus.health()
        assert health["running"] is True
        await bus.stop()
        health = await bus.health()
        assert health["running"] is False

    @pytest.mark.asyncio
    async def test_publish(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        event = _make_event("system.event")
        result = await bus.publish(event)
        assert result.status == EventStatus.COMPLETED
        await bus.stop()

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        sub_id = await bus.subscribe("task.created", handler)
        assert sub_id
        event = _make_event("task.created")
        await bus.publish(event)
        assert len(received) == 1
        assert received[0].event_type == "task.created"
        await bus.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        sub_id = await bus.subscribe("task.created", handler)
        await bus.unsubscribe(sub_id)
        await bus.publish(_make_event("task.created"))
        assert len(received) == 0
        await bus.stop()

    @pytest.mark.asyncio
    async def test_broadcast(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe("task.created", handler)
        await bus.broadcast(_make_event("task.created"))
        assert len(received) == 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_wildcard_subscription(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe("*", handler)
        await bus.publish(_make_event("task.created"))
        await bus.publish(_make_event("goal.created"))
        assert len(received) == 2
        await bus.stop()

    @pytest.mark.asyncio
    async def test_request_reply(self, bus: InMemoryEventBus) -> None:
        await bus.start()

        async def responder(event: Event) -> None:
            reply = _make_event("reply.event", payload={"original": event.event_id})
            await bus.reply(event, reply)

        await bus.subscribe("request.event", responder)
        request_event = _make_event("request.event")
        reply = await bus.request(request_event, timeout=5.0)
        assert reply.event_type == "reply.event"
        await bus.stop()

    @pytest.mark.asyncio
    async def test_request_timeout(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        with pytest.raises(TimeoutError):
            await bus.request(_make_event("request.event"), timeout=0.1)
        await bus.stop()

    @pytest.mark.asyncio
    async def test_delayed_event(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe("delayed.event", handler)
        event = _make_event("delayed.event")
        await bus.publish_delayed(event, delay_seconds=0)
        await asyncio.sleep(0.3)
        assert len(received) >= 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_scheduled_event(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe("sched.event", handler)
        event = _make_event("sched.event")
        await bus.schedule_event(event, interval_seconds=0, max_runs=1)
        await asyncio.sleep(0.3)
        assert len(received) >= 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_dead_letter_queue(self, bus: InMemoryEventBus) -> None:
        await bus.start()

        async def failing_handler(event: Event) -> None:
            raise ValueError("handler failure")

        await bus.subscribe("fail.event", failing_handler)
        await bus.publish(_make_event("fail.event"))
        dlq = await bus.get_dead_letters()
        assert len(dlq) >= 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_get_event(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        event = _make_event("system.event")
        await bus.publish(event)
        fetched = await bus.get_event(event.event_id)
        assert fetched is not None
        assert fetched.event_id == event.event_id
        await bus.stop()

    @pytest.mark.asyncio
    async def test_list_events(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        await bus.publish(_make_event("task.created"))
        await bus.publish(_make_event("goal.created"))
        events = await bus.list_events()
        assert len(events) >= 2
        await bus.stop()

    @pytest.mark.asyncio
    async def test_statistics(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        stats = await bus.get_statistics()
        assert "total_events" in stats
        assert "active_subscriptions" in stats
        assert "dead_letter_count" in stats
        await bus.stop()

    @pytest.mark.asyncio
    async def test_health(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        health = await bus.health()
        assert health["status"] == "ok"
        await bus.stop()

    @pytest.mark.asyncio
    async def test_multiple_handlers_same_event(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        results: list[str] = []

        async def handler_a(event: Event) -> None:
            results.append("a")

        async def handler_b(event: Event) -> None:
            results.append("b")

        await bus.subscribe("task.created", handler_a)
        await bus.subscribe("task.created", handler_b)
        await bus.publish(_make_event("task.created"))
        assert sorted(results) == ["a", "b"]
        await bus.stop()

    @pytest.mark.asyncio
    async def test_handler_error_does_not_crash_bus(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        results: list[str] = []

        async def broken(event: Event) -> None:
            raise ValueError("broken")

        async def good(event: Event) -> None:
            results.append("ok")

        await bus.subscribe("task.x", broken)
        await bus.subscribe("task.x", good)
        await bus.publish(_make_event("task.x"))
        assert "ok" in results
        await bus.stop()

    @pytest.mark.asyncio
    async def test_get_active_subscriptions(self, bus: InMemoryEventBus) -> None:
        await bus.start()
        await bus.subscribe("task.created", AsyncMock())
        subs = bus.get_active_subscriptions()
        assert len(subs) == 1
        await bus.stop()


# ======================================================================
# Dispatcher
# ======================================================================

class TestDispatcher:
    @pytest.fixture
    def dispatcher(self) -> EventDispatcher:
        return EventDispatcher()

    @pytest.mark.asyncio
    async def test_dispatch_sync(self, dispatcher: EventDispatcher) -> None:
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        event = _make_event("test.sync")
        await dispatcher.dispatch_sync(event, [handler])
        assert len(received) == 1
        assert event.status == EventStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_dispatch_async(self, dispatcher: EventDispatcher) -> None:
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        event = _make_event("test.async")
        await dispatcher.dispatch_async(event, [handler])
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_dispatch_parallel(self, dispatcher: EventDispatcher) -> None:
        results: list[str] = []

        async def handler_a(event: Event) -> None:
            results.append("a")

        async def handler_b(event: Event) -> None:
            results.append("b")

        event = _make_event("test.parallel")
        await dispatcher.dispatch_parallel(event, [handler_a, handler_b])
        assert sorted(results) == ["a", "b"]

    @pytest.mark.asyncio
    async def test_dispatch_ordered(self, dispatcher: EventDispatcher) -> None:
        order: list[int] = []

        async def handler_a(event: Event) -> None:
            order.append(1)

        async def handler_b(event: Event) -> None:
            order.append(2)

        event = _make_event("test.ordered")
        await dispatcher.dispatch_ordered(event, [handler_a, handler_b])
        assert order == [1, 2]

    @pytest.mark.asyncio
    async def test_dispatch_priority(self, dispatcher: EventDispatcher) -> None:
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        event = _make_event("test.priority", priority=EventPriority.HIGH)
        await dispatcher.dispatch_priority(event, [handler])
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_dispatch_sync_failure(self, dispatcher: EventDispatcher) -> None:
        async def failing(event: Event) -> None:
            raise RuntimeError("fail")

        event = _make_event("test.fail")
        with pytest.raises(RuntimeError):
            await dispatcher.dispatch_sync(event, [failing])
        assert event.status == EventStatus.FAILED

    @pytest.mark.asyncio
    async def test_dispatch_parallel_failure(self, dispatcher: EventDispatcher) -> None:
        async def failing(event: Event) -> None:
            raise RuntimeError("fail")

        event = _make_event("test.fail")
        with pytest.raises(RuntimeError):
            await dispatcher.dispatch_parallel(event, [failing])
        assert event.status == EventStatus.FAILED

    def test_queue_size(self, dispatcher: EventDispatcher) -> None:
        assert dispatcher.queue_size == 0

    def test_max_concurrency(self, dispatcher: EventDispatcher) -> None:
        assert dispatcher.max_concurrency == 10


# ======================================================================
# Publisher
# ======================================================================

class TestPublisher:
    @pytest.fixture
    def bus(self) -> InMemoryEventBus:
        return InMemoryEventBus()

    @pytest.fixture
    def publisher(self, bus: InMemoryEventBus) -> EventPublisher:
        return EventPublisher(bus=bus, default_source="test")

    @pytest.mark.asyncio
    async def test_publish(self, publisher: EventPublisher) -> None:
        event = await publisher.publish("task.created", payload={"task_id": "1"})
        assert event.event_type == "task.created"
        assert event.payload["task_id"] == "1"
        assert event.source == "test"

    @pytest.mark.asyncio
    async def test_publish_event(self, publisher: EventPublisher) -> None:
        event = _make_event("goal.created")
        result = await publisher.publish_event(event)
        assert result.event_type == "goal.created"

    @pytest.mark.asyncio
    async def test_publish_many(self, publisher: EventPublisher) -> None:
        events = [_make_event(f"type.{i}") for i in range(3)]
        results = await publisher.publish_many(events)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_publish_with_middleware(self, bus: InMemoryEventBus) -> None:
        tracking: list[str] = []

        class TestMiddleware(EventMiddleware):
            @property
            def name(self) -> str:
                return "test"

            @property
            def priority(self) -> int:
                return 0

            async def before_publish(self, event: Event) -> Event:
                tracking.append("before")
                return event

            async def after_publish(self, event: Event, result: Event | None = None) -> None:
                tracking.append("after")

            async def on_error(self, event: Event, error: Exception) -> bool:
                return True

        publisher = EventPublisher(bus=bus, middlewares=[TestMiddleware()])
        await publisher.publish("test.event")
        assert "before" in tracking
        assert "after" in tracking


# ======================================================================
# Subscriber
# ======================================================================

class TestSubscriber:
    @pytest.fixture
    def bus(self) -> InMemoryEventBus:
        return InMemoryEventBus()

    @pytest.fixture
    def subscriber(self, bus: InMemoryEventBus) -> EventSubscriber:
        return EventSubscriber(bus=bus)

    @pytest.mark.asyncio
    async def test_subscribe(self, subscriber: EventSubscriber) -> None:
        async def handler(event: Event) -> None:
            pass

        sub_id = await subscriber.subscribe("task.created", handler)
        assert sub_id
        assert subscriber.subscription_count == 1

    @pytest.mark.asyncio
    async def test_subscribe_handler(self, subscriber: EventSubscriber) -> None:
        handler = TaskCreatedHandler()
        sub_id = await subscriber.subscribe_handler(handler)
        assert sub_id

    @pytest.mark.asyncio
    async def test_subscribe_wildcard(self, subscriber: EventSubscriber) -> None:
        async def handler(event: Event) -> None:
            pass

        sub_id = await subscriber.subscribe_wildcard(handler)
        assert sub_id

    @pytest.mark.asyncio
    async def test_unsubscribe(self, subscriber: EventSubscriber) -> None:
        async def handler(event: Event) -> None:
            pass

        sub_id = await subscriber.subscribe("task.created", handler)
        result = await subscriber.unsubscribe(sub_id)
        assert result is True
        assert subscriber.subscription_count == 0

    @pytest.mark.asyncio
    async def test_get_subscriptions(self, subscriber: EventSubscriber) -> None:
        async def handler(event: Event) -> None:
            pass

        await subscriber.subscribe("task.created", handler)
        subs = await subscriber.get_subscriptions()
        assert len(subs) == 1
        assert subs[0]["event_type"] == "task.created"


# ======================================================================
# Registry
# ======================================================================

class TestRegistry:
    def test_register_and_get(self) -> None:
        from app.events.registry import EventHandlerRegistry

        registry = EventHandlerRegistry()
        handler = TaskCreatedHandler()
        registry.register(handler)
        assert registry.has_handlers("task.created")
        handlers = registry.get_handlers("task.created")
        assert len(handlers) == 1

    def test_unregister(self) -> None:
        from app.events.registry import EventHandlerRegistry

        registry = EventHandlerRegistry()
        handler = TaskCreatedHandler()
        registry.register(handler)
        result = registry.unregister(handler)
        assert result is True
        assert not registry.has_handlers("task.created")

    def test_get_all_handlers(self) -> None:
        from app.events.registry import EventHandlerRegistry

        registry = EventHandlerRegistry()
        registry.register(TaskCreatedHandler())
        registry.register(GoalCreatedHandler())
        all_h = registry.get_all_handlers()
        assert "task.created" in all_h
        assert "goal.created" in all_h

    def test_get_registered_types(self) -> None:
        from app.events.registry import EventHandlerRegistry

        registry = EventHandlerRegistry()
        registry.register(TaskCreatedHandler())
        types = registry.get_registered_types()
        assert "task.created" in types

    def test_get_handler_count(self) -> None:
        from app.events.registry import EventHandlerRegistry

        registry = EventHandlerRegistry()
        registry.register(TaskCreatedHandler())
        registry.register(GoalCreatedHandler())
        assert registry.get_handler_count() == 2

    def test_clear(self) -> None:
        from app.events.registry import EventHandlerRegistry

        registry = EventHandlerRegistry()
        registry.register(TaskCreatedHandler())
        count = registry.clear()
        assert count == 1
        assert registry.get_handler_count() == 0

    def test_get_handler_by_name(self) -> None:
        from app.events.registry import EventHandlerRegistry

        registry = EventHandlerRegistry()
        handler = TaskCreatedHandler()
        registry.register(handler)
        found = registry.get_handler("TaskCreatedHandler")
        assert found is handler


# ======================================================================
# Default Handlers
# ======================================================================

class TestDefaultHandlers:
    def test_all_default_handlers_exist(self) -> None:
        assert len(DEFAULT_HANDLERS) == 21

    @pytest.mark.asyncio
    async def test_conversation_created_handler(self) -> None:
        handler = ConversationCreatedHandler()
        assert handler.event_type == "conversation.created"
        event = _make_event("conversation.created")
        assert await handler.can_handle(event) is True
        result = await handler.handle(event)
        assert result is None

    @pytest.mark.asyncio
    async def test_task_created_handler(self) -> None:
        handler = TaskCreatedHandler()
        assert handler.event_type == "task.created"
        event = _make_event("task.created")
        assert await handler.can_handle(event) is True
        result = await handler.handle(event)
        assert result is None

    @pytest.mark.asyncio
    async def test_goal_created_handler(self) -> None:
        handler = GoalCreatedHandler()
        assert handler.event_type == "goal.created"
        event = _make_event("goal.created")
        assert await handler.can_handle(event) is True

    @pytest.mark.asyncio
    async def test_message_stored_handler(self) -> None:
        handler = MessageStoredHandler()
        assert handler.event_type == "message.stored"
        event = _make_event("message.stored")
        assert await handler.can_handle(event) is True

    @pytest.mark.asyncio
    async def test_handler_cannot_handle_wrong_type(self) -> None:
        handler = TaskCreatedHandler()
        event = _make_event("wrong.type")
        assert await handler.can_handle(event) is False


# ======================================================================
# Middleware
# ======================================================================

class TestMiddleware:
    @pytest.mark.asyncio
    async def test_logging_middleware(self) -> None:
        mw = LoggingMiddleware()
        assert mw.name == "logging"
        assert mw.priority == 100
        event = _make_event("test")
        result = await mw.before_publish(event)
        assert result is event
        await mw.after_publish(event, event)
        assert await mw.on_error(event, Exception("test")) is True

    @pytest.mark.asyncio
    async def test_tracing_middleware(self) -> None:
        mw = TracingMiddleware()
        assert mw.name == "tracing"
        event = _make_event("test")
        result = await mw.before_publish(event)
        assert "trace_start" in result.metadata
        await mw.after_publish(event, event)
        assert "trace_latency_ms" in event.metadata

    @pytest.mark.asyncio
    async def test_metrics_middleware(self) -> None:
        mw = MetricsMiddleware()
        assert mw.name == "metrics"
        event = _make_event("test")
        await mw.before_publish(event)
        await mw.after_publish(event, event)
        metrics = mw.get_metrics()
        assert metrics["total_published"] == 1
        assert metrics["total_completed"] == 1

    @pytest.mark.asyncio
    async def test_validation_middleware(self) -> None:
        mw = ValidationMiddleware()
        assert mw.name == "validation"
        event = _make_event("test")
        result = await mw.before_publish(event)
        assert result is event

    @pytest.mark.asyncio
    async def test_validation_middleware_missing_field(self) -> None:
        mw = ValidationMiddleware(required_fields=["nonexistent"])
        event = _make_event("test")
        with pytest.raises(ValueError, match="missing required field"):
            await mw.before_publish(event)

    @pytest.mark.asyncio
    async def test_retry_middleware(self) -> None:
        mw = RetryMiddleware(max_retries=2)
        assert mw.name == "retry"
        event = _make_event("test")
        result = await mw.on_error(event, Exception("fail"))
        assert result is True
        assert mw.get_retry_count(event.event_id) == 1

    @pytest.mark.asyncio
    async def test_retry_middleware_exhausted(self) -> None:
        mw = RetryMiddleware(max_retries=1)
        event = _make_event("test")
        await mw.on_error(event, Exception("fail"))
        result = await mw.on_error(event, Exception("fail"))
        assert result is False

    @pytest.mark.asyncio
    async def test_authorization_middleware(self) -> None:
        mw = AuthorizationMiddleware(allowed_sources=["allowed"])
        event = _make_event("test", source="allowed")
        result = await mw.before_publish(event)
        assert result is event

    @pytest.mark.asyncio
    async def test_authorization_middleware_denied(self) -> None:
        mw = AuthorizationMiddleware(allowed_sources=["allowed"])
        event = _make_event("test", source="denied")
        with pytest.raises(PermissionError):
            await mw.before_publish(event)

    @pytest.mark.asyncio
    async def test_transformation_middleware(self) -> None:
        def transform(event: Event) -> Event:
            event.payload["transformed"] = True
            return event

        mw = TransformationMiddleware(transformations={"test.event": transform})
        event = _make_event("test.event")
        result = await mw.before_publish(event)
        assert result.payload["transformed"] is True


# ======================================================================
# Filters
# ======================================================================

class TestFilters:
    def test_matches_type(self) -> None:
        engine = EventFilterEngine()
        event = _make_event("task.created")
        assert engine.matches_type(event, "task.created") is True
        assert engine.matches_type(event, "goal.created") is False
        assert engine.matches_type(event, "*") is True

    def test_matches_source(self) -> None:
        engine = EventFilterEngine()
        event = _make_event("test", source="test-source")
        assert engine.matches_source(event, "test-source") is True
        assert engine.matches_source(event, "other") is False

    def test_matches_session(self) -> None:
        engine = EventFilterEngine()
        event = _make_event("test", session_id="sess-1")
        assert engine.matches_session(event, "sess-1") is True

    def test_matches_user(self) -> None:
        engine = EventFilterEngine()
        event = _make_event("test", user_id="user-1")
        assert engine.matches_user(event, "user-1") is True

    def test_matches_correlation(self) -> None:
        engine = EventFilterEngine()
        event = _make_event("test", correlation_id="corr-1")
        assert engine.matches_correlation(event, "corr-1") is True

    def test_matches_aggregate(self) -> None:
        engine = EventFilterEngine()
        event = _make_event("test", aggregate_id="agg-1")
        assert engine.matches_aggregate(event, "agg-1") is True

    def test_matches_time_range(self) -> None:
        engine = EventFilterEngine()
        now = datetime.now(timezone.utc)
        event = _make_event("test", timestamp=now)
        assert engine.matches_time_range(event, time_from=now - timedelta(hours=1)) is True
        assert engine.matches_time_range(event, time_to=now - timedelta(hours=1)) is False

    def test_matches_filter(self) -> None:
        engine = EventFilterEngine()
        event = _make_event("task.created", user_id="u1", session_id="s1")
        f = EventFilter(event_types=["task.created"], user_ids=["u1"])
        assert engine.matches(event, f) is True
        f_fail = EventFilter(user_ids=["other"])
        assert engine.matches(event, f_fail) is False

    def test_filter_events(self) -> None:
        engine = EventFilterEngine()
        events = [
            _make_event("task.created"),
            _make_event("goal.created"),
            _make_event("task.created"),
        ]
        f = EventFilter(event_types=["task.created"])
        filtered = engine.filter_events(events, f)
        assert len(filtered) == 2

    def test_matches_empty_filter(self) -> None:
        engine = EventFilterEngine()
        event = _make_event("test")
        assert engine.matches(event, EventFilter()) is True


# ======================================================================
# Serializer
# ======================================================================

class TestSerializer:
    def test_serialize_deserialize(self) -> None:
        serializer = JSONEventSerializer()
        event = _make_event("task.created", payload={"key": "value"})
        serialized = serializer.serialize(event)
        deserialized = serializer.deserialize(serialized)
        assert deserialized.event_type == "task.created"
        assert deserialized.payload["key"] == "value"

    def test_serialize_bytes_deserialize_bytes(self) -> None:
        serializer = JSONEventSerializer()
        event = _make_event("test")
        data = serializer.serialize_bytes(event)
        assert isinstance(data, bytes)
        result = serializer.deserialize_bytes(data)
        assert result.event_id == event.event_id

    def test_serialize_dict_deserialize_dict(self) -> None:
        serializer = JSONEventSerializer()
        event = _make_event("test", payload={"x": 1})
        d = serializer.serialize_dict(event)
        assert isinstance(d, dict)
        result = serializer.deserialize_dict(d)
        assert result.event_type == "test"
        assert result.payload["x"] == 1


# ======================================================================
# Persistence
# ======================================================================

class TestPersistence:
    @pytest.fixture
    def store(self) -> InMemoryEventPersistence:
        return InMemoryEventPersistence()

    @pytest.mark.asyncio
    async def test_store_and_get(self, store: InMemoryEventPersistence) -> None:
        event = _make_event("test")
        await store.store(event)
        fetched = await store.get(event.event_id)
        assert fetched is not None
        assert fetched.event_id == event.event_id

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store: InMemoryEventPersistence) -> None:
        result = await store.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_events(self, store: InMemoryEventPersistence) -> None:
        await store.store(_make_event("type.a"))
        await store.store(_make_event("type.b"))
        events = await store.list_events()
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_list_with_filter(self, store: InMemoryEventPersistence) -> None:
        await store.store(_make_event("task.created"))
        await store.store(_make_event("goal.created"))
        f = EventFilter(event_types=["task.created"])
        events = await store.list_events(filter_expr=f)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_count(self, store: InMemoryEventPersistence) -> None:
        await store.store(_make_event("test"))
        count = await store.count()
        assert count == 1

    @pytest.mark.asyncio
    async def test_count_with_filter(self, store: InMemoryEventPersistence) -> None:
        await store.store(_make_event("task.created"))
        await store.store(_make_event("goal.created"))
        f = EventFilter(event_types=["task.created"])
        count = await store.count(filter_expr=f)
        assert count == 1

    @pytest.mark.asyncio
    async def test_delete(self, store: InMemoryEventPersistence) -> None:
        event = _make_event("test")
        await store.store(event)
        result = await store.delete(event.event_id)
        assert result is True
        assert await store.get(event.event_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, store: InMemoryEventPersistence) -> None:
        result = await store.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self, store: InMemoryEventPersistence) -> None:
        await store.store(_make_event("a"))
        await store.store(_make_event("b"))
        count = await store.clear()
        assert count == 2
        assert await store.count() == 0

    @pytest.mark.asyncio
    async def test_max_events_eviction(self) -> None:
        store = InMemoryEventPersistence(max_events=3)
        for i in range(5):
            await store.store(_make_event(f"test.{i}"))
        assert store.size == 3

    def test_size(self, store: InMemoryEventPersistence) -> None:
        assert store.size == 0


# ======================================================================
# Replay
# ======================================================================

class TestReplay:
    @pytest.fixture
    def replay(self) -> EventReplay:
        persistence = InMemoryEventPersistence()
        return EventReplay(persistence=persistence)

    @pytest.mark.asyncio
    async def test_replay_by_event_id(self, replay: EventReplay) -> None:
        event = _make_event("test.replay")
        await replay._persistence.store(event)
        result = await replay.replay_by_event_id(event.event_id)
        assert result.total_events == 1

    @pytest.mark.asyncio
    async def test_replay_by_event_id_not_found(self, replay: EventReplay) -> None:
        result = await replay.replay_by_event_id("nonexistent")
        assert result.total_events == 0

    @pytest.mark.asyncio
    async def test_replay_by_aggregate(self, replay: EventReplay) -> None:
        event = _make_event("test", aggregate_id="agg-1")
        await replay._persistence.store(event)
        result = await replay.replay_by_aggregate("agg-1")
        assert result.total_events == 1

    @pytest.mark.asyncio
    async def test_replay_by_session(self, replay: EventReplay) -> None:
        event = _make_event("test", session_id="sess-1")
        await replay._persistence.store(event)
        result = await replay.replay_by_session("sess-1")
        assert result.total_events == 1

    @pytest.mark.asyncio
    async def test_replay_by_user(self, replay: EventReplay) -> None:
        event = _make_event("test", user_id="user-1")
        await replay._persistence.store(event)
        result = await replay.replay_by_user("user-1")
        assert result.total_events == 1

    @pytest.mark.asyncio
    async def test_replay_by_time_range(self, replay: EventReplay) -> None:
        event = _make_event("test")
        await replay._persistence.store(event)
        now = datetime.now(timezone.utc)
        result = await replay.replay_by_time_range(
            time_from=now - timedelta(hours=1),
            time_to=now + timedelta(hours=1),
        )
        assert result.total_events == 1

    @pytest.mark.asyncio
    async def test_replay_by_request(self, replay: EventReplay) -> None:
        event = _make_event("test", user_id="user-1")
        await replay._persistence.store(event)
        req = ReplayRequest(user_ids=["user-1"])
        result = await replay.replay_by_request(req)
        assert result.total_events == 1

    @pytest.mark.asyncio
    async def test_replay_with_handler(self, replay: EventReplay) -> None:
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        event = _make_event("task.created")
        await replay._persistence.store(event)
        replay.register_handler("task.created", handler)
        result = await replay.replay_by_event_id(event.event_id)
        assert result.replayed >= 1
        assert len(received) >= 1

    @pytest.mark.asyncio
    async def test_replay_wildcard_handler(self, replay: EventReplay) -> None:
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        event = _make_event("anything")
        await replay._persistence.store(event)
        replay.register_wildcard(handler)
        result = await replay.replay_by_event_id(event.event_id)
        assert result.replayed >= 1

    @pytest.mark.asyncio
    async def test_replay_count(self, replay: EventReplay) -> None:
        assert replay.replay_count == 0
        await replay.replay_by_time_range()
        assert replay.replay_count == 1


# ======================================================================
# Metrics
# ======================================================================

class TestMetrics:
    def test_metrics(self) -> None:
        metrics = EventMetrics()
        metrics.increment_published(5)
        metrics.increment_processed(3)
        metrics.increment_failed(1)
        metrics.increment_retries(2)
        metrics.record_latency(1.5)
        metrics.set_subscriber_count(10)
        metrics.set_queue_size(5)
        metrics.increment_replay_count()
        metrics.increment_dead_letter()
        summary = metrics.get_summary()
        assert summary["total_published"] == 5
        assert summary["total_processed"] == 3
        assert summary["total_failed"] == 1
        assert summary["total_retries"] == 2
        assert summary["subscriber_count"] == 10
        assert summary["queue_size"] == 5
        assert summary["replay_count"] == 1
        assert summary["dead_letter_count"] == 1
        assert summary["average_latency_ms"] == 1.5

    def test_metrics_reset(self) -> None:
        metrics = EventMetrics()
        metrics.increment_published(5)
        metrics.reset()
        summary = metrics.get_summary()
        assert summary["total_published"] == 0

    def test_get_event_metrics_singleton(self) -> None:
        m1 = get_event_metrics()
        m2 = get_event_metrics()
        assert m1 is m2


# ======================================================================
# Tracing
# ======================================================================

class TestTracing:
    def test_tracer(self) -> None:
        tracer = EventTracer()
        span = tracer.start_span("evt-1", "publish", event_type="test")
        assert span.span_id
        trace = tracer.end_span(span, event_type="test")
        assert trace.status == "success"
        assert trace.latency_ms >= 0

    def test_tracer_error(self) -> None:
        tracer = EventTracer()
        span = tracer.start_span("evt-1", "dispatch")
        trace = tracer.end_span(span, error=True, error_message="test error")
        assert trace.status == "error"

    def test_trace_publication(self) -> None:
        tracer = EventTracer()
        span = tracer.trace_publication("evt-1", "task.created")
        trace = tracer.end_span(span)
        assert trace.operation == "publish"

    def test_trace_dispatch(self) -> None:
        tracer = EventTracer()
        span = tracer.trace_dispatch("evt-1", handler_count=3)
        trace = tracer.end_span(span)
        assert trace.operation == "dispatch"

    def test_trace_subscriber(self) -> None:
        tracer = EventTracer()
        span = tracer.trace_subscriber("evt-1", "my_handler")
        trace = tracer.end_span(span)
        assert trace.operation == "subscriber"

    def test_trace_retry(self) -> None:
        tracer = EventTracer()
        span = tracer.trace_retry("evt-1", retry_count=2)
        trace = tracer.end_span(span)
        assert trace.operation == "retry"

    def test_trace_failure(self) -> None:
        tracer = EventTracer()
        span = tracer.trace_failure("evt-1", error="test error")
        trace = tracer.end_span(span, error=True)
        assert trace.operation == "failure"
        assert trace.status == "error"

    def test_get_traces(self) -> None:
        tracer = EventTracer()
        span = tracer.start_span("evt-1", "op")
        tracer.end_span(span)
        traces = tracer.get_traces()
        assert len(traces) == 1

    def test_get_traces_by_event(self) -> None:
        tracer = EventTracer()
        span = tracer.start_span("evt-1", "op")
        tracer.end_span(span)
        traces = tracer.get_traces_by_event("evt-1")
        assert len(traces) == 1

    def test_get_traces_by_operation(self) -> None:
        tracer = EventTracer()
        span = tracer.start_span("evt-1", "publish")
        tracer.end_span(span)
        traces = tracer.get_traces_by_operation("publish")
        assert len(traces) == 1

    def test_get_error_count(self) -> None:
        tracer = EventTracer()
        span = tracer.start_span("evt-1", "op")
        tracer.end_span(span, error=True)
        assert tracer.get_error_count() == 1

    def test_get_total_count(self) -> None:
        tracer = EventTracer()
        span = tracer.start_span("evt-1", "op")
        tracer.end_span(span)
        assert tracer.get_total_count() == 1

    def test_reset(self) -> None:
        tracer = EventTracer()
        span = tracer.start_span("evt-1", "op")
        tracer.end_span(span)
        tracer.reset()
        assert tracer.get_total_count() == 0

    def test_get_event_tracer_singleton(self) -> None:
        t1 = get_event_tracer()
        t2 = get_event_tracer()
        assert t1 is t2

    def test_max_traces_eviction(self) -> None:
        tracer = EventTracer(max_traces=2)
        for i in range(4):
            span = tracer.start_span(f"evt-{i}", "op")
            tracer.end_span(span)
        assert tracer.get_total_count() == 2


# ======================================================================
# Lifecycle
# ======================================================================

class TestLifecycle:
    def test_lifecycle_states(self) -> None:
        lc = EventLifecycle()
        assert lc.state == EventLifecycleState.REGISTERED
        assert lc.is_registered is True
        lc.initialized()
        assert lc.is_initialized is True
        lc.ready()
        assert lc.is_ready is True
        lc.running()
        assert lc.is_running is True
        lc.paused()
        assert lc.is_paused is True
        lc.shutdown()
        assert lc.is_shutdown is True

    def test_lifecycle_failed(self) -> None:
        lc = EventLifecycle()
        lc.failed("test error")
        assert lc.is_failed is True

    def test_lifecycle_recover(self) -> None:
        lc = EventLifecycle()
        lc.failed("error")
        lc.recover()
        assert lc.is_registered is True

    def test_lifecycle_name(self) -> None:
        lc = EventLifecycle(name="my_bus")
        assert lc.name == "my_bus"


# ======================================================================
# Factory
# ======================================================================

class TestFactory:
    def test_create_system(self) -> None:
        factory = EventSystemFactory()
        system = factory.create_system()
        assert "bus" in system
        assert "dispatcher" in system
        assert "publisher" in system
        assert "subscriber" in system
        assert "replay" in system
        assert "serializer" in system
        assert "filter_engine" in system
        assert "lifecycle" in system
        assert "metrics" in system
        assert "tracer" in system
        assert "persistence" in system

    def test_create_bus(self) -> None:
        factory = EventSystemFactory()
        bus = factory.create_bus()
        assert isinstance(bus, InMemoryEventBus)

    def test_create_dispatcher(self) -> None:
        factory = EventSystemFactory()
        dispatcher = factory.create_dispatcher()
        assert isinstance(dispatcher, EventDispatcher)

    def test_create_serializer(self) -> None:
        factory = EventSystemFactory()
        serializer = factory.create_serializer()
        assert isinstance(serializer, JSONEventSerializer)

    def test_create_filter_engine(self) -> None:
        factory = EventSystemFactory()
        engine = factory.create_filter_engine()
        assert isinstance(engine, EventFilterEngine)

    def test_create_lifecycle(self) -> None:
        factory = EventSystemFactory()
        lc = factory.create_lifecycle()
        assert isinstance(lc, EventLifecycle)


# ======================================================================
# API Endpoints
# ======================================================================

class TestAPIEndpoints:
    @pytest.fixture
    def app(self):
        from fastapi import FastAPI
        from app.api.v1.routes.events import router as events_router

        test_app = FastAPI()
        test_app.include_router(events_router)
        return test_app

    @pytest.fixture
    def client(self, app):
        from httpx import AsyncClient, ASGITransport

        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.mark.asyncio
    async def test_health_no_bus(self, client) -> None:
        response = await client.get("/events/health")
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_publish_no_bus(self, client) -> None:
        response = await client.post(
            "/events/publish",
            json={"event_type": "test.event"},
        )
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_list_no_bus(self, client) -> None:
        response = await client.get("/events")
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_statistics_no_bus(self, client) -> None:
        response = await client.get("/events/statistics")
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_metrics_no_bus(self, client) -> None:
        response = await client.get("/events/metrics")
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_traces_no_bus(self, client) -> None:
        response = await client.get("/events/traces")
        assert response.status_code == 503


# ======================================================================
# Integration
# ======================================================================

class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_publish_subscribe_flow(self) -> None:
        bus = InMemoryEventBus()
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe("task.created", handler)
        event = _make_event("task.created", payload={"task_id": "123"})
        await bus.publish(event)
        assert len(received) == 1
        assert received[0].payload["task_id"] == "123"
        await bus.stop()

    @pytest.mark.asyncio
    async def test_publisher_with_bus_and_middleware(self) -> None:
        bus = InMemoryEventBus()
        await bus.start()
        metrics_mw = MetricsMiddleware()
        publisher = EventPublisher(bus=bus, middlewares=[metrics_mw])
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe("task.created", handler)
        await publisher.publish("task.created", payload={"x": 1})
        assert len(received) == 1
        summary = metrics_mw.get_metrics()
        assert summary["total_published"] == 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_factory_full_flow(self) -> None:
        factory = EventSystemFactory()
        system = factory.create_system()
        bus: InMemoryEventBus = system["bus"]
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe("task.created", handler)
        publisher: EventPublisher = system["publisher"]
        await publisher.publish("task.created", payload={"data": "test"})
        assert len(received) == 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_replay_integration(self) -> None:
        persistence = InMemoryEventPersistence()
        bus = InMemoryEventBus(persistence=persistence)
        await bus.start()
        replay = EventReplay(persistence=persistence)
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        replay.register_handler("task.created", handler)
        event = _make_event("task.created", aggregate_id="agg-1")
        await bus.publish(event)
        result = await replay.replay_by_aggregate("agg-1")
        assert result.replayed >= 1
        await bus.stop()

    @pytest.mark.asyncio
    async def test_filtered_subscription(self) -> None:
        bus = InMemoryEventBus()
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        f = EventFilter(user_ids=["user-1"])
        await bus.subscribe("task.created", handler, filter_expr=f)
        await bus.publish(_make_event("task.created", user_id="user-1"))
        await bus.publish(_make_event("task.created", user_id="user-2"))
        assert len(received) == 1
        await bus.stop()


# ======================================================================
# Concurrency
# ======================================================================

class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_publish(self) -> None:
        bus = InMemoryEventBus()
        await bus.start()
        received: list[str] = []
        lock = asyncio.Lock()

        async def handler(event: Event) -> None:
            async with lock:
                received.append(event.event_id)

        await bus.subscribe("test.event", handler)
        tasks = [
            bus.publish(_make_event("test.event")) for _ in range(10)
        ]
        await asyncio.gather(*tasks)
        assert len(received) == 10
        await bus.stop()

    @pytest.mark.asyncio
    async def test_concurrent_subscribe_unsubscribe(self) -> None:
        bus = InMemoryEventBus()
        await bus.start()
        sub_ids: list[str] = []

        async def handler(event: Event) -> None:
            pass

        for _ in range(5):
            sub_id = await bus.subscribe("test.event", handler)
            sub_ids.append(sub_id)

        for sub_id in sub_ids:
            await bus.unsubscribe(sub_id)

        subs = bus.get_active_subscriptions()
        assert len(subs) == 0
        await bus.stop()


# ======================================================================
# Failure Recovery
# ======================================================================

class TestFailureRecovery:
    @pytest.mark.asyncio
    async def test_bus_recovers_after_handler_error(self) -> None:
        bus = InMemoryEventBus()
        await bus.start()
        received: list[str] = []

        async def failing(event: Event) -> None:
            raise RuntimeError("boom")

        async def good(event: Event) -> None:
            received.append("ok")

        await bus.subscribe("test.event", failing)
        await bus.subscribe("test.event", good)
        await bus.publish(_make_event("test.event"))
        assert "ok" in received
        await bus.stop()

    @pytest.mark.asyncio
    async def test_lifecycle_recovery(self) -> None:
        lc = EventLifecycle()
        lc.initialized()
        lc.ready()
        lc.running()
        lc.failed("error")
        assert lc.is_failed
        lc.recover()
        assert lc.is_registered
        lc.initialized()
        lc.ready()
        lc.running()
        assert lc.is_running

    @pytest.mark.asyncio
    async def test_bus_stops_delayed_processing(self) -> None:
        bus = InMemoryEventBus()
        await bus.start()
        await bus.stop()
        health = await bus.health()
        assert health["running"] is False


# ======================================================================
# Edge Cases
# ======================================================================

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_publish_empty_event(self) -> None:
        bus = InMemoryEventBus()
        await bus.start()
        event = Event()
        result = await bus.publish(event)
        assert result.status == EventStatus.COMPLETED
        await bus.stop()

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent(self) -> None:
        bus = InMemoryEventBus()
        await bus.start()
        result = await bus.unsubscribe("nonexistent")
        assert result is False
        await bus.stop()

    @pytest.mark.asyncio
    async def test_publish_with_all_fields(self) -> None:
        bus = InMemoryEventBus()
        await bus.start()
        event = Event(
            event_type="test.all_fields",
            aggregate_id="agg-1",
            aggregate_type="task",
            source="test",
            correlation_id="corr-1",
            causation_id="cause-1",
            session_id="sess-1",
            user_id="user-1",
            payload={"key": "value"},
            metadata={"meta": "data"},
            priority=EventPriority.HIGH,
        )
        result = await bus.publish(event)
        assert result.event_type == "test.all_fields"
        assert result.aggregate_id == "agg-1"
        assert result.priority == EventPriority.HIGH
        await bus.stop()

    @pytest.mark.asyncio
    async def test_delayed_event_with_past_time(self) -> None:
        bus = InMemoryEventBus()
        await bus.start()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        await bus.subscribe("test.delayed", handler)
        await bus.publish_delayed(_make_event("test.delayed"), delay_seconds=0)
        await asyncio.sleep(0.3)
        assert len(received) >= 1
        await bus.stop()

    def test_serializer_roundtrip_complex(self) -> None:
        serializer = JSONEventSerializer()
        event = Event(
            event_type="complex.event",
            payload={"nested": {"a": [1, 2, 3]}, "string": "hello"},
            metadata={"tags": ["a", "b"]},
        )
        data = serializer.serialize(event)
        result = serializer.deserialize(data)
        assert result.payload["nested"]["a"] == [1, 2, 3]
        assert result.metadata["tags"] == ["a", "b"]

    def test_filter_engine_all_criteria(self) -> None:
        engine = EventFilterEngine()
        now = datetime.now(timezone.utc)
        event = Event(
            event_type="task.created",
            source="test",
            user_id="u1",
            session_id="s1",
            correlation_id="c1",
            aggregate_id="a1",
            timestamp=now,
            priority=EventPriority.HIGH,
        )
        f = EventFilter(
            event_types=["task.created"],
            sources=["test"],
            user_ids=["u1"],
            session_ids=["s1"],
            correlation_ids=["c1"],
            aggregate_ids=["a1"],
            time_from=now - timedelta(hours=1),
            time_to=now + timedelta(hours=1),
            priority_min=EventPriority.NORMAL,
        )
        assert engine.matches(event, f) is True

    @pytest.mark.asyncio
    async def test_persistence_offset_limit(self) -> None:
        store = InMemoryEventPersistence()
        for i in range(10):
            await store.store(_make_event(f"test.{i}"))
        events = await store.list_events(limit=3, offset=2)
        assert len(events) == 3
