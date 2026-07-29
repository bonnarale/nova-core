"""Resilience tracing."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any


class ResilienceTracer:
    """Distributed tracing for resilience operations."""

    def __init__(self, max_traces: int = 1000) -> None:
        self._traces: list[dict[str, Any]] = []
        self._max_traces = max_traces
        self._lock = threading.RLock()

    def start_trace(self, operation: str, metadata: dict[str, Any] | None = None) -> str:
        trace_id = str(uuid.uuid4())[:12]
        with self._lock:
            self._traces.append({
                "trace_id": trace_id,
                "operation": operation,
                "start_time": time.time(),
                "end_time": None,
                "duration_ms": None,
                "status": "started",
                "metadata": metadata or {},
            })
            if len(self._traces) > self._max_traces:
                self._traces = self._traces[-self._max_traces:]
        return trace_id

    def finish_trace(self, trace_id: str, status: str = "completed", error: str | None = None) -> None:
        with self._lock:
            for trace in reversed(self._traces):
                if trace["trace_id"] == trace_id:
                    trace["end_time"] = time.time()
                    trace["duration_ms"] = (trace["end_time"] - trace["start_time"]) * 1000
                    trace["status"] = status
                    if error:
                        trace["error"] = error
                    break

    def get_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._traces[-limit:])

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        with self._lock:
            for trace in self._traces:
                if trace["trace_id"] == trace_id:
                    return dict(trace)
        return None

    def count(self) -> int:
        with self._lock:
            return len(self._traces)

    def clear(self) -> None:
        with self._lock:
            self._traces.clear()
