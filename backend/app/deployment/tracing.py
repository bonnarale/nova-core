"""Request tracing for the Deployment subsystem."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class DeploymentTracer:
    """Traces deployment operations."""

    def __init__(self, max_spans: int = 5000) -> None:
        self._lock = threading.Lock()
        self._spans: list[dict[str, Any]] = []
        self._max_spans = max_spans

    def start_trace(self, name: str = "", trace_id: str = "") -> str:
        tid = trace_id or str(uuid.uuid4())
        span = {
            "trace_id": tid,
            "name": name,
            "started_at": time.time(),
            "finished_at": 0.0,
            "duration_ms": 0.0,
            "status": "started",
            "spans": [],
        }
        with self._lock:
            self._spans.append(span)
            if len(self._spans) > self._max_spans:
                self._spans = self._spans[-self._max_spans // 2:]
        return tid

    def add_span(self, trace_id: str, name: str) -> None:
        with self._lock:
            for s in reversed(self._spans):
                if s["trace_id"] == trace_id:
                    s["spans"].append({
                        "name": name,
                        "started_at": time.time(),
                        "finished_at": 0.0,
                        "duration_ms": 0.0,
                    })
                    break

    def end_span(self, trace_id: str, name: str) -> None:
        with self._lock:
            for s in reversed(self._spans):
                if s["trace_id"] == trace_id:
                    for sp in reversed(s["spans"]):
                        if sp["name"] == name and sp["finished_at"] == 0.0:
                            sp["finished_at"] = time.time()
                            sp["duration_ms"] = round(
                                (sp["finished_at"] - sp["started_at"]) * 1000, 2
                            )
                            break
                    break

    def finish_trace(self, trace_id: str, status: str = "ok") -> None:
        with self._lock:
            for s in reversed(self._spans):
                if s["trace_id"] == trace_id:
                    s["finished_at"] = time.time()
                    s["duration_ms"] = round(
                        (s["finished_at"] - s["started_at"]) * 1000, 2
                    )
                    s["status"] = status
                    break

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        with self._lock:
            for s in reversed(self._spans):
                if s["trace_id"] == trace_id:
                    return dict(s)
        return None

    def get_recent_traces(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(s) for s in self._spans[-limit:]]

    def get_statistics(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._spans)
            completed = sum(1 for s in self._spans if s["status"] != "started")
            failed = sum(1 for s in self._spans if s["status"] == "error")
            durations = [s["duration_ms"] for s in self._spans if s["duration_ms"] > 0]
            avg = sum(durations) / len(durations) if durations else 0.0
            return {
                "total_traces": total,
                "completed": completed,
                "failed": failed,
                "average_duration_ms": round(avg, 2),
            }

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()
