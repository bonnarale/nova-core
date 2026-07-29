"""Event middleware — logging, tracing, metrics, validation, retry, authorization, transformation."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.events.base import EventMiddleware
from app.events.schemas import Event, EventPriority, EventStatus

logger = logging.getLogger(__name__)


class LoggingMiddleware(EventMiddleware):
    """Logs event publish and completion."""

    def __init__(self, log_level: int = logging.INFO) -> None:
        self._log_level = log_level

    @property
    def name(self) -> str:
        return "logging"

    @property
    def priority(self) -> int:
        return 100

    async def before_publish(self, event: Event) -> Event:
        logger.log(
            self._log_level,
            "Publishing event: type=%s id=%s aggregate=%s",
            event.event_type,
            event.event_id,
            event.aggregate_id,
        )
        return event

    async def after_publish(self, event: Event, result: Event | None = None) -> None:
        logger.log(
            self._log_level,
            "Event published: type=%s id=%s status=%s",
            event.event_type,
            event.event_id,
            (result or event).status.value,
        )

    async def on_error(self, event: Event, error: Exception) -> bool:
        logger.error(
            "Event error: type=%s id=%s error=%s",
            event.event_type,
            event.event_id,
            error,
        )
        return True


class TracingMiddleware(EventMiddleware):
    """Traces event publish timing."""

    @property
    def name(self) -> str:
        return "tracing"

    @property
    def priority(self) -> int:
        return 90

    def __init__(self) -> None:
        self._spans: dict[str, float] = {}

    async def before_publish(self, event: Event) -> Event:
        self._spans[event.event_id] = time.monotonic()
        event.metadata["trace_start"] = datetime.now(timezone.utc).isoformat()
        return event

    async def after_publish(self, event: Event, result: Event | None = None) -> None:
        start = self._spans.pop(event.event_id, None)
        if start is not None:
            latency_ms = (time.monotonic() - start) * 1000
            event.metadata["trace_latency_ms"] = round(latency_ms, 3)
            event.metadata["trace_end"] = datetime.now(timezone.utc).isoformat()

    async def on_error(self, event: Event, error: Exception) -> bool:
        self._spans.pop(event.event_id, None)
        return True

    def get_spans(self) -> dict[str, float]:
        return dict(self._spans)


class MetricsMiddleware(EventMiddleware):
    """Collects event metrics."""

    @property
    def name(self) -> str:
        return "metrics"

    @property
    def priority(self) -> int:
        return 80

    def __init__(self) -> None:
        self._published: int = 0
        self._completed: int = 0
        self._failed: int = 0
        self._latencies: list[float] = []

    async def before_publish(self, event: Event) -> Event:
        self._published += 1
        event.metadata["metrics_start"] = time.monotonic()
        return event

    async def after_publish(self, event: Event, result: Event | None = None) -> None:
        self._completed += 1
        start = event.metadata.get("metrics_start")
        if start is not None:
            latency = (time.monotonic() - start) * 1000
            self._latencies.append(latency)

    async def on_error(self, event: Event, error: Exception) -> bool:
        self._failed += 1
        return True

    def get_metrics(self) -> dict[str, Any]:
        avg_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        return {
            "total_published": self._published,
            "total_completed": self._completed,
            "total_failed": self._failed,
            "average_latency_ms": round(avg_latency, 3),
            "latency_samples": len(self._latencies),
        }

    def reset(self) -> None:
        self._published = 0
        self._completed = 0
        self._failed = 0
        self._latencies.clear()


class ValidationMiddleware(EventMiddleware):
    """Validates events before publishing."""

    def __init__(self, required_fields: list[str] | None = None) -> None:
        self._required_fields = required_fields or ["event_type", "event_id"]

    @property
    def name(self) -> str:
        return "validation"

    @property
    def priority(self) -> int:
        return 70

    async def before_publish(self, event: Event) -> Event:
        for field_name in self._required_fields:
            value = getattr(event, field_name, None)
            if not value:
                raise ValueError(f"Event missing required field: {field_name}")
        return event

    async def after_publish(self, event: Event, result: Event | None = None) -> None:
        pass

    async def on_error(self, event: Event, error: Exception) -> bool:
        return True


class RetryMiddleware(EventMiddleware):
    """Handles retry logic for failed events."""

    def __init__(self, max_retries: int = 3, base_delay: float = 0.1) -> None:
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._retry_counts: dict[str, int] = {}

    @property
    def name(self) -> str:
        return "retry"

    @property
    def priority(self) -> int:
        return 60

    async def before_publish(self, event: Event) -> Event:
        return event

    async def after_publish(self, event: Event, result: Event | None = None) -> None:
        self._retry_counts.pop(event.event_id, None)

    async def on_error(self, event: Event, error: Exception) -> bool:
        count = self._retry_counts.get(event.event_id, 0)
        if count < self._max_retries:
            self._retry_counts[event.event_id] = count + 1
            event.retry_count = count + 1
            event.status = EventStatus.RETRYING
            return True
        return False

    def get_retry_count(self, event_id: str) -> int:
        return self._retry_counts.get(event_id, 0)


class AuthorizationMiddleware(EventMiddleware):
    """Authorizes events based on metadata."""

    def __init__(self, allowed_sources: list[str] | None = None) -> None:
        self._allowed_sources = allowed_sources

    @property
    def name(self) -> str:
        return "authorization"

    @property
    def priority(self) -> int:
        return 50

    async def before_publish(self, event: Event) -> Event:
        if self._allowed_sources and event.source not in self._allowed_sources:
            raise PermissionError(
                f"Source '{event.source}' not authorized. Allowed: {self._allowed_sources}"
            )
        return event

    async def after_publish(self, event: Event, result: Event | None = None) -> None:
        pass

    async def on_error(self, event: Event, error: Exception) -> bool:
        return True


class TransformationMiddleware(EventMiddleware):
    """Transforms event payloads before publishing."""

    def __init__(self, transformations: dict[str, Any] | None = None) -> None:
        self._transformations = transformations or {}

    @property
    def name(self) -> str:
        return "transformation"

    @property
    def priority(self) -> int:
        return 40

    async def before_publish(self, event: Event) -> Event:
        transform = self._transformations.get(event.event_type)
        if callable(transform):
            event = transform(event)
        return event

    async def after_publish(self, event: Event, result: Event | None = None) -> None:
        pass

    async def on_error(self, event: Event, error: Exception) -> bool:
        return True
