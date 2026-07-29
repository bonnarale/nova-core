from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .schemas import OptimizationResult


class OptimizationEngine:
    def __init__(self) -> None:
        self._results: dict[str, OptimizationResult] = {}

    def analyze(
        self,
        category: str,
        current_state: str,
        proposed_state: str,
        improvement: str,
        priority: int = 3,
        estimated_impact: str = "",
    ) -> dict:
        result = OptimizationResult(
            category=category,
            current_state=current_state,
            proposed_state=proposed_state,
            improvement=improvement,
            priority=priority,
            estimated_impact=estimated_impact,
        )
        self._results[result.id] = result
        return self._result_to_dict(result)

    def get_result(self, result_id: str) -> dict | None:
        result = self._results.get(result_id)
        if result is None:
            return None
        return self._result_to_dict(result)

    def list_results(self, category: str | None = None) -> list[dict]:
        results = list(self._results.values())
        if category is not None:
            results = [r for r in results if r.category == category]
        return [self._result_to_dict(r) for r in results]

    def prioritize(self) -> list[dict]:
        sorted_results = sorted(
            self._results.values(), key=lambda r: r.priority, reverse=True
        )
        return [self._result_to_dict(r) for r in sorted_results]

    def _result_to_dict(self, result: OptimizationResult) -> dict:
        return {
            "id": result.id,
            "category": result.category,
            "current_state": result.current_state,
            "proposed_state": result.proposed_state,
            "improvement": result.improvement,
            "priority": result.priority,
            "estimated_impact": result.estimated_impact,
            "created_at": result.created_at,
        }

    def to_dict(self) -> dict:
        return {
            "results": {
                k: self._result_to_dict(v) for k, v in self._results.items()
            }
        }
