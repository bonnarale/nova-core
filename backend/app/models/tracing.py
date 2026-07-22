"""Tracing for model provider requests."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class Span:
    """A single trace span."""

    span_id: UUID = field(default_factory=uuid4)
    trace_id: UUID = field(default_factory=uuid4)
    parent_span_id: Optional[UUID] = None
    name: str = ""
    provider: str = ""
    model: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    status: str = "pending"
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def finish(self, status: str = "completed", error: Optional[str] = None) -> None:
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        if error:
            self.error = error
            self.events.append({"name": "error", "message": error, "timestamp": time.time()})

    def add_event(self, name: str, attributes: Optional[dict[str, Any]] = None) -> None:
        self.events.append({"name": name, "attributes": attributes or {}, "timestamp": time.time()})

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": str(self.span_id),
            "trace_id": str(self.trace_id),
            "parent_span_id": str(self.parent_span_id) if self.parent_span_id else None,
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events,
            "error": self.error,
        }


@dataclass
class Trace:
    """A complete trace of a request."""

    trace_id: UUID = field(default_factory=uuid4)
    spans: list[Span] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def finish(self, status: str = "completed") -> None:
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status

    def add_span(self, span: Span) -> None:
        self.spans.append(span)

    def get_span(self, span_id: UUID) -> Optional[Span]:
        for span in self.spans:
            if span.span_id == span_id:
                return span
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": str(self.trace_id),
            "spans": [s.to_dict() for s in self.spans],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "metadata": self.metadata,
        }


class ModelTracer:
    """Traces model provider requests."""

    def __init__(self, max_traces: int = 1000) -> None:
        self._max_traces = max_traces
        self._traces: list[Trace] = []
        self._active_traces: dict[str, Trace] = {}
        self._active_spans: dict[str, Span] = {}

    def start_trace(self, name: str, metadata: Optional[dict[str, Any]] = None) -> Trace:
        trace = Trace(metadata=metadata or {})
        span = Span(name=name, trace_id=trace.trace_id)
        trace.add_span(span)
        self._traces.append(trace)
        if len(self._traces) > self._max_traces:
            self._traces = self._traces[-self._max_traces // 2:]
        return trace

    def start_span(
        self,
        name: str,
        trace: Trace,
        provider: str = "",
        model: str = "",
        parent_span_id: Optional[UUID] = None,
    ) -> Span:
        span = Span(
            name=name,
            trace_id=trace.trace_id,
            parent_span_id=parent_span_id,
            provider=provider,
            model=model,
        )
        trace.add_span(span)
        return span

    def finish_span(self, span: Span, status: str = "completed", error: Optional[str] = None) -> None:
        span.finish(status, error)

    def finish_trace(self, trace: Trace, status: str = "completed") -> None:
        trace.finish(status)

    def get_trace(self, trace_id: UUID) -> Optional[Trace]:
        for trace in self._traces:
            if trace.trace_id == trace_id:
                return trace
        return None

    def get_traces(self, limit: int = 100) -> list[Trace]:
        return list(self._traces[-limit:])

    def get_trace_count(self) -> int:
        return len(self._traces)

    def clear(self) -> int:
        count = len(self._traces)
        self._traces.clear()
        self._active_traces.clear()
        self._active_spans.clear()
        return count

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_count": len(self._traces),
            "max_traces": self._max_traces,
        }


def get_model_tracer(max_traces: int = 1000) -> ModelTracer:
    return ModelTracer(max_traces=max_traces)
