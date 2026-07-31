"""Observability metrics — singleton metrics collector for all subsystems."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.observability.models import MetricPoint, MetricType


class ObservabilityMetrics:
    """Thread-safe singleton tracking observability metrics."""

    _instance: ObservabilityMetrics | None = None
    _lock = threading.Lock()

    def __new__(cls) -> ObservabilityMetrics:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._metrics: list[MetricPoint] = []
        self._started_at = time.monotonic()

    def record_counter(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        key = name
        self._counters[key] = self._counters.get(key, 0.0) + value
        self._metrics.append(MetricPoint(
            name=name,
            metric_type=MetricType.COUNTER,
            value=self._counters[key],
            labels=labels or {},
            timestamp=time.time(),
        ))

    def record_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        self._gauges[name] = value
        self._metrics.append(MetricPoint(
            name=name,
            metric_type=MetricType.GAUGE,
            value=value,
            labels=labels or {},
            timestamp=time.time(),
        ))

    def record_histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)
        self._metrics.append(MetricPoint(
            name=name,
            metric_type=MetricType.HISTOGRAM,
            value=value,
            labels=labels or {},
            timestamp=time.time(),
        ))

    def get_counter(self, name: str) -> float:
        return self._counters.get(name, 0.0)

    def get_gauge(self, name: str) -> float:
        return self._gauges.get(name, 0.0)

    def get_histogram(self, name: str) -> list[float]:
        return list(self._histograms.get(name, []))

    def get_histogram_stats(self, name: str) -> dict[str, float]:
        values = self._histograms.get(name, [])
        if not values:
            return {"count": 0, "min": 0.0, "max": 0.0, "mean": 0.0, "sum": 0.0}
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "sum": sum(values),
        }

    def get_metric(self, name: str) -> MetricPoint | None:
        for m in reversed(self._metrics):
            if m.name == name:
                return m
        return None

    def get_all_metrics(self) -> list[MetricPoint]:
        return list(self._metrics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: self.get_histogram_stats(k) for k in self._histograms},
            "total_metric_points": len(self._metrics),
        }

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._started_at

    @property
    def metric_count(self) -> int:
        return len(self._metrics)

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._metrics.clear()
        self._started_at = time.monotonic()

    @classmethod
    def reset_singleton(cls) -> None:
        with cls._lock:
            cls._instance = None


def get_observability_metrics() -> ObservabilityMetrics:
    return ObservabilityMetrics()
