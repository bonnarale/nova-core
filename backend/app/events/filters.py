"""Event filtering — match events against filter criteria."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.events.schemas import Event, EventFilter, EventPriority


class EventFilterEngine:
    """Evaluates events against filter expressions."""

    def matches(self, event: Event, filter_expr: EventFilter) -> bool:
        if not filter_expr:
            return True
        if filter_expr.event_types and event.event_type not in filter_expr.event_types:
            return False
        if filter_expr.sources and event.source not in filter_expr.sources:
            return False
        if filter_expr.user_ids and event.user_id not in filter_expr.user_ids:
            return False
        if filter_expr.session_ids and event.session_id not in filter_expr.session_ids:
            return False
        if filter_expr.correlation_ids and event.correlation_id not in filter_expr.correlation_ids:
            return False
        if filter_expr.aggregate_ids and event.aggregate_id not in filter_expr.aggregate_ids:
            return False
        if filter_expr.time_from and event.timestamp < filter_expr.time_from:
            return False
        if filter_expr.time_to and event.timestamp > filter_expr.time_to:
            return False
        if filter_expr.priority_min:
            priority_order = {
                EventPriority.LOW: 0,
                EventPriority.NORMAL: 1,
                EventPriority.HIGH: 2,
                EventPriority.CRITICAL: 3,
            }
            event_prio = priority_order.get(event.priority, 1)
            min_prio = priority_order.get(filter_expr.priority_min, 0)
            if event_prio < min_prio:
                return False
        return True

    def filter_events(
        self,
        events: list[Event],
        filter_expr: EventFilter,
    ) -> list[Event]:
        return [e for e in events if self.matches(e, filter_expr)]

    def matches_type(self, event: Event, event_type: str) -> bool:
        if event_type == "*":
            return True
        return event.event_type == event_type

    def matches_source(self, event: Event, source: str) -> bool:
        return event.source == source

    def matches_session(self, event: Event, session_id: str) -> bool:
        return event.session_id == session_id

    def matches_user(self, event: Event, user_id: str) -> bool:
        return event.user_id == user_id

    def matches_correlation(self, event: Event, correlation_id: str) -> bool:
        return event.correlation_id == correlation_id

    def matches_aggregate(self, event: Event, aggregate_id: str) -> bool:
        return event.aggregate_id == aggregate_id

    def matches_time_range(
        self,
        event: Event,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
    ) -> bool:
        if time_from and event.timestamp < time_from:
            return False
        if time_to and event.timestamp > time_to:
            return False
        return True
