"""RAG tracing — trace retrieval pipeline execution."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID, uuid4


@dataclass
class RAGSpan:
    span_id: UUID = field(default_factory=uuid4)
    trace_id: UUID = field(default_factory=uuid4)
    name: str = ""
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

    def add_event(self, name: str, attributes: Optional[dict[str, Any]] = None) -> None:
        self.events.append({"name": name, "attributes": attributes or {}, "timestamp": time.time()})

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": str(self.span_id),
            "trace_id": str(self.trace_id),
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events,
            "error": self.error,
        }


@dataclass
class RAGTrace:
    trace_id: UUID = field(default_factory=uuid4)
    query: str = ""
    rewritten_query: Optional[str] = None
    embedding_provider: str = ""
    chunks_retrieved: int = 0
    chunks_reranked: int = 0
    spans: list[RAGSpan] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    status: str = "pending"
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def finish(self, status: str = "completed", error: Optional[str] = None) -> None:
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        if error:
            self.error = error

    def add_span(self, span: RAGSpan) -> None:
        self.spans.append(span)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": str(self.trace_id),
            "query": self.query,
            "rewritten_query": self.rewritten_query,
            "embedding_provider": self.embedding_provider,
            "chunks_retrieved": self.chunks_retrieved,
            "chunks_reranked": self.chunks_reranked,
            "spans": [s.to_dict() for s in self.spans],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
        }


class RAGTracer:
    """Traces RAG pipeline operations."""

    def __init__(self, max_traces: int = 500) -> None:
        self._max_traces = max_traces
        self._traces: list[RAGTrace] = []

    def start_trace(self, query: str, metadata: Optional[dict[str, Any]] = None) -> RAGTrace:
        trace = RAGTrace(query=query, metadata=metadata or {})
        self._traces.append(trace)
        if len(self._traces) > self._max_traces:
            self._traces = self._traces[-self._max_traces // 2:]
        return trace

    def start_span(self, name: str, trace: RAGTrace) -> RAGSpan:
        span = RAGSpan(trace_id=trace.trace_id, name=name)
        trace.add_span(span)
        return span

    def finish_span(self, span: RAGSpan, status: str = "completed", error: Optional[str] = None) -> None:
        span.finish(status, error)

    def finish_trace(self, trace: RAGTrace, status: str = "completed", error: Optional[str] = None) -> None:
        trace.finish(status, error)

    def get_trace(self, trace_id: UUID) -> Optional[RAGTrace]:
        for t in self._traces:
            if t.trace_id == trace_id:
                return t
        return None

    def get_traces(self, limit: int = 100) -> list[RAGTrace]:
        return list(self._traces[-limit:])

    def get_trace_count(self) -> int:
        return len(self._traces)

    def clear(self) -> int:
        count = len(self._traces)
        self._traces.clear()
        return count

    def to_dict(self) -> dict[str, Any]:
        return {"trace_count": len(self._traces), "max_traces": self._max_traces}


def get_rag_tracer(max_traces: int = 500) -> RAGTracer:
    return RAGTracer(max_traces=max_traces)
