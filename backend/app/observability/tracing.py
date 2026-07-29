"""Observability tracing — distributed tracing for all subsystems."""

from __future__ import annotations

import time
from typing import Any, Optional
from uuid import uuid4

from app.observability.models import TraceSpan


class ObservabilityTracer:
    """Tracer for observability operations — collects and queries trace spans."""

    def __init__(self, max_spans: int = 1000) -> None:
        self._max_spans = max_spans
        self._spans: list[TraceSpan] = []
        self._active_spans: dict[str, TraceSpan] = {}

    @property
    def span_count(self) -> int:
        return len(self._spans)

    def start_span(self, name: str, parent_id: str | None = None, trace_id: str | None = None) -> TraceSpan:
        span = TraceSpan(
            span_id=str(uuid4()),
            name=name,
            parent_id=parent_id,
            trace_id=trace_id or str(uuid4()),
            start_time=time.monotonic(),
        )
        self._active_spans[span.span_id] = span
        return span

    def end_span(self, span: TraceSpan) -> None:
        span.end_time = time.monotonic()
        span.duration_ms = (span.end_time - span.start_time) * 1000
        self._active_spans.pop(span.span_id, None)
        self._spans.append(span)
        if len(self._spans) > self._max_spans:
            self._spans = self._spans[-self._max_spans:]

    def get_traces(self, name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        spans = self._spans
        if name is not None:
            spans = [s for s in spans if s.name == name]
        return [s.to_dict() for s in spans[-limit:]]

    def get_span(self, span_id: str) -> TraceSpan | None:
        for span in self._spans:
            if span.span_id == span_id:
                return span
        return self._active_spans.get(span_id)

    def get_traces_by_trace_id(self, trace_id: str) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._spans if s.trace_id == trace_id]

    def clear(self) -> int:
        count = len(self._spans)
        self._spans.clear()
        self._active_spans.clear()
        return count

    def to_dict(self, limit: int = 100) -> dict[str, Any]:
        traces = self.get_traces(limit=limit)
        return {"traces": traces, "total": len(self._spans)}
