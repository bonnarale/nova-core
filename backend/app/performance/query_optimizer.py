"""Query optimization for database operations."""

from __future__ import annotations

import threading
import time
from typing import Any


class QueryOptimizer:
    """Optimizes database query patterns and identifies slow queries."""

    _SLOW_THRESHOLD_MS = 100.0

    def __init__(self) -> None:
        self._queries: list[dict[str, Any]] = []
        self._slow_queries: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def record_query(self, query: str, duration_ms: float, rows: int = 0, table: str = "") -> None:
        entry = {
            "query": query,
            "duration_ms": duration_ms,
            "rows": rows,
            "table": table,
            "timestamp": time.time(),
        }
        with self._lock:
            self._queries.append(entry)
            if duration_ms > self._SLOW_THRESHOLD_MS:
                self._slow_queries.append(entry)

    def get_slow_queries(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return sorted(self._slow_queries, key=lambda q: q["duration_ms"], reverse=True)[:limit]

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            if not self._queries:
                return {"total": 0, "slow": 0, "avg_ms": 0, "max_ms": 0}
            times = [q["duration_ms"] for q in self._queries]
            return {
                "total": len(self._queries),
                "slow": len(self._slow_queries),
                "avg_ms": sum(times) / len(times),
                "max_ms": max(times),
                "min_ms": min(times),
            }

    def get_recommendations(self) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        stats = self.get_stats()
        if stats["slow"] > 0:
            recs.append({
                "area": "query_optimization",
                "severity": "high",
                "title": f"{stats['slow']} slow queries detected",
                "description": f"Queries exceeding {self._SLOW_THRESHOLD_MS}ms threshold. Add indexes or optimize joins.",
                "expected_improvement": "20-50% query time reduction",
            })
        if stats["avg_ms"] > 50 and stats["total"] > 0:
            recs.append({
                "area": "query_optimization",
                "severity": "medium",
                "title": "High average query time",
                "description": f"Average query time is {stats['avg_ms']:.1f}ms. Consider query batching and connection pooling.",
                "expected_improvement": "10-30% throughput improvement",
            })
        return recs

    def optimize(self, target: str = "all") -> dict[str, Any]:
        return {
            "optimized": True,
            "target": target,
            "recommendations": self.get_recommendations(),
            "stats": self.get_stats(),
        }
