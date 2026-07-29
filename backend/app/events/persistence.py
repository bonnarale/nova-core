"""Event persistence — in-memory and pluggable persistence providers."""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any

from app.events.base import EventPersistence
from app.events.filters import EventFilterEngine
from app.events.schemas import Event, EventFilter

logger = logging.getLogger(__name__)


class InMemoryEventPersistence(EventPersistence):
    """In-memory event store for development and testing."""

    def __init__(self, max_events: int = 10000) -> None:
        self._events: dict[str, Event] = {}
        self._lock = threading.Lock()
        self._max_events = max_events
        self._filter_engine = EventFilterEngine()

    async def store(self, event: Event) -> None:
        with self._lock:
            self._events[event.event_id] = event
            if len(self._events) > self._max_events:
                oldest = sorted(self._events.keys(), key=lambda k: self._events[k].timestamp)
                for key in oldest[: len(oldest) - self._max_events]:
                    del self._events[key]

    async def get(self, event_id: str) -> Event | None:
        with self._lock:
            return self._events.get(event_id)

    async def list_events(
        self,
        filter_expr: EventFilter | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        with self._lock:
            events = list(self._events.values())
        events.sort(key=lambda e: e.timestamp, reverse=True)
        if filter_expr:
            events = self._filter_engine.filter_events(events, filter_expr)
        return events[offset : offset + limit]

    async def count(self, filter_expr: EventFilter | None = None) -> int:
        if filter_expr is None:
            with self._lock:
                return len(self._events)
        with self._lock:
            events = list(self._events.values())
        return len(self._filter_engine.filter_events(events, filter_expr))

    async def delete(self, event_id: str) -> bool:
        with self._lock:
            if event_id in self._events:
                del self._events[event_id]
                return True
            return False

    async def clear(self) -> int:
        with self._lock:
            count = len(self._events)
            self._events.clear()
            return count

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._events)


class PostgresEventPersistence(EventPersistence):
    """PostgreSQL event store — requires asyncpg session factory."""

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory
        self._filter_engine = EventFilterEngine()

    async def store(self, event: Event) -> None:
        async with self._session_factory() as session:
            await session.execute(
                """
                INSERT INTO events (event_id, event_type, aggregate_id, aggregate_type,
                    source, timestamp, correlation_id, causation_id, session_id, user_id,
                    payload, metadata, version, priority, status, retry_count, max_retries)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
                ON CONFLICT (event_id) DO UPDATE SET status = EXCLUDED.status
                """,
                event.event_id,
                event.event_type,
                event.aggregate_id,
                event.aggregate_type,
                event.source,
                event.timestamp,
                event.correlation_id,
                event.causation_id,
                event.session_id,
                event.user_id,
                event.model_dump_json(),
                event.model_dump_json(),
                event.version,
                event.priority.value,
                event.status.value,
                event.retry_count,
                event.max_retries,
            )

    async def get(self, event_id: str) -> Event | None:
        async with self._session_factory() as session:
            row = await session.fetchrow(
                "SELECT payload FROM events WHERE event_id = $1", event_id
            )
            if row:
                return Event.model_validate_json(row["payload"])
            return None

    async def list_events(
        self,
        filter_expr: EventFilter | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        async with self._session_factory() as session:
            rows = await session.fetch(
                "SELECT payload FROM events ORDER BY timestamp DESC LIMIT $1 OFFSET $2",
                limit,
                offset,
            )
            events = [Event.model_validate_json(r["payload"]) for r in rows]
        if filter_expr:
            events = self._filter_engine.filter_events(events, filter_expr)
        return events

    async def count(self, filter_expr: EventFilter | None = None) -> int:
        async with self._session_factory() as session:
            row = await session.fetchrow("SELECT COUNT(*) as cnt FROM events")
            return row["cnt"] if row else 0

    async def delete(self, event_id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                "DELETE FROM events WHERE event_id = $1", event_id
            )
            return result == "DELETE 1"

    async def clear(self) -> int:
        async with self._session_factory() as session:
            result = await session.execute("DELETE FROM events")
            return int(result.split()[-1]) if result else 0
