"""Performance metrics collection."""

from __future__ import annotations

import threading
import time
from typing import Any


class PerformanceMetrics:
    """Snapshot of performance metrics."""

    __slots__ = (
        "latency",
        "throughput",
        "cache_hit_ratio",
        "query_time",
        "execution_time",
        "resource_utilization",
    )

    def __init__(
        self,
        latency: dict[str, float] | None = None,
        throughput: dict[str, float] | None = None,
        cache_hit_ratio: float = 0.0,
        query_time: float = 0.0,
        execution_time: float = 0.0,
        resource_utilization: dict[str, float] | None = None,
    ) -> None:
        self.latency = latency or {}
        self.throughput = throughput or {}
        self.cache_hit_ratio = cache_hit_ratio
        self.query_time = query_time
        self.execution_time = execution_time
        self.resource_utilization = resource_utilization or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "latency": dict(self.latency),
            "throughput": dict(self.throughput),
            "cache_hit_ratio": self.cache_hit_ratio,
            "query_time": self.query_time,
            "execution_time": self.execution_time,
            "resource_utilization": dict(self.resource_utilization),
        }


class PerformanceMetricsCollector:
    """Thread-safe collector for performance metrics."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._latency: dict[str, list[float]] = {}
        self._throughput: dict[str, float] = {}
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._query_times: list[float] = []
        self._execution_times: list[float] = []
        self._start_time: float = 0.0

    def start(self) -> None:
        with self._lock:
            self._start_time = time.time()

    def record_latency(self, operation: str, duration_ms: float) -> None:
        with self._lock:
            self._latency.setdefault(operation, []).append(duration_ms)

    def record_throughput(self, operation: str, count: float) -> None:
        with self._lock:
            self._throughput[operation] = count

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    def record_query_time(self, duration_ms: float) -> None:
        with self._lock:
            self._query_times.append(duration_ms)

    def record_execution_time(self, duration_ms: float) -> None:
        with self._lock:
            self._execution_times.append(duration_ms)

    def snapshot(self) -> PerformanceMetrics:
        with self._lock:
            avg_latency: dict[str, float] = {}
            for op, times in self._latency.items():
                avg_latency[op] = sum(times) / len(times) if times else 0.0

            total_cache = self._cache_hits + self._cache_misses
            cache_ratio = self._cache_hits / total_cache if total_cache > 0 else 0.0
            avg_query = sum(self._query_times) / len(self._query_times) if self._query_times else 0.0
            avg_exec = sum(self._execution_times) / len(self._execution_times) if self._execution_times else 0.0
            uptime = time.time() - self._start_time if self._start_time else 0.0

            return PerformanceMetrics(
                latency=avg_latency,
                throughput=dict(self._throughput),
                cache_hit_ratio=cache_ratio,
                query_time=avg_query,
                execution_time=avg_exec,
                resource_utilization={"uptime_seconds": uptime},
            )

    def get_latency_stats(self) -> dict[str, dict[str, float]]:
        with self._lock:
            stats: dict[str, dict[str, float]] = {}
            for op, times in self._latency.items():
                if times:
                    sorted_t = sorted(times)
                    stats[op] = {
                        "count": float(len(times)),
                        "min": sorted_t[0],
                        "max": sorted_t[-1],
                        "avg": sum(times) / len(times),
                        "p50": sorted_t[len(sorted_t) // 2],
                        "p95": sorted_t[int(len(sorted_t) * 0.95)] if len(sorted_t) > 1 else sorted_t[0],
                        "p99": sorted_t[int(len(sorted_t) * 0.99)] if len(sorted_t) > 1 else sorted_t[0],
                    }
            return stats
