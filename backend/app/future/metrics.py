"""Metrics collection for the Future subsystem."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: float
    tags: dict[str, str] = field(default_factory=dict)


class FutureMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._points: dict[str, list[MetricPoint]] = defaultdict(list)

    def record(self, name: str, value: float = 1.0, tags: dict[str, str] | None = None) -> None:
        point = MetricPoint(name=name, value=value, timestamp=time.perf_counter(), tags=tags or {})
        with self._lock:
            self._points[name].append(point)

    def increment(self, name: str, tags: dict[str, str] | None = None) -> None:
        self.record(name, 1.0, tags)

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        self.record(name, value, tags)

    def count(self, name: str) -> int:
        return len(self._points.get(name, []))

    def sum_values(self, name: str) -> float:
        return sum(p.value for p in self._points.get(name, []))

    def get_points(self, name: str) -> list[MetricPoint]:
        return list(self._points.get(name, []))

    def all_names(self) -> list[str]:
        return list(self._points.keys())

    def reset(self) -> None:
        with self._lock:
            self._points.clear()

    def summary(self) -> dict[str, Any]:
        return {
            "metric_names": self.all_names(),
            "total_points": sum(len(pts) for pts in self._points.values()),
            "by_name": {name: len(pts) for name, pts in self._points.items()},
        }


_feature_usage: FutureMetrics | None = None
_experiment_metrics: FutureMetrics | None = None
_compatibility_metrics: FutureMetrics | None = None
_migration_metrics: FutureMetrics | None = None
_deprecation_metrics: FutureMetrics | None = None


def get_feature_metrics() -> FutureMetrics:
    global _feature_usage
    if _feature_usage is None:
        _feature_usage = FutureMetrics()
    return _feature_usage


def get_experiment_metrics() -> FutureMetrics:
    global _experiment_metrics
    if _experiment_metrics is None:
        _experiment_metrics = FutureMetrics()
    return _experiment_metrics


def get_compatibility_metrics() -> FutureMetrics:
    global _compatibility_metrics
    if _compatibility_metrics is None:
        _compatibility_metrics = FutureMetrics()
    return _compatibility_metrics


def get_migration_metrics() -> FutureMetrics:
    global _migration_metrics
    if _migration_metrics is None:
        _migration_metrics = FutureMetrics()
    return _migration_metrics


def get_deprecation_metrics() -> FutureMetrics:
    global _deprecation_metrics
    if _deprecation_metrics is None:
        _deprecation_metrics = FutureMetrics()
    return _deprecation_metrics
