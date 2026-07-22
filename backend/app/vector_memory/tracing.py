"""Tracing for the Vector Memory module — trace operations and errors."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class VectorTrace:
    """A single trace entry for a vector memory operation."""
    span_id: str
    operation: str
    status: str  # "success" or "error"
    timestamp: str
    latency_ms: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorSpan:
    """A tracing span for a vector memory operation."""
    span_id: str
    operation: str
    start_time: float
    details: dict[str, Any]


class VectorTracer:
    """Tracer for vector memory operations."""

    def __init__(self, max_traces: int = 1000):
        self._lock = threading.Lock()
        self._max_traces = max_traces
        self._traces: list[VectorTrace] = []

    def start_span(self, operation: str, **details: Any) -> VectorSpan:
        import uuid
        span_id = str(uuid.uuid4())
        return VectorSpan(
            span_id=span_id,
            operation=operation,
            start_time=time.monotonic(),
            details=details,
        )

    def end_span(
        self,
        span: VectorSpan,
        error: bool = False,
        **extra_details: Any,
    ) -> VectorTrace:
        latency_ms = (time.monotonic() - span.start_time) * 1000
        details = dict(span.details)
        details.update(extra_details)

        trace = VectorTrace(
            span_id=span.span_id,
            operation=span.operation,
            status="error" if error else "success",
            timestamp=datetime.now(timezone.utc).isoformat(),
            latency_ms=round(latency_ms, 3),
            details=details,
        )

        if error:
            logger.error(
                "Vector trace error: operation=%s, latency=%.1fms",
                span.operation, latency_ms,
            )

        with self._lock:
            self._traces.append(trace)
            if len(self._traces) > self._max_traces:
                self._traces = self._traces[-self._max_traces:]

        return trace

    def get_traces(self, limit: int = 100) -> list[VectorTrace]:
        with self._lock:
            return self._traces[-limit:]

    def get_traces_by_operation(self, operation: str, limit: int = 100) -> list[tuple[int, VectorTrace]]:
        matching = []
        for i, t in enumerate(self._traces):
            if t.operation == operation:
                matching.append((i, t))
        return matching[-limit:]

    def get_error_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._traces if t.status == "error")

    def get_total_count(self) -> int:
        return len(self._traces)

    def reset(self) -> None:
        with self._lock:
            self._traces.clear()


_tracer_instance: VectorTracer | None = None


def get_vector_tracer() -> VectorTracer:
    global _tracer_instance
    if _tracer_instance is None:
        _tracer_instance = VectorTracer()
    return _tracer_instance
