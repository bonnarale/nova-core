"""Plugin tracer — tracks plugin-specific traces."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any


class PluginSpan:
    """A single trace span for plugin operations."""

    def __init__(self, name: str, trace_id: str = "", parent_id: str | None = None) -> None:
        self.span_id = uuid.uuid4().hex[:16]
        self.name = name
        self.trace_id = trace_id or uuid.uuid4().hex
        self.parent_id = parent_id
        self.start_time = time.time()
        self.end_time: float = 0.0
        self.duration_ms: float = 0.0
        self.status = "ok"
        self.error: str | None = None
        self.attributes: dict[str, Any] = {}

    def end(self) -> None:
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000

    def set_error(self, error: str) -> None:
        self.status = "error"
        self.error = error

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
            "attributes": self.attributes,
        }


class PluginTracer:
    """Distributed tracing for plugin operations."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._spans: list[dict[str, Any]] = []
        self._active_spans: dict[str, PluginSpan] = {}
        self._trace_count = 0

    def start_span(self, name: str, trace_id: str = "", parent_id: str | None = None) -> PluginSpan:
        span = PluginSpan(name=name, trace_id=trace_id, parent_id=parent_id)
        with self._lock:
            self._active_spans[span.span_id] = span
        return span

    def end_span(self, span: PluginSpan) -> None:
        span.end()
        with self._lock:
            self._active_spans.pop(span.span_id, None)
            self._spans.append(span.to_dict())
            self._trace_count += 1

    def get_span(self, span_id: str) -> PluginSpan | None:
        with self._lock:
            return self._active_spans.get(span_id)

    def get_traces(self, name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            spans = list(self._spans)
        if name:
            spans = [s for s in spans if s["name"] == name]
        return spans[-limit:]

    def get_statistics(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._spans)
            errors = sum(1 for s in self._spans if s["status"] == "error")
            durations = [s["duration_ms"] for s in self._spans if s["duration_ms"] > 0]
        return {
            "total_spans": total,
            "error_spans": errors,
            "active_spans": len(self._active_spans),
            "average_duration_ms": sum(durations) / len(durations) if durations else 0.0,
        }

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()
            self._active_spans.clear()
            self._trace_count = 0
