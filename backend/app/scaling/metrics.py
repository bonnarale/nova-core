"""Metrics collection for the Scaling subsystem."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app.scaling.models import ScalingMetrics

logger = logging.getLogger(__name__)


class ScalingMetricsCollector:
    """Collects scaling lifecycle metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests_per_second = 0.0
        self._active_workers = 0
        self._queue_depth = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._scaling_events = 0
        self._execution_throughput = 0.0
        self._resource_utilization = 0.0
        self._start_time = time.time()

    def record_request(self) -> None:
        with self._lock:
            self._requests_per_second += 1

    def set_active_workers(self, count: int) -> None:
        with self._lock:
            self._active_workers = count

    def set_queue_depth(self, depth: int) -> None:
        with self._lock:
            self._queue_depth = depth

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    def record_scaling_event(self) -> None:
        with self._lock:
            self._scaling_events += 1

    def set_execution_throughput(self, throughput: float) -> None:
        with self._lock:
            self._execution_throughput = throughput

    def set_resource_utilization(self, utilization: float) -> None:
        with self._lock:
            self._resource_utilization = utilization

    def get_statistics(self) -> dict[str, Any]:
        with self._lock:
            total_cache = self._cache_hits + self._cache_misses
            hit_ratio = self._cache_hits / total_cache if total_cache > 0 else 0.0
            return {
                "requests_per_second": round(self._requests_per_second, 2),
                "active_workers": self._active_workers,
                "queue_depth": self._queue_depth,
                "cache_hit_ratio": round(hit_ratio, 4),
                "scaling_events": self._scaling_events,
                "execution_throughput": round(self._execution_throughput, 2),
                "resource_utilization": round(self._resource_utilization, 2),
                "uptime_seconds": round(time.time() - self._start_time, 2),
            }

    def to_model(self) -> ScalingMetrics:
        stats = self.get_statistics()
        return ScalingMetrics(**stats)

    def reset(self) -> None:
        with self._lock:
            self._requests_per_second = 0.0
            self._active_workers = 0
            self._queue_depth = 0
            self._cache_hits = 0
            self._cache_misses = 0
            self._scaling_events = 0
            self._execution_throughput = 0.0
            self._resource_utilization = 0.0
            self._start_time = time.time()
