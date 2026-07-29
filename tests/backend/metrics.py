"""NOVA CORE Metrics Testing — Chapter 29.

Provides testing infrastructure for validating metrics collection,
aggregation, and reporting.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: float
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """Aggregated metric summary."""
    name: str
    count: int
    sum: float
    min: float
    max: float
    avg: float
    p50: float
    p95: float
    p99: float


class MetricsCollector:
    """Collect and aggregate metrics for testing."""

    def __init__(self) -> None:
        self._points: dict[str, list[MetricPoint]] = defaultdict(list)

    def record(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        point = MetricPoint(name=name, value=value, timestamp=time.perf_counter(), tags=tags or {})
        self._points[name].append(point)

    def get_points(self, name: str) -> list[MetricPoint]:
        return list(self._points.get(name, []))

    def summary(self, name: str) -> MetricSummary:
        points = self._points.get(name, [])
        if not points:
            return MetricSummary(name=name, count=0, sum=0, min=0, max=0, avg=0, p50=0, p95=0, p99=0)
        values = sorted(p.value for p in points)
        n = len(values)
        return MetricSummary(
            name=name,
            count=n,
            sum=sum(values),
            min=values[0],
            max=values[-1],
            avg=sum(values) / n,
            p50=values[int(n * 0.5)],
            p95=values[int(n * 0.95)],
            p99=values[int(n * 0.99)],
        )

    def all_summaries(self) -> dict[str, MetricSummary]:
        return {name: self.summary(name) for name in self._points}

    def count(self, name: str) -> int:
        return len(self._points.get(name, []))

    def reset(self) -> None:
        self._points.clear()


def assert_metric_recorded(collector: MetricsCollector, name: str, min_count: int = 1) -> None:
    """Assert that a metric has been recorded at least min_count times."""
    assert collector.count(name) >= min_count, f"Metric '{name}' has {collector.count(name)} records, expected >= {min_count}"


def assert_metric_value_in_range(
    collector: MetricsCollector, name: str, min_val: float, max_val: float
) -> None:
    """Assert that all values of a metric are within range."""
    points = collector.get_points(name)
    assert points, f"No points for metric '{name}'"
    for p in points:
        assert min_val <= p.value <= max_val, f"Metric '{name}' value {p.value} not in [{min_val}, {max_val}]"
