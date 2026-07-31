"""Audit — authentication, authorization, API usage, workflow execution, admin actions, config changes."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.enterprise.enums import AuditEventType


class AuditEvent:
    """Represents a single audit event."""

    __slots__ = (
        "id", "event_type", "actor", "details",
        "timestamp", "ip_address", "resource",
    )

    def __init__(
        self,
        event_type: AuditEventType,
        actor: str,
        details: dict[str, Any] | None = None,
        ip_address: str = "",
        resource: str = "",
    ) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.event_type = event_type
        self.actor = actor
        self.details = details or {}
        self.timestamp = time.time()
        self.ip_address = ip_address
        self.resource = resource

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "actor": self.actor,
            "details": self.details,
            "timestamp": self.timestamp,
            "ip_address": self.ip_address,
            "resource": self.resource,
        }


class AuditManager:
    """Manages audit events with thread-safe operations."""

    def __init__(self, max_events: int = 10000) -> None:
        self._events: list[AuditEvent] = []
        self._max_events = max_events
        self._lock = threading.RLock()

    def record(
        self,
        event_type: AuditEventType,
        actor: str,
        details: dict[str, Any] | None = None,
        ip_address: str = "",
        resource: str = "",
    ) -> AuditEvent:
        event = AuditEvent(event_type=event_type, actor=actor, details=details, ip_address=ip_address, resource=resource)
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]
        return event

    def get(self, event_id: str) -> AuditEvent | None:
        with self._lock:
            for e in self._events:
                if e.id == event_id:
                    return e
        return None

    def query(
        self,
        event_type: AuditEventType | None = None,
        actor: str | None = None,
        resource: str | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        with self._lock:
            results = self._events
            if event_type:
                results = [e for e in results if e.event_type == event_type]
            if actor:
                results = [e for e in results if e.actor == actor]
            if resource:
                results = [e for e in results if e.resource == resource]
            if since:
                results = [e for e in results if e.timestamp >= since]
            return results[-limit:]

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    def count_by_type(self) -> dict[str, int]:
        with self._lock:
            counts: dict[str, int] = {}
            for e in self._events:
                key = e.event_type.value
                counts[key] = counts.get(key, 0) + 1
            return counts

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
