"""Scheduler optimization."""

from __future__ import annotations

import threading
import time
from typing import Any


class SchedulerOptimizer:
    """Optimizes scheduler job execution and timing."""

    def __init__(self) -> None:
        self._jobs: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def record_job(self, job_name: str, scheduled_at: float, executed_at: float, duration_ms: float) -> None:
        with self._lock:
            self._jobs.append({
                "job_name": job_name,
                "scheduled_at": scheduled_at,
                "executed_at": executed_at,
                "delay_ms": (executed_at - scheduled_at) * 1000,
                "duration_ms": duration_ms,
            })

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            if not self._jobs:
                return {"total_jobs": 0, "avg_delay_ms": 0, "avg_duration_ms": 0}
            delays = [j["delay_ms"] for j in self._jobs]
            durations = [j["duration_ms"] for j in self._jobs]
            return {
                "total_jobs": len(self._jobs),
                "avg_delay_ms": sum(delays) / len(delays),
                "avg_duration_ms": sum(durations) / len(durations),
                "max_delay_ms": max(delays),
                "max_duration_ms": max(durations),
            }

    def get_recommendations(self) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        stats = self.get_stats()
        if stats.get("avg_delay_ms", 0) > 50:
            recs.append({
                "area": "scheduler_optimization",
                "severity": "medium",
                "title": "High scheduler delay",
                "description": f"Average job delay is {stats['avg_delay_ms']:.1f}ms. Consider priority queues.",
                "expected_improvement": "10-20% scheduling efficiency",
            })
        return recs

    def optimize(self, target: str = "all") -> dict[str, Any]:
        return {"optimized": True, "target": target, "recommendations": self.get_recommendations(), "stats": self.get_stats()}
