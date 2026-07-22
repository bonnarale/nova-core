"""Execution tracing for agent calls and delegation."""

from __future__ import annotations

import datetime
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceSpan:
    """A single span in an execution trace."""

    span_id: str = ""
    parent_span_id: str | None = None
    trace_id: str = ""
    agent_id: str = ""
    task: str = ""
    task_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = "unknown"
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    child_spans: list[TraceSpan] = field(default_factory=list)

    def close(self, status: str = "success", output: dict | None = None, error: str | None = None) -> None:
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        if output:
            self.output = output
        self.error = error


class Tracer:
    """Collects execution traces for agent activity."""

    def __init__(self) -> None:
        self._spans: dict[str, TraceSpan] = {}
        self._traces: dict[str, list[TraceSpan]] = {}

    def start_span(
        self,
        agent_id: str,
        task: str,
        task_id: str = "",
        parent_span_id: str | None = None,
        trace_id: str | None = None,
        **input_data: Any,
    ) -> TraceSpan:
        span_id = str(uuid.uuid4())
        actual_trace_id = trace_id or span_id
        span = TraceSpan(
            span_id=span_id,
            parent_span_id=parent_span_id,
            trace_id=actual_trace_id,
            agent_id=agent_id,
            task=task,
            task_id=task_id,
            start_time=time.time(),
            input=input_data,
        )
        self._spans[span_id] = span
        if actual_trace_id not in self._traces:
            self._traces[actual_trace_id] = []
        self._traces[actual_trace_id].append(span)

        if parent_span_id and parent_span_id in self._spans:
            parent = self._spans[parent_span_id]
            parent.child_spans.append(span)

        return span

    def get_span(self, span_id: str) -> TraceSpan | None:
        return self._spans.get(span_id)

    def get_trace(self, trace_id: str) -> list[TraceSpan]:
        return self._traces.get(trace_id, [])

    def get_all_traces(self) -> dict[str, list[TraceSpan]]:
        return dict(self._traces)

    def clear(self) -> None:
        self._spans.clear()
        self._traces.clear()

    def to_dict(self) -> list[dict[str, Any]]:
        def _span_dict(s: TraceSpan) -> dict[str, Any]:
            return {
                "span_id": s.span_id,
                "parent_span_id": s.parent_span_id,
                "trace_id": s.trace_id,
                "agent_id": s.agent_id,
                "task": s.task,
                "task_id": s.task_id,
                "duration_ms": round(s.duration_ms, 2),
                "status": s.status,
                "error": s.error,
                "start_time": datetime.datetime.fromtimestamp(s.start_time, tz=datetime.timezone.utc).isoformat(),
                "end_time": datetime.datetime.fromtimestamp(s.end_time, tz=datetime.timezone.utc).isoformat() if s.end_time else None,
                "child_spans": [_span_dict(c) for c in s.child_spans],
            }

        result = []
        for trace_id, spans in self._traces.items():
            for span in spans:
                if span.parent_span_id is None:
                    result.append(_span_dict(span))
        return result
