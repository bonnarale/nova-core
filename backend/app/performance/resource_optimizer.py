"""Resource utilization optimization."""

from __future__ import annotations

import threading
import time
from typing import Any


class ResourceOptimizer:
    """Optimizes resource utilization across the platform."""

    def __init__(self) -> None:
        self._snapshots: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def record_snapshot(self, cpu_percent: float = 0.0, memory_mb: float = 0.0, open_files: int = 0, threads: int = 0) -> None:
        with self._lock:
            self._snapshots.append({
                "cpu_percent": cpu_percent,
                "memory_mb": memory_mb,
                "open_files": open_files,
                "threads": threads,
                "timestamp": time.time(),
            })

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            if not self._snapshots:
                return {"snapshots": 0, "avg_cpu": 0, "avg_memory_mb": 0}
            cpu = [s["cpu_percent"] for s in self._snapshots]
            mem = [s["memory_mb"] for s in self._snapshots]
            return {
                "snapshots": len(self._snapshots),
                "avg_cpu": sum(cpu) / len(cpu),
                "max_cpu": max(cpu),
                "avg_memory_mb": sum(mem) / len(mem),
                "max_memory_mb": max(mem),
            }

    def get_recommendations(self) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        stats = self.get_stats()
        if stats.get("max_cpu", 0) > 80:
            recs.append({
                "area": "resource_optimization",
                "severity": "high",
                "title": "High CPU utilization detected",
                "description": f"Peak CPU usage is {stats['max_cpu']:.1f}%. Consider load balancing or scaling.",
                "expected_improvement": "Improved stability and throughput",
            })
        if stats.get("max_memory_mb", 0) > 1000:
            recs.append({
                "area": "resource_optimization",
                "severity": "medium",
                "title": "High memory usage",
                "description": f"Peak memory is {stats['max_memory_mb']:.0f}MB. Consider memory profiling and optimization.",
                "expected_improvement": "Reduced memory footprint",
            })
        return recs

    def optimize(self, target: str = "all") -> dict[str, Any]:
        return {"optimized": True, "target": target, "recommendations": self.get_recommendations(), "stats": self.get_stats()}
