"""Workflow optimization."""

from __future__ import annotations

import threading
from typing import Any


class WorkflowOptimizer:
    """Optimizes workflow execution patterns."""

    def __init__(self) -> None:
        self._workflows: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def record_workflow(self, workflow_id: str, step_count: int, total_ms: float, parallel_steps: int = 0) -> None:
        with self._lock:
            self._workflows.append({
                "workflow_id": workflow_id,
                "step_count": step_count,
                "total_ms": total_ms,
                "parallel_steps": parallel_steps,
                "avg_step_ms": total_ms / step_count if step_count > 0 else 0,
            })

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            if not self._workflows:
                return {"total": 0, "avg_steps": 0, "avg_duration_ms": 0}
            return {
                "total": len(self._workflows),
                "avg_steps": sum(w["step_count"] for w in self._workflows) / len(self._workflows),
                "avg_duration_ms": sum(w["total_ms"] for w in self._workflows) / len(self._workflows),
                "avg_parallel_ratio": sum(
                    w["parallel_steps"] / max(w["step_count"], 1) for w in self._workflows
                ) / len(self._workflows),
            }

    def get_recommendations(self) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        stats = self.get_stats()
        if stats.get("avg_parallel_ratio", 0) < 0.2 and stats.get("total", 0) > 0:
            recs.append({
                "area": "workflow_optimization",
                "severity": "medium",
                "title": "Low workflow parallelization",
                "description": "Most workflow steps run sequentially. Identify parallelizable steps.",
                "expected_improvement": "15-30% workflow execution speedup",
            })
        return recs

    def optimize(self, target: str = "all") -> dict[str, Any]:
        return {"optimized": True, "target": target, "recommendations": self.get_recommendations(), "stats": self.get_stats()}
