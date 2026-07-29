"""Autonomy manager — coordinates all autonomy subsystems."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.autonomy.adaptation import AdaptationEngine
from app.autonomy.approval import ApprovalManager
from app.autonomy.enums import AutonomyState, RecommendationStatus
from app.autonomy.evaluator import Evaluator
from app.autonomy.governor import AutonomyGovernor
from app.autonomy.lifecycle import AutonomyLifecycle
from app.autonomy.metrics import AutonomyMetricsCollector
from app.autonomy.objective import ObjectiveManager
from app.autonomy.optimizer import Optimizer
from app.autonomy.planner import AutonomousPlanner
from app.autonomy.policy import PolicyEngine
from app.autonomy.reflection import ReflectionEngine
from app.autonomy.safety import SafetyEngine
from app.autonomy.strategy import StrategyManager
from app.autonomy.tracing import AutonomyTracer

logger = logging.getLogger(__name__)


class AutonomyManager:
    """Coordinates all autonomy subsystems into a cohesive layer."""

    def __init__(self) -> None:
        self._lifecycle = AutonomyLifecycle()
        self._governor = AutonomyGovernor()
        self._policy = PolicyEngine()
        self._objectives = ObjectiveManager()
        self._evaluator = Evaluator(self._objectives)
        self._reflection = ReflectionEngine()
        self._planner = AutonomousPlanner()
        self._optimizer = Optimizer()
        self._adaptation = AdaptationEngine()
        self._strategy = StrategyManager()
        self._safety = SafetyEngine()
        self._approval = ApprovalManager()
        self._metrics = AutonomyMetricsCollector()
        self._tracer = AutonomyTracer()
        self._recommendations: list[dict[str, Any]] = []
        self._running = False

    @property
    def lifecycle(self) -> AutonomyLifecycle: return self._lifecycle
    @property
    def governor(self) -> AutonomyGovernor: return self._governor
    @property
    def policy(self) -> PolicyEngine: return self._policy
    @property
    def objectives(self) -> ObjectiveManager: return self._objectives
    @property
    def evaluator(self) -> Evaluator: return self._evaluator
    @property
    def reflection(self) -> ReflectionEngine: return self._reflection
    @property
    def planner(self) -> AutonomousPlanner: return self._planner
    @property
    def optimizer(self) -> Optimizer: return self._optimizer
    @property
    def adaptation(self) -> AdaptationEngine: return self._adaptation
    @property
    def strategy(self) -> StrategyManager: return self._strategy
    @property
    def safety(self) -> SafetyEngine: return self._safety
    @property
    def approval(self) -> ApprovalManager: return self._approval
    @property
    def metrics(self) -> AutonomyMetricsCollector: return self._metrics
    @property
    def tracer(self) -> AutonomyTracer: return self._tracer
    @property
    def recommendations(self) -> list[dict[str, Any]]: return list(self._recommendations)

    async def start(self) -> None:
        self._metrics.start()
        self._lifecycle.transition(AutonomyState.INITIALIZED, "init")
        self._lifecycle.transition(AutonomyState.READY, "ready")
        self._lifecycle.transition(AutonomyState.OBSERVING, "start_observing")
        self._running = True
        logger.info("Autonomy manager started")

    async def shutdown(self) -> None:
        self._lifecycle.transition(AutonomyState.SHUTDOWN, "shutdown")
        self._running = False
        logger.info("Autonomy manager stopped")

    def is_running(self) -> bool:
        return self._running

    async def evaluate_objectives(self) -> list[dict[str, Any]]:
        trace_id = self._tracer.start_trace("evaluate_objectives")
        self._lifecycle.transition(AutonomyState.ANALYZING, "evaluating")
        objectives = self._objectives.prioritize()
        results = [self._evaluator.evaluate_objective(o.to_dict()) for o in objectives]
        self._lifecycle.transition(AutonomyState.RECOMMENDING, "analysis_done")
        self._tracer.finish_trace(trace_id)
        return results

    async def propose_plan(self, objective_id: str) -> dict[str, Any]:
        trace_id = self._tracer.start_trace(f"propose_plan.{objective_id}")
        plan = await self._planner.propose_plan(objective_id)
        self._tracer.finish_trace(trace_id)
        return plan.to_dict()

    async def evaluate_execution(self, execution_id: str, results: dict[str, Any] | None = None) -> dict[str, Any]:
        trace_id = self._tracer.start_trace(f"evaluate_execution.{execution_id}")
        result = await self._reflection.review_execution(execution_id, results or {"success": True})
        self._tracer.finish_trace(trace_id)
        return result

    async def reflect_on_results(self, results: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("reflect_on_results")
        if results.get("success", True):
            reflection = await self._reflection.analyze_success("current", results)
        else:
            reflection = await self._reflection.analyze_failure("current", results.get("error", "unknown"))
        self._tracer.finish_trace(trace_id)
        return reflection

    async def recommend_improvements(self) -> list[dict[str, Any]]:
        trace_id = self._tracer.start_trace("recommend_improvements")
        self._lifecycle.transition(AutonomyState.RECOMMENDING, "generating_recommendations")
        recommendations: list[dict[str, Any]] = []
        strategy_types = self._strategy.get_all_types()
        for st in strategy_types:
            rec = {
                "id": f"rec_{st}_{int(time.time())}",
                "type": "strategy_optimization",
                "strategy_type": st,
                "current_strategy": self._adaptation.get_strategy(st),
                "confidence": 0.7,
                "risk_level": "low",
                "status": RecommendationStatus.PENDING.value,
            }
            recommendations.append(rec)
        self._recommendations.extend(recommendations)
        self._metrics.record_recommendation()
        self._tracer.finish_trace(trace_id)
        return recommendations

    async def adapt_strategy(self, strategy_type: str, context: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._tracer.start_trace(f"adapt_strategy.{strategy_type}")
        new_strategy = self._adaptation.adapt(strategy_type, context)
        self._tracer.finish_trace(trace_id)
        return {"strategy_type": strategy_type, "new_strategy": new_strategy}

    async def optimize_workflows(self, workflows: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("optimize_workflows")
        result = await self._optimizer.optimize_workflows(workflows)
        self._metrics.record_optimization_gain(result.gain)
        self._tracer.finish_trace(trace_id)
        return result.to_dict()

    async def optimize_task_execution(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("optimize_task_execution")
        result = await self._optimizer.optimize_task_execution(tasks)
        self._metrics.record_optimization_gain(result.gain)
        self._tracer.finish_trace(trace_id)
        return result.to_dict()

    async def recommend_model_selection(self, requirements: dict[str, Any]) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("recommend_model_selection")
        result = await self._optimizer.recommend_model_selection(requirements)
        self._tracer.finish_trace(trace_id)
        return result

    async def recommend_tool_selection(self, task_description: str, available_tools: list[str]) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("recommend_tool_selection")
        result = await self._optimizer.recommend_tool_selection(task_description, available_tools)
        self._tracer.finish_trace(trace_id)
        return result

    def get_status(self) -> dict[str, Any]:
        status = self._lifecycle.get_status()
        return {
            **status,
            "autonomy_level": self._governor.level.value,
            "total_objectives": self._objectives.count(),
            "total_recommendations": len(self._recommendations),
        }

    def get_objectives(self) -> list[dict[str, Any]]:
        return [o.to_dict() for o in self._objectives.get_all()]

    def get_policies(self) -> dict[str, Any]:
        return {k: v.to_dict() for k, v in self._policy.get_all().items()}

    def get_metrics_snapshot(self) -> dict[str, Any]:
        return self._metrics.snapshot().to_dict()

    def get_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._tracer.get_traces(limit)

    def get_reflections(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._reflection.get_records(limit)
