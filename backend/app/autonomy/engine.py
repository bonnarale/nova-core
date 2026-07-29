"""Autonomous Intelligence engine — top-level coordinator."""

from __future__ import annotations

import logging
from typing import Any

from app.autonomy.enums import AutonomyState, RecommendationStatus
from app.autonomy.manager import AutonomyManager

logger = logging.getLogger(__name__)


class AutonomyEngine:
    """Top-level autonomous intelligence engine."""

    def __init__(self) -> None:
        self._manager = AutonomyManager()

    @property
    def manager(self) -> AutonomyManager:
        return self._manager

    async def start(self) -> None:
        await self._manager.start()

    async def shutdown(self) -> None:
        await self._manager.shutdown()

    def is_running(self) -> bool:
        return self._manager.is_running()

    async def evaluate_objectives(self) -> list[dict[str, Any]]:
        return await self._manager.evaluate_objectives()

    async def propose_plan(self, objective_id: str) -> dict[str, Any]:
        return await self._manager.propose_plan(objective_id)

    async def evaluate_execution(self, execution_id: str, results: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._manager.evaluate_execution(execution_id, results)

    async def reflect_on_results(self, results: dict[str, Any]) -> dict[str, Any]:
        return await self._manager.reflect_on_results(results)

    async def recommend_improvements(self) -> list[dict[str, Any]]:
        return await self._manager.recommend_improvements()

    async def adapt_strategy(self, strategy_type: str, context: dict[str, Any]) -> dict[str, Any]:
        return await self._manager.adapt_strategy(strategy_type, context)

    async def optimize_workflows(self, workflows: dict[str, Any]) -> dict[str, Any]:
        return await self._manager.optimize_workflows(workflows)

    async def optimize_task_execution(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        return await self._manager.optimize_task_execution(tasks)

    async def recommend_model_selection(self, requirements: dict[str, Any]) -> dict[str, Any]:
        return await self._manager.recommend_model_selection(requirements)

    async def recommend_tool_selection(self, task_description: str, available_tools: list[str]) -> dict[str, Any]:
        return await self._manager.recommend_tool_selection(task_description, available_tools)

    def get_status(self) -> dict[str, Any]:
        return self._manager.get_status()

    def get_objectives(self) -> list[dict[str, Any]]:
        return self._manager.get_objectives()

    def get_recommendations(self) -> list[dict[str, Any]]:
        return self._manager.recommendations

    def get_reflections(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._manager.get_reflections(limit)

    def get_policies(self) -> dict[str, Any]:
        return self._manager.get_policies()

    def get_metrics(self) -> dict[str, Any]:
        return self._manager.get_metrics_snapshot()

    def get_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._manager.get_traces(limit)

    async def approve_recommendation(self, recommendation_id: str, approver: str = "human") -> bool:
        return self._manager.approval.approve(recommendation_id, approver)

    async def reject_recommendation(self, recommendation_id: str, reason: str = "") -> bool:
        return self._manager.approval.reject(recommendation_id, reason)
