"""Observability profiler — performance profiling for subsystems."""

from __future__ import annotations

import threading
import time
from typing import Any
from uuid import uuid4


class ProfileSpan:
    """A single profiling span measuring execution time."""

    def __init__(self, name: str, category: str = "") -> None:
        self.span_id = str(uuid4())
        self.name = name
        self.category = category
        self.start_time = time.monotonic()
        self.end_time: float = 0.0
        self.duration_ms: float = 0.0
        self.metadata: dict[str, Any] = {}

    def finish(self) -> None:
        self.end_time = time.monotonic()
        self.duration_ms = (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "category": self.category,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


class Profiler:
    """Performance profiler collecting execution timing data."""

    def __init__(self, max_spans: int = 1000) -> None:
        self._max_spans = max_spans
        self._spans: list[ProfileSpan] = []
        self._active_spans: dict[str, ProfileSpan] = {}
        self._lock = threading.Lock()

    @property
    def span_count(self) -> int:
        return len(self._spans)

    def start(self, name: str, category: str = "") -> ProfileSpan:
        span = ProfileSpan(name=name, category=category)
        with self._lock:
            self._active_spans[span.span_id] = span
        return span

    def stop(self, span: ProfileSpan) -> None:
        span.finish()
        with self._lock:
            self._active_spans.pop(span.span_id, None)
            self._spans.append(span)
            if len(self._spans) > self._max_spans:
                self._spans = self._spans[-self._max_spans:]

    def get_spans(self, category: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        spans = self._spans
        if category:
            spans = [s for s in spans if s.category == category]
        return [s.to_dict() for s in spans[-limit:]]

    def get_slowest(self, limit: int = 10) -> list[dict[str, Any]]:
        sorted_spans = sorted(self._spans, key=lambda s: s.duration_ms, reverse=True)
        return [s.to_dict() for s in sorted_spans[:limit]]

    def get_by_category(self) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for span in self._spans:
            cat = span.category or "uncategorized"
            if cat not in result:
                result[cat] = []
            result[cat].append(span.to_dict())
        return result

    def clear(self) -> int:
        with self._lock:
            count = len(self._spans)
            self._spans.clear()
            self._active_spans.clear()
            return count

    def to_dict(self, limit: int = 100) -> dict[str, Any]:
        spans = self.get_spans(limit=limit)
        return {"spans": spans, "total": len(self._spans)}
