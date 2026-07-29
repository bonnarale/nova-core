"""Tracing for the Future subsystem."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceSpan:
    span_id: str
    name: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = "ok"
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id, "name": self.name,
            "start_time": self.start_time, "end_time": self.end_time,
            "duration_ms": self.duration_ms, "status": self.status,
            "parent_id": self.parent_id, "metadata": self.metadata,
        }


class FutureTracer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._spans: list[TraceSpan] = []
        self._active_spans: dict[str, TraceSpan] = {}

    def start_span(self, name: str, parent_id: str | None = None, metadata: dict[str, Any] | None = None) -> str:
        span_id = str(uuid.uuid4())
        span = TraceSpan(
            span_id=span_id, name=name, start_time=time.perf_counter(),
            parent_id=parent_id, metadata=metadata or {},
        )
        with self._lock:
            self._active_spans[span_id] = span
        return span_id

    def end_span(self, span_id: str, status: str = "ok") -> TraceSpan | None:
        with self._lock:
            span = self._active_spans.pop(span_id, None)
            if not span:
                return None
            span.end_time = time.perf_counter()
            span.duration_ms = (span.end_time - span.start_time) * 1000
            span.status = status
            self._spans.append(span)
        return span

    def get_spans(self) -> list[TraceSpan]:
        return list(self._spans)

    def get_span(self, span_id: str) -> TraceSpan | None:
        for s in self._spans:
            if s.span_id == span_id:
                return s
        return None

    def get_spans_by_name(self, name: str) -> list[TraceSpan]:
        return [s for s in self._spans if s.name == name]

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()
            self._active_spans.clear()

    def summary(self) -> dict[str, Any]:
        names: dict[str, int] = {}
        for s in self._spans:
            names[s.name] = names.get(s.name, 0) + 1
        return {
            "total_spans": len(self._spans),
            "active_spans": len(self._active_spans),
            "by_name": names,
        }
