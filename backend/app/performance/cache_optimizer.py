"""Cache optimization strategies."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.performance.enums import CacheStrategy


class CacheStats:
    """Statistics for a cache instance."""

    __slots__ = ("name", "hits", "misses", "evictions", "size", "max_size", "strategy", "hit_ratio")

    def __init__(self, name: str = "", max_size: int = 1000, strategy: str = "lru") -> None:
        self.name = name
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.size = 0
        self.max_size = max_size
        self.strategy = strategy
        self.hit_ratio = 0.0

    def record_hit(self) -> None:
        self.hits += 1
        total = self.hits + self.misses
        self.hit_ratio = self.hits / total if total > 0 else 0.0

    def record_miss(self) -> None:
        self.misses += 1
        total = self.hits + self.misses
        self.hit_ratio = self.hits / total if total > 0 else 0.0

    def record_eviction(self) -> None:
        self.evictions += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size": self.size,
            "max_size": self.max_size,
            "strategy": self.strategy,
            "hit_ratio": self.hit_ratio,
        }


class CacheOptimizer:
    """Optimizes cache configurations and provides recommendations."""

    _KNOWN_CACHES: dict[str, dict[str, Any]] = {
        "memory_cache": {"max_size": 1000, "strategy": "lru", "ttl": 300},
        "retrieval_cache": {"max_size": 500, "strategy": "lfu", "ttl": 600},
        "embedding_cache": {"max_size": 2000, "strategy": "lru", "ttl": 1800},
        "model_cache": {"max_size": 100, "strategy": "lru", "ttl": 3600},
        "workflow_cache": {"max_size": 200, "strategy": "lru", "ttl": 300},
        "scheduler_cache": {"max_size": 500, "strategy": "lru", "ttl": 60},
    }

    def __init__(self) -> None:
        self._stats: dict[str, CacheStats] = {}
        self._lock = threading.RLock()
        for name, config in self._KNOWN_CACHES.items():
            self._stats[name] = CacheStats(name, config["max_size"], config["strategy"])

    def get_stats(self, cache_name: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        with self._lock:
            if cache_name:
                stats = self._stats.get(cache_name)
                return stats.to_dict() if stats else {}
            return [s.to_dict() for s in self._stats.values()]

    def record_hit(self, cache_name: str) -> None:
        with self._lock:
            if cache_name in self._stats:
                self._stats[cache_name].record_hit()

    def record_miss(self, cache_name: str) -> None:
        with self._lock:
            if cache_name in self._stats:
                self._stats[cache_name].record_miss()

    def get_recommendations(self) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        with self._lock:
            for name, stats in self._stats.items():
                if stats.hit_ratio < 0.5 and (stats.hits + stats.misses) > 10:
                    recs.append({
                        "area": "cache_optimization",
                        "severity": "high",
                        "title": f"Low hit ratio for {name}",
                        "description": f"Cache '{name}' has hit ratio {stats.hit_ratio:.2%}. Consider increasing size or adjusting strategy.",
                        "expected_improvement": "10-30% latency reduction",
                    })
                if stats.evictions > stats.hits * 0.1 and stats.hits > 0:
                    recs.append({
                        "area": "cache_optimization",
                        "severity": "medium",
                        "title": f"High eviction rate for {name}",
                        "description": f"Cache '{name}' has {stats.evictions} evictions. Consider increasing max_size.",
                        "expected_improvement": "5-15% hit ratio improvement",
                    })
        return recs

    def optimize(self, cache_name: str | None = None) -> dict[str, Any]:
        recs = self.get_recommendations()
        if cache_name:
            recs = [r for r in recs if cache_name in r.get("title", "")]
        return {
            "optimized": True,
            "cache": cache_name,
            "recommendations": recs,
            "total_caches": len(self._stats),
        }
