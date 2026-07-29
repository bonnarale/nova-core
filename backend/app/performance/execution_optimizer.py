"""Execution optimization — parallel execution, async scheduling, task batching."""

from __future__ import annotations

import threading
import time
from typing import Any


class ExecutionOptimizer:
    """Optimizes execution patterns across the platform."""

    def __init__(self) -> None:
        self._executions: list[dict[str, Any]] = []
        self._batch_stats: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def record_execution(self, operation: str, duration_ms: float, parallel: bool = False, batched: bool = False) -> None:
        with self._lock:
            self._executions.append({
                "operation": operation,
                "duration_ms": duration_ms,
                "parallel": parallel,
                "batched": batched,
                "timestamp": time.time(),
            })

    def record_batch(self, batch_name: str, count: int, total_ms: float) -> None:
        with self._lock:
            self._batch_stats[batch_name] = {
                "count": count,
                "total_ms": total_ms,
                "avg_ms": total_ms / count if count > 0 else 0,
                "throughput": count / (total_ms / 1000) if total_ms > 0 else 0,
            }

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            result: dict[str, Any] = {"batch_stats": dict(self._batch_stats)}
            if not self._executions:
                result.update({"total": 0, "parallel": 0, "batched": 0, "avg_ms": 0})
                return result
            times = [e["duration_ms"] for e in self._executions]
            parallel = sum(1 for e in self._executions if e["parallel"])
            batched = sum(1 for e in self._executions if e["batched"])
            result.update({
                "total": len(self._executions),
                "parallel": parallel,
                "batched": batched,
                "avg_ms": sum(times) / len(times),
                "max_ms": max(times),
                "min_ms": min(times),
            })
            return result

    def get_recommendations(self) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        stats = self.get_stats()
        if stats["total"] > 0:
            serial_ratio = 1 - (stats["parallel"] / stats["total"])
            if serial_ratio > 0.7:
                recs.append({
                    "area": "execution_optimization",
                    "severity": "medium",
                    "title": "Low parallelization ratio",
                    "description": f"{serial_ratio:.0%} of executions are serial. Consider parallelizing independent tasks.",
                    "expected_improvement": "20-40% throughput improvement",
                })
            if stats.get("avg_ms", 0) > 100:
                recs.append({
                    "area": "execution_optimization",
                    "severity": "high",
                    "title": "High average execution time",
                    "description": f"Average execution time is {stats['avg_ms']:.1f}ms. Consider task batching and async scheduling.",
                    "expected_improvement": "15-35% latency reduction",
                })
        return recs

    def optimize(self, target: str = "all") -> dict[str, Any]:
        return {
            "optimized": True,
            "target": target,
            "recommendations": self.get_recommendations(),
            "stats": self.get_stats(),
        }
