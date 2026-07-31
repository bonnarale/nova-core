"""Workflow tracing — distributed tracing for workflow operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4


class WorkflowTraceSpan:
    """A single tracing span for workflow operations."""

    def __init__(self, name: str, parent_id: str | None = None) -> None:
        self.span_id = str(uuid4())
        self.name = name
        self.parent_id = parent_id
        self.start_time = datetime.now(timezone.utc)
        self.end_time: Optional[datetime] = None
        self.duration_ms: Optional[float] = None
        self.attributes: dict[str, Any] = {}
        self.status = "ok"
        self.error: Optional[str] = None

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_error(self, error: str) -> None:
        self.error = error
        self.status = "error"

    def finish(self) -> None:
        self.end_time = datetime.now(timezone.utc)
        if self.start_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "status": self.status,
            "error": self.error,
        }


class WorkflowTracer:
    """Tracer for workflow operations — collects and queries trace spans."""

    def __init__(self, max_spans: int = 1000) -> None:
        self._max_spans = max_spans
        self._spans: list[WorkflowTraceSpan] = []
        self._active_spans: dict[str, WorkflowTraceSpan] = {}

    @property
    def span_count(self) -> int:
        return len(self._spans)

    def start_span(self, name: str, parent_id: str | None = None) -> WorkflowTraceSpan:
        span = WorkflowTraceSpan(name=name, parent_id=parent_id)
        self._active_spans[span.span_id] = span
        return span

    def end_span(self, span: WorkflowTraceSpan) -> None:
        span.finish()
        self._active_spans.pop(span.span_id, None)
        self._spans.append(span)
        if len(self._spans) > self._max_spans:
            self._spans = self._spans[-self._max_spans:]

    def get_traces(self, name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        spans = self._spans
        if name is not None:
            spans = [s for s in spans if s.name == name]
        return [s.to_dict() for s in spans[-limit:]]

    def get_span(self, span_id: str) -> WorkflowTraceSpan | None:
        for span in self._spans:
            if span.span_id == span_id:
                return span
        return self._active_spans.get(span_id)

    def clear(self) -> int:
        count = len(self._spans)
        self._spans.clear()
        self._active_spans.clear()
        return count

    def to_dict(self, limit: int = 100) -> dict[str, Any]:
        traces = self.get_traces(limit=limit)
        return {"traces": traces, "total": len(self._spans)}
