"""In-memory event bus — core publish/subscribe/routing engine."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.events.base import EventPersistence
from app.events.filters import EventFilterEngine
from app.events.schemas import (
    DeadLetterEvent,
    DelayedEvent,
    DispatchType,
    Event,
    EventFilter,
    EventPriority,
    EventStatus,
    ReplayRequest,
    ReplayResult,
    ScheduledEvent,
    Subscription,
)

logger = logging.getLogger(__name__)

Handler = Any


class InMemoryEventBus:
    """In-memory event bus with full publish/subscribe/routing support."""

    def __init__(
        self,
        persistence: EventPersistence | None = None,
        max_retries: int = 3,
    ) -> None:
        self._subscriptions: dict[str, Subscription] = {}
        self._handlers: dict[str, list[tuple[str, Handler, EventFilter | None]]] = {}
        self._wildcard_handlers: list[tuple[str, Handler, EventFilter | None]] = []
        self._persistence = persistence
        self._max_retries = max_retries
        self._dead_letter_queue: list[DeadLetterEvent] = []
        self._delayed_events: list[DelayedEvent] = []
        self._scheduled_events: list[ScheduledEvent] = []
        self._request_reply: dict[str, asyncio.Future[Event]] = {}
        self._lock = asyncio.Lock()
        self._filter_engine = EventFilterEngine()
        self._running = False
        self._delayed_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._running = True
        self._delayed_task = asyncio.create_task(self._process_delayed_events())
        logger.info("EventBus started")

    async def stop(self) -> None:
        self._running = False
        if self._delayed_task and not self._delayed_task.done():
            self._delayed_task.cancel()
            try:
                await self._delayed_task
            except asyncio.CancelledError:
                pass
        logger.info("EventBus stopped")

    async def publish(self, event: Event) -> Event:
        event.status = EventStatus.PROCESSING
        if self._persistence:
            await self._persistence.store(event)
        await self._dispatch(event)
        event.status = EventStatus.COMPLETED
        return event

    async def broadcast(self, event: Event) -> Event:
        event.status = EventStatus.PROCESSING
        if self._persistence:
            await self._persistence.store(event)
        await self._dispatch(event, broadcast=True)
        event.status = EventStatus.COMPLETED
        return event

    async def subscribe(
        self,
        event_type: str,
        handler: Handler,
        filter_expr: EventFilter | None = None,
    ) -> str:
        subscription_id = str(uuid4())
        sub = Subscription(
            subscription_id=subscription_id,
            event_type=event_type,
            handler_name=handler.__name__ if hasattr(handler, "__name__") else str(handler),
            active=True,
        )
        self._subscriptions[subscription_id] = sub
        if event_type == "*":
            self._wildcard_handlers.append((subscription_id, handler, filter_expr))
        else:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append((subscription_id, handler, filter_expr))
        logger.debug("Subscribed %s for event_type=%s", subscription_id, event_type)
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        sub = self._subscriptions.pop(subscription_id, None)
        if not sub:
            return False
        sub.active = False
        et = sub.event_type
        if et == "*":
            self._wildcard_handlers = [
                (sid, h, f) for sid, h, f in self._wildcard_handlers if sid != subscription_id
            ]
        else:
            handlers = self._handlers.get(et, [])
            self._handlers[et] = [(sid, h, f) for sid, h, f in handlers if sid != subscription_id]
        logger.debug("Unsubscribed %s", subscription_id)
        return True

    async def request(self, event: Event, timeout: float = 30.0) -> Event:
        future: asyncio.Future[Event] = asyncio.get_event_loop().create_future()
        self._request_reply[event.event_id] = future
        event.metadata["expects_reply"] = True
        await self.publish(event)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._request_reply.pop(event.event_id, None)
            raise TimeoutError(f"No reply for event {event.event_id} within {timeout}s")

    async def reply(self, request_event: Event, reply_event: Event) -> Event:
        reply_event.correlation_id = request_event.event_id
        reply_event.causation_id = request_event.event_id
        future = self._request_reply.pop(request_event.event_id, None)
        if future and not future.done():
            future.set_result(reply_event)
        return reply_event

    async def publish_delayed(self, event: Event, delay_seconds: int) -> str:
        delay_id = str(uuid4())
        publish_at = datetime.now(timezone.utc).timestamp() + delay_seconds
        delayed = DelayedEvent(
            delay_id=delay_id,
            event=event,
            publish_at=datetime.fromtimestamp(publish_at, tz=timezone.utc),
        )
        async with self._lock:
            self._delayed_events.append(delayed)
        logger.debug("Delayed event %s scheduled for %ss", event.event_id, delay_seconds)
        return delay_id

    async def schedule_event(
        self,
        event: Event,
        interval_seconds: int | None = None,
        max_runs: int | None = None,
    ) -> str:
        schedule_id = str(uuid4())
        scheduled = ScheduledEvent(
            schedule_id=schedule_id,
            event=event,
            run_at=datetime.now(timezone.utc),
            interval_seconds=interval_seconds,
            max_runs=max_runs,
        )
        async with self._lock:
            self._scheduled_events.append(scheduled)
        return schedule_id

    async def replay(self, request: ReplayRequest) -> ReplayResult:
        if not self._persistence:
            return ReplayResult(total_events=0, replayed=0, failed=0, errors=["No persistence configured"])
        events = await self._persistence.list_events(
            filter_expr=self._build_replay_filter(request),
            limit=10000,
        )
        replayed = 0
        failed = 0
        errors: list[str] = []
        for event in events:
            try:
                await self._dispatch(event, is_replay=True)
                replayed += 1
            except Exception as e:
                failed += 1
                errors.append(f"{event.event_id}: {e}")
        return ReplayResult(
            total_events=len(events),
            replayed=replayed,
            failed=failed,
            errors=errors,
        )

    async def get_event(self, event_id: str) -> Event | None:
        if self._persistence:
            return await self._persistence.get(event_id)
        return None

    async def list_events(
        self,
        filter_expr: EventFilter | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        if self._persistence:
            return await self._persistence.list_events(filter_expr, limit, offset)
        return []

    async def get_statistics(self) -> dict[str, Any]:
        total = 0
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        if self._persistence:
            total = await self._persistence.count()
        return {
            "total_events": total,
            "events_by_type": by_type,
            "events_by_status": by_status,
            "active_subscriptions": len(self._subscriptions),
            "dead_letter_count": len(self._dead_letter_queue),
            "replay_count": 0,
        }

    async def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self._running else "stopped",
            "total_events": await self._persistence.count() if self._persistence else 0,
            "active_subscriptions": len(self._subscriptions),
            "dead_letter_count": len(self._dead_letter_queue),
            "running": self._running,
        }

    async def get_dead_letters(self) -> list[DeadLetterEvent]:
        return list(self._dead_letter_queue)

    def get_active_subscriptions(self) -> list[Subscription]:
        return [s for s in self._subscriptions.values() if s.active]

    async def _dispatch(self, event: Event, broadcast: bool = False, is_replay: bool = False) -> None:
        dispatched = False
        if event.event_type in self._handlers:
            for sub_id, handler, filter_expr in self._handlers[event.event_type]:
                if filter_expr and not self._filter_engine.matches(event, filter_expr):
                    continue
                await self._invoke_handler(handler, event, sub_id)
                dispatched = True
        for sub_id, handler, filter_expr in self._wildcard_handlers:
            if filter_expr and not self._filter_engine.matches(event, filter_expr):
                continue
            await self._invoke_handler(handler, event, sub_id)
            dispatched = True
        if not dispatched and not broadcast:
            logger.debug("No handlers for event_type=%s", event.event_type)

    async def _invoke_handler(self, handler: Handler, event: Event, sub_id: str) -> None:
        retries = 0
        while retries <= self._max_retries:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
                return
            except Exception as e:
                retries += 1
                if retries > self._max_retries:
                    dlq = DeadLetterEvent(
                        original_event=event,
                        error=str(e),
                        retry_count=retries,
                    )
                    self._dead_letter_queue.append(dlq)
                    event.status = EventStatus.DEAD_LETTER
                    logger.error("Event %s moved to DLQ after %d retries: %s", event.event_id, retries, e)
                    return
                event.status = EventStatus.RETRYING
                event.retry_count = retries
                await asyncio.sleep(0.01 * retries)

    async def _process_delayed_events(self) -> None:
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                async with self._lock:
                    ready = [d for d in self._delayed_events if d.publish_at <= now and d.active]
                    self._delayed_events = [d for d in self._delayed_events if d not in ready]
                for delayed in ready:
                    await self.publish(delayed.event)
                async with self._lock:
                    due = [s for s in self._scheduled_events if s.run_at <= now and s.active]
                    for sched in due:
                        if sched.max_runs and sched.run_count >= sched.max_runs:
                            sched.active = False
                            continue
                        sched.run_count += 1
                        await self.publish(sched.event)
                        if sched.interval_seconds:
                            sched.run_at = datetime.fromtimestamp(
                                now.timestamp() + sched.interval_seconds, tz=timezone.utc
                            )
                        else:
                            sched.active = False
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error processing delayed events")
                await asyncio.sleep(0.5)

    def _build_replay_filter(self, request: ReplayRequest) -> EventFilter | None:
        return EventFilter(
            event_types=request.event_types,
            aggregate_ids=request.aggregate_ids,
            session_ids=request.session_ids,
            user_ids=request.user_ids,
            time_from=request.time_from,
            time_to=request.time_to,
        ) if any([
            request.event_types,
            request.aggregate_ids,
            request.session_ids,
            request.user_ids,
            request.time_from,
            request.time_to,
        ]) else None
