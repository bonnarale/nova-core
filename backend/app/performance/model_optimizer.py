"""Model gateway optimization."""

from __future__ import annotations

import threading
from typing import Any


class ModelOptimizer:
    """Optimizes model inference and API calls."""

    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def record_call(self, model: str, tokens: int, duration_ms: float, cached: bool = False) -> None:
        with self._lock:
            self._calls.append({
                "model": model,
                "tokens": tokens,
                "duration_ms": duration_ms,
                "cached": cached,
                "tokens_per_second": tokens / (duration_ms / 1000) if duration_ms > 0 else 0,
            })

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            if not self._calls:
                return {"total": 0, "avg_ms": 0}
            times = [c["duration_ms"] for c in self._calls]
            tps = [c["tokens_per_second"] for c in self._calls if c["tokens_per_second"] > 0]
            cached = sum(1 for c in self._calls if c["cached"])
            return {
                "total": len(self._calls),
                "avg_ms": sum(times) / len(times),
                "max_ms": max(times),
                "avg_tokens_per_second": sum(tps) / len(tps) if tps else 0,
                "cache_ratio": cached / len(self._calls),
            }

    def get_recommendations(self) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        stats = self.get_stats()
        if stats.get("cache_ratio", 1) < 0.3 and stats.get("total", 0) > 5:
            recs.append({
                "area": "model_optimization",
                "severity": "medium",
                "title": "Low model response cache ratio",
                "description": f"Only {stats.get('cache_ratio', 0):.0%} of model calls are cached. Implement response caching.",
                "expected_improvement": "30-60% cost reduction",
            })
        return recs

    def optimize(self, target: str = "all") -> dict[str, Any]:
        return {"optimized": True, "target": target, "recommendations": self.get_recommendations(), "stats": self.get_stats()}
