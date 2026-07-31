"""Evaluator — scores objectives and evaluates execution outcomes."""

from __future__ import annotations

import threading
from typing import Any

from app.autonomy.enums import ObjectivePriority, ObjectiveStatus
from app.autonomy.objective import Objective, ObjectiveManager, _PRIORITY_ORDER


class Evaluator:
    """Evaluates objectives, scores completion, and ranks objectives."""

    def __init__(self, objective_manager: ObjectiveManager | None = None) -> None:
        self._objective_manager = objective_manager or ObjectiveManager()
        self._evaluations: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    @property
    def objective_manager(self) -> ObjectiveManager:
        return self._objective_manager

    def evaluate_objective(self, objective: dict[str, Any]) -> dict[str, Any]:
        priority = ObjectivePriority(objective.get("priority", "medium"))
        status = ObjectiveStatus(objective.get("status", "pending"))
        progress = objective.get("progress", 0.0)
        priority_score = (4 - _PRIORITY_ORDER.get(priority, 4)) / 4.0
        status_score = {
            ObjectiveStatus.COMPLETED: 1.0,
            ObjectiveStatus.IN_PROGRESS: 0.6,
            ObjectiveStatus.ACTIVE: 0.4,
            ObjectiveStatus.PENDING: 0.1,
            ObjectiveStatus.BLOCKED: 0.0,
            ObjectiveStatus.FAILED: 0.0,
            ObjectiveStatus.CANCELLED: 0.0,
        }.get(status, 0.0)
        score = priority_score * 0.3 + status_score * 0.3 + progress * 0.4
        result = {
            "objective_id": objective.get("id", "unknown"),
            "score": round(score, 3),
            "priority_score": round(priority_score, 3),
            "status_score": round(status_score, 3),
            "progress": progress,
        }
        with self._lock:
            self._evaluations.append(result)
        return result

    def score_completion(self, objective: dict[str, Any], results: dict[str, Any]) -> float:
        progress = objective.get("progress", 0.0)
        success_rate = results.get("success_rate", 1.0)
        efficiency = results.get("efficiency", 0.8)
        score = min(1.0, progress * 0.4 + success_rate * 0.3 + efficiency * 0.3)
        return round(score, 3)

    def rank_objectives(self, objectives: list[dict[str, Any]]) -> list[dict[str, Any]]:
        evaluated = [self.evaluate_objective(obj) for obj in objectives]
        evaluated.sort(key=lambda e: e["score"], reverse=True)
        return evaluated

    def get_evaluations(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._evaluations[-limit:])
