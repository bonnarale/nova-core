"""Metrics collection for the Vector Memory module."""

from __future__ import annotations

import logging
import statistics
import threading
from typing import Any

logger = logging.getLogger(__name__)


class VectorMetrics:
    """Collects and reports performance metrics for vector memory operations."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._vectors_stored: int = 0
        self._vectors_indexed: int = 0
        self._searches: int = 0
        self._retrieval_latencies: list[float] = []
        self._indexing_latencies: list[float] = []
        self._embedding_latencies: list[float] = []
        self._storage_usage_bytes: int = 0
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._consolidations_run: int = 0
        self._max_latency_samples: int = 1000

    def increment_vectors_stored(self, count: int = 1) -> None:
        with self._lock:
            self._vectors_stored += count

    def increment_vectors_indexed(self, count: int = 1) -> None:
        with self._lock:
            self._vectors_indexed += count

    def record_search(self) -> None:
        with self._lock:
            self._searches += 1

    def record_retrieval_latency(self, ms: float) -> None:
        with self._lock:
            self._retrieval_latencies.append(ms)
            if len(self._retrieval_latencies) > self._max_latency_samples:
                self._retrieval_latencies = self._retrieval_latencies[-self._max_latency_samples:]

    def record_indexing_latency(self, ms: float) -> None:
        with self._lock:
            self._indexing_latencies.append(ms)
            if len(self._indexing_latencies) > self._max_latency_samples:
                self._indexing_latencies = self._indexing_latencies[-self._max_latency_samples:]

    def record_embedding_latency(self, ms: float) -> None:
        with self._lock:
            self._embedding_latencies.append(ms)
            if len(self._embedding_latencies) > self._max_latency_samples:
                self._embedding_latencies = self._embedding_latencies[-self._max_latency_samples:]

    def record_storage_usage(self, bytes_: int) -> None:
        with self._lock:
            self._storage_usage_bytes = bytes_

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    def record_consolidation(self) -> None:
        with self._lock:
            self._consolidations_run += 1

    def get_summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "vectors_stored": self._vectors_stored,
                "vectors_indexed": self._vectors_indexed,
                "total_searches": self._searches,
                "avg_retrieval_latency_ms": self._average(self._retrieval_latencies),
                "avg_indexing_latency_ms": self._average(self._indexing_latencies),
                "avg_embedding_latency_ms": self._average(self._embedding_latencies),
                "storage_usage_bytes": self._storage_usage_bytes,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "consolidations_run": self._consolidations_run,
            }

    def reset(self) -> None:
        with self._lock:
            self._vectors_stored = 0
            self._vectors_indexed = 0
            self._searches = 0
            self._retrieval_latencies.clear()
            self._indexing_latencies.clear()
            self._embedding_latencies.clear()
            self._storage_usage_bytes = 0
            self._cache_hits = 0
            self._cache_misses = 0
            self._consolidations_run = 0

    @staticmethod
    def _average(values: list[float]) -> float:
        if not values:
            return 0.0
        return statistics.mean(values)


_metrics_instance: VectorMetrics | None = None


def get_vector_metrics() -> VectorMetrics:
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = VectorMetrics()
    return _metrics_instance
