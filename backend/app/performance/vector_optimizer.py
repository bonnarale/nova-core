"""Vector search optimization."""

from __future__ import annotations

import threading
from typing import Any


class VectorOptimizer:
    """Optimizes vector search and embedding operations."""

    def __init__(self) -> None:
        self._searches: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def record_search(self, query_size: int, result_count: int, duration_ms: float, indexed: bool = True) -> None:
        with self._lock:
            self._searches.append({
                "query_size": query_size,
                "result_count": result_count,
                "duration_ms": duration_ms,
                "indexed": indexed,
            })

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            if not self._searches:
                return {"total": 0, "avg_ms": 0}
            times = [s["duration_ms"] for s in self._searches]
            indexed = sum(1 for s in self._searches if s["indexed"])
            return {
                "total": len(self._searches),
                "avg_ms": sum(times) / len(times),
                "max_ms": max(times),
                "indexed_ratio": indexed / len(self._searches),
            }

    def get_recommendations(self) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        stats = self.get_stats()
        if stats.get("indexed_ratio", 1.0) < 0.8 and stats.get("total", 0) > 0:
            recs.append({
                "area": "vector_search",
                "severity": "high",
                "title": "Low index utilization",
                "description": f"Only {stats['indexed_ratio']:.0%} of searches use indexes. Ensure HNSW/IVF indexes are configured.",
                "expected_improvement": "50-90% search speedup",
            })
        if stats.get("avg_ms", 0) > 50 and stats.get("total", 0) > 0:
            recs.append({
                "area": "vector_search",
                "severity": "medium",
                "title": "High average search latency",
                "description": f"Average vector search time is {stats['avg_ms']:.1f}ms. Consider dimension reduction or quantization.",
                "expected_improvement": "20-40% search speedup",
            })
        return recs

    def optimize(self, target: str = "all") -> dict[str, Any]:
        return {"optimized": True, "target": target, "recommendations": self.get_recommendations(), "stats": self.get_stats()}
