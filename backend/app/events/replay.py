"""Event replay — replay events by various criteria."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Coroutine

from app.events.base import EventPersistence
from app.events.schemas import Event, EventFilter, ReplayRequest, ReplayResult

logger = logging.getLogger(__name__)

EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventReplay:
    """Replays events from persistence through registered handlers."""

    def __init__(self, persistence: EventPersistence) -> None:
        self._persistence = persistence
        self._handlers: dict[str, list[EventHandler]] = {}
        self._wildcard_handlers: list[EventHandler] = []
        self._replay_count = 0

    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def register_wildcard(self, handler: EventHandler) -> None:
        self._wildcard_handlers.append(handler)

    async def replay_by_event_id(self, event_id: str) -> ReplayResult:
        event = await self._persistence.get(event_id)
        if not event:
            return ReplayResult(total_events=0, replayed=0, failed=0, errors=[f"Event {event_id} not found"])
        return await self._replay_events([event])

    async def replay_by_aggregate(self, aggregate_id: str) -> ReplayResult:
        events = await self._persistence.list_events(
            filter_expr=EventFilter(aggregate_ids=[aggregate_id]),
            limit=10000,
        )
        return await self._replay_events(events)

    async def replay_by_session(self, session_id: str) -> ReplayResult:
        events = await self._persistence.list_events(
            filter_expr=EventFilter(session_ids=[session_id]),
            limit=10000,
        )
        return await self._replay_events(events)

    async def replay_by_user(self, user_id: str) -> ReplayResult:
        events = await self._persistence.list_events(
            filter_expr=EventFilter(user_ids=[user_id]),
            limit=10000,
        )
        return await self._replay_events(events)

    async def replay_by_time_range(
        self,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
    ) -> ReplayResult:
        events = await self._persistence.list_events(
            filter_expr=EventFilter(time_from=time_from, time_to=time_to),
            limit=10000,
        )
        return await self._replay_events(events)

    async def replay_by_request(self, request: ReplayRequest) -> ReplayResult:
        filter_expr = EventFilter(
            event_types=request.event_types,
            aggregate_ids=request.aggregate_ids,
            session_ids=request.session_ids,
            user_ids=request.user_ids,
            time_from=request.time_from,
            time_to=request.time_to,
        )
        if request.event_ids:
            events = []
            for eid in request.event_ids:
                event = await self._persistence.get(eid)
                if event:
                    events.append(event)
        else:
            events = await self._persistence.list_events(
                filter_expr=filter_expr,
                limit=10000,
            )
        return await self._replay_events(events)

    async def _replay_events(self, events: list[Event]) -> ReplayResult:
        replayed = 0
        failed = 0
        errors: list[str] = []
        for event in sorted(events, key=lambda e: e.timestamp):
            handlers = self._handlers.get(event.event_type, [])
            all_handlers = handlers + self._wildcard_handlers
            if not all_handlers:
                continue
            for handler in all_handlers:
                try:
                    await handler(event)
                    replayed += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"{event.event_id}: {e}")
        self._replay_count += 1
        return ReplayResult(
            total_events=len(events),
            replayed=replayed,
            failed=failed,
            errors=errors,
        )

    @property
    def replay_count(self) -> int:
        return self._replay_count
