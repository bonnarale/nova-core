"""Event tracing — trace publication, dispatch, subscribers, retries, failures, latency."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EventTrace:
    """A single trace entry for an event operation."""
    trace_id: str
    event_id: str
    event_type: str
    operation: str
    status: str
    timestamp: str
    latency_ms: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceSpan:
    """An active trace span."""
    span_id: str
    event_id: str
    operation: str
    start_time: float
    details: dict[str, Any]


class EventTracer:
    """Traces event system operations."""

    def __init__(self, max_traces: int = 1000) -> None:
        self._lock = threading.Lock()
        self._max_traces = max_traces
        self._traces: list[EventTrace] = []

    def start_span(self, event_id: str, operation: str, **details: Any) -> TraceSpan:
        import uuid
        span_id = str(uuid.uuid4())
        return TraceSpan(
            span_id=span_id,
            event_id=event_id,
            operation=operation,
            start_time=time.monotonic(),
            details=details,
        )

    def end_span(
        self,
        span: TraceSpan,
        error: bool = False,
        **extra_details: Any,
    ) -> EventTrace:
        latency_ms = (time.monotonic() - span.start_time) * 1000
        details = dict(span.details)
        details.update(extra_details)

        trace = EventTrace(
            trace_id=span.span_id,
            event_id=span.event_id,
            event_type=details.get("event_type", ""),
            operation=span.operation,
            status="error" if error else "success",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_ms=round(latency_ms, 3),
            details=details,
        )

        if error:
            logger.error(
                "Event trace error: operation=%s event_id=%s latency=%.1fms",
                span.operation,
                span.event_id,
                latency_ms,
            )

        with self._lock:
            self._traces.append(trace)
            if len(self._traces) > self._max_traces:
                self._traces = self._traces[-self._max_traces:]

        return trace

    def trace_publication(self, event_id: str, event_type: str, **details: Any) -> TraceSpan:
        return self.start_span(event_id, "publish", event_type=event_type, **details)

    def trace_dispatch(self, event_id: str, handler_count: int, **details: Any) -> TraceSpan:
        return self.start_span(event_id, "dispatch", handler_count=handler_count, **details)

    def trace_subscriber(self, event_id: str, handler_name: str, **details: Any) -> TraceSpan:
        return self.start_span(event_id, "subscriber", handler_name=handler_name, **details)

    def trace_retry(self, event_id: str, retry_count: int, **details: Any) -> TraceSpan:
        return self.start_span(event_id, "retry", retry_count=retry_count, **details)

    def trace_failure(self, event_id: str, error: str, **details: Any) -> TraceSpan:
        return self.start_span(event_id, "failure", error=error, **details)

    def get_traces(self, limit: int = 100) -> list[EventTrace]:
        with self._lock:
            return list(self._traces[-limit:])

    def get_traces_by_event(self, event_id: str, limit: int = 100) -> list[EventTrace]:
        with self._lock:
            return [t for t in self._traces if t.event_id == event_id][-limit:]

    def get_traces_by_operation(self, operation: str, limit: int = 100) -> list[EventTrace]:
        with self._lock:
            return [t for t in self._traces if t.operation == operation][-limit:]

    def get_error_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._traces if t.status == "error")

    def get_total_count(self) -> int:
        return len(self._traces)

    def reset(self) -> None:
        with self._lock:
            self._traces.clear()


_tracer_instance: EventTracer | None = None


def get_event_tracer() -> EventTracer:
    global _tracer_instance
    if _tracer_instance is None:
        _tracer_instance = EventTracer()
    return _tracer_instance
