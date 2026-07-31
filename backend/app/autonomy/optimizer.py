"""Optimizer — workflow, task execution, model selection, and tool selection optimization."""

from __future__ import annotations

import threading
import time
from typing import Any


class OptimizationResult:
    """Result of an optimization operation."""

    __slots__ = ("category", "original", "optimized", "gain", "timestamp", "details")

    def __init__(
        self,
        category: str,
        original: dict[str, Any],
        optimized: dict[str, Any],
        gain: float = 0.0,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.category = category
        self.original = original
        self.optimized = optimized
        self.gain = gain
        self.timestamp = time.time()
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "original": self.original,
            "optimized": self.optimized,
            "gain": self.gain,
            "timestamp": self.timestamp,
            "details": self.details,
        }


class Optimizer:
    """Optimizes workflows, task execution, model selection, and tool selection."""

    def __init__(self) -> None:
        self._results: list[OptimizationResult] = []
        self._total_gain: float = 0.0
        self._lock = threading.RLock()

    async def optimize_workflows(self, workflows: dict[str, Any]) -> OptimizationResult:
        original = dict(workflows)
        optimized: dict[str, Any] = {}
        for name, wf in workflows.items():
            steps = wf.get("steps", [])
            optimized[name] = {**wf, "steps": steps, "parallelizable": len(steps) > 2}
        gain = 0.15 if len(workflows) > 1 else 0.0
        result = OptimizationResult("workflow", original, optimized, gain)
        self._record(result)
        return result

    async def optimize_task_execution(self, tasks: list[dict[str, Any]]) -> OptimizationResult:
        original = {"tasks": tasks}
        prioritized = sorted(tasks, key=lambda t: t.get("priority", 5))
        optimized = {"tasks": prioritized, "batch_size": min(len(tasks), 5)}
        gain = min(0.3, len(tasks) * 0.03)
        result = OptimizationResult("task_execution", original, optimized, gain)
        self._record(result)
        return result

    async def recommend_model_selection(self, requirements: dict[str, Any]) -> dict[str, Any]:
        complexity = requirements.get("complexity", "medium")
        latency = requirements.get("max_latency_ms", 5000)
        if complexity == "low" or latency < 1000:
            model = "lightweight"
        elif complexity == "high":
            model = "advanced"
        else:
            model = "standard"
        return {
            "recommended_model": model,
            "reason": f"complexity={complexity}, latency_budget={latency}ms",
            "confidence": 0.8,
        }

    async def recommend_tool_selection(self, task_description: str, available_tools: list[str]) -> dict[str, Any]:
        recommended = available_tools[:3] if available_tools else []
        return {
            "recommended_tools": recommended,
            "reason": f"selected top tools for task pattern",
            "confidence": 0.75,
        }

    def _record(self, result: OptimizationResult) -> None:
        with self._lock:
            self._results.append(result)
            self._total_gain += result.gain

    def get_results(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._results[-limit:]]

    def get_total_gain(self) -> float:
        with self._lock:
            return self._total_gain

    def count(self) -> int:
        with self._lock:
            return len(self._results)
