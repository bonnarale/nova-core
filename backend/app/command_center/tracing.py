from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any


class TracingManager:
    def __init__(self) -> None:
        self.spans: list[dict] = []
        self.traces: dict[str, list[str]] = {}

    def start_span(
        self,
        operation: str,
        parent_span_id: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        span_id = str(uuid.uuid4())
        trace_id: str | None = None

        if parent_span_id is not None:
            for tid, span_ids in self.traces.items():
                if parent_span_id in span_ids:
                    trace_id = tid
                    break

        if trace_id is None:
            trace_id = str(uuid.uuid4())
            self.traces[trace_id] = []

        span: dict[str, Any] = {
            "span_id": span_id,
            "trace_id": trace_id,
            "parent_span_id": parent_span_id,
            "operation": operation,
            "metadata": metadata or {},
            "status": "in_progress",
            "result": None,
            "start_time": time.time(),
            "end_time": None,
            "duration_ms": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        self.spans.append(span)
        self.traces[trace_id].append(span_id)
        return span

    def end_span(
        self, span_id: str, status: str = "completed", result: Any = None
    ) -> dict | None:
        for span in self.spans:
            if span["span_id"] == span_id:
                span["status"] = status
                span["result"] = result
                span["end_time"] = time.time()
                span["duration_ms"] = (span["end_time"] - span["start_time"]) * 1000
                span["ended_at"] = datetime.now(timezone.utc).isoformat()
                return span
        return None

    def get_trace(self, trace_id: str) -> list[dict]:
        span_ids = self.traces.get(trace_id, [])
        return [s for s in self.spans if s["span_id"] in span_ids]

    def get_span(self, span_id: str) -> dict | None:
        for span in self.spans:
            if span["span_id"] == span_id:
                return span
        return None

    def list_spans(
        self, operation: str | None = None, limit: int = 100
    ) -> list[dict]:
        items = self.spans
        if operation is not None:
            items = [s for s in items if s["operation"] == operation]
        return items[:limit]

    def to_dict(self) -> dict:
        return {
            "total_spans": len(self.spans),
            "total_traces": len(self.traces),
            "traces": {tid: list(sids) for tid, sids in self.traces.items()},
        }
