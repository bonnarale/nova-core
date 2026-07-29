"""Tests for the Autonomy subsystem (Ch35)."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import pytest

from app.autonomy.enums import (
    AutonomyLevel,
    AutonomyState,
    ApprovalType,
    ObjectivePriority,
    ObjectiveStatus,
    RecommendationStatus,
    ReflectionType,
    SafetyLevel,
    StrategyType,
)
from app.autonomy.base import (
    AutonomyProvider,
    PolicyProvider,
    ReflectionProvider,
    StrategyProvider,
    EvaluatorProvider,
    ApprovalProvider,
)
from app.autonomy.policy import PolicyEngine, AutonomyPolicy, PolicyRule
from app.autonomy.objective import ObjectiveManager, Objective
from app.autonomy.evaluator import Evaluator
from app.autonomy.reflection import ReflectionEngine
from app.autonomy.planner import AutonomousPlanner, Plan, PlanStep
from app.autonomy.optimizer import Optimizer
from app.autonomy.adaptation import AdaptationEngine
from app.autonomy.strategy import StrategyManager, StrategyEntry
from app.autonomy.governor import AutonomyGovernor
from app.autonomy.approval import ApprovalManager
from app.autonomy.safety import SafetyEngine, SafetyConstraint
from app.autonomy.lifecycle import AutonomyLifecycle
from app.autonomy.repository import AutonomyRepository
from app.autonomy.persistence import InMemoryAutonomyRepository
from app.autonomy.metrics import AutonomyMetricsCollector
from app.autonomy.tracing import AutonomyTracer
from app.autonomy.manager import AutonomyManager
from app.autonomy.engine import AutonomyEngine
from app.autonomy.factory import AutonomyFactory


# ===== Enums =====

class TestEnums:
    def test_autonomy_level(self) -> None:
        assert AutonomyLevel.MANUAL.value == "manual"
        assert AutonomyLevel.ASSISTED.value == "assisted"
        assert AutonomyLevel.SUPERVISED.value == "supervised"
        assert AutonomyLevel.AUTONOMOUS.value == "autonomous"
        assert AutonomyLevel.FULL.value == "full"

    def test_autonomy_state(self) -> None:
        assert AutonomyState.REGISTERED.value == "registered"
        assert AutonomyState.EXECUTING.value == "executing"
        assert AutonomyState.SHUTDOWN.value == "shutdown"

    def test_objective_priority(self) -> None:
        assert ObjectivePriority.CRITICAL.value == "critical"
        assert ObjectivePriority.HIGH.value == "high"
        assert ObjectivePriority.MEDIUM.value == "medium"
        assert ObjectivePriority.LOW.value == "low"
        assert ObjectivePriority.BACKGROUND.value == "background"

    def test_objective_status(self) -> None:
        assert ObjectiveStatus.PENDING.value == "pending"
        assert ObjectiveStatus.ACTIVE.value == "active"
        assert ObjectiveStatus.COMPLETED.value == "completed"
        assert ObjectiveStatus.FAILED.value == "failed"

    def test_reflection_type(self) -> None:
        assert ReflectionType.EXECUTION_REVIEW.value == "execution_review"
        assert ReflectionType.FAILURE_ANALYSIS.value == "failure_analysis"
        assert ReflectionType.SUCCESS_ANALYSIS.value == "success_analysis"

    def test_strategy_type(self) -> None:
        assert StrategyType.PLANNING.value == "planning"
        assert StrategyType.EXECUTION.value == "execution"
        assert StrategyType.MODEL_SELECTION.value == "model_selection"

    def test_approval_type(self) -> None:
        assert ApprovalType.AUTOMATIC.value == "automatic"
        assert ApprovalType.HUMAN.value == "human"
        assert ApprovalType.POLICY.value == "policy"

    def test_safety_level(self) -> None:
        assert SafetyLevel.PERMISSIVE.value == "permissive"
        assert SafetyLevel.NORMAL.value == "normal"
        assert SafetyLevel.STRICT.value == "strict"
        assert SafetyLevel.MAXIMUM.value == "maximum"

    def test_recommendation_status(self) -> None:
        assert RecommendationStatus.PENDING.value == "pending"
        assert RecommendationStatus.APPROVED.value == "approved"
        assert RecommendationStatus.REJECTED.value == "rejected"


# ===== ABCs =====

class TestABCs:
    def test_autonomy_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            AutonomyProvider()

    def test_policy_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            PolicyProvider()

    def test_reflection_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ReflectionProvider()

    def test_strategy_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            StrategyProvider()

    def test_evaluator_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            EvaluatorProvider()

    def test_approval_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ApprovalProvider()

    def test_repository_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            AutonomyRepository()


# ===== Policy Engine =====

class TestPolicyEngine:
    def test_default_policies(self) -> None:
        engine = PolicyEngine()
        all_p = engine.get_all()
        assert "default" in all_p
        assert "strict" in all_p
        assert "autonomous" in all_p

    def test_evaluate_read_allowed(self) -> None:
        engine = PolicyEngine()
        result = engine.evaluate("default", "read")
        assert result["allowed"] is True
        assert result["requires_approval"] is False

    def test_evaluate_write_requires_approval(self) -> None:
        engine = PolicyEngine()
        result = engine.evaluate("default", "write")
        assert result["allowed"] is True
        assert result["requires_approval"] is True

    def test_evaluate_delete_requires_approval(self) -> None:
        engine = PolicyEngine()
        result = engine.evaluate("default", "delete")
        assert result["allowed"] is True
        assert result["requires_approval"] is True

    def test_strict_policy_all_requires_approval(self) -> None:
        engine = PolicyEngine()
        result = engine.evaluate("strict", "read")
        assert result["requires_approval"] is True

    def test_register_custom_policy(self) -> None:
        engine = PolicyEngine()
        custom = AutonomyPolicy(name="custom", level=AutonomyLevel.FULL)
        custom.add_rule(PolicyRule("custom_rule", "custom_action", allowed=True))
        engine.register(custom)
        result = engine.evaluate("custom", "custom_action")
        assert result["allowed"] is True
        assert result["requires_approval"] is False

    def test_resource_constraints(self) -> None:
        engine = PolicyEngine()
        policy = engine.get("default")
        policy.resource_limits = {"cpu": 8, "memory": 16}
        result = engine.check_resource_constraints("default", {"cpu": 4, "memory": 8})
        assert result["within_constraints"] is True

    def test_resource_constraint_violation(self) -> None:
        engine = PolicyEngine()
        policy = engine.get("default")
        policy.resource_limits = {"cpu": 4}
        result = engine.check_resource_constraints("default", {"cpu": 8})
        assert result["within_constraints"] is False
        assert len(result["violations"]) == 1

    def test_get_violations(self) -> None:
        engine = PolicyEngine()
        engine.get_violations()
        assert isinstance(engine.get_violations(), list)

    def test_is_action_allowed(self) -> None:
        engine = PolicyEngine()
        assert engine.is_action_allowed("default", "read") is True

    def test_policy_to_dict(self) -> None:
        policy = AutonomyPolicy(name="test")
        d = policy.to_dict()
        assert d["name"] == "test"
        assert "level" in d
        assert "rules" in d

    def test_policy_rule_to_dict(self) -> None:
        rule = PolicyRule("test", "test_action")
        d = rule.to_dict()
        assert d["name"] == "test"
        assert d["action_pattern"] == "test_action"


# ===== Objective Management =====

class TestObjectiveManager:
    def test_create_objective(self) -> None:
        mgr = ObjectiveManager()
        obj = mgr.create("test_obj", "desc", priority="high")
        assert obj.name == "test_obj"
        assert obj.priority == ObjectivePriority.HIGH

    def test_get_objective(self) -> None:
        mgr = ObjectiveManager()
        obj = mgr.create("test_obj")
        fetched = mgr.get(obj.id)
        assert fetched is not None
        assert fetched.id == obj.id

    def test_get_nonexistent(self) -> None:
        mgr = ObjectiveManager()
        assert mgr.get("nonexistent") is None

    def test_update_status(self) -> None:
        mgr = ObjectiveManager()
        obj = mgr.create("test_obj")
        assert mgr.update_status(obj.id, "active") is True
        assert mgr.get(obj.id).status == ObjectiveStatus.ACTIVE

    def test_update_progress(self) -> None:
        mgr = ObjectiveManager()
        obj = mgr.create("test_obj")
        assert mgr.update_progress(obj.id, 0.5) is True
        assert mgr.get(obj.id).progress == 0.5

    def test_update_progress_clamp(self) -> None:
        mgr = ObjectiveManager()
        obj = mgr.create("test_obj")
        mgr.update_progress(obj.id, 1.5)
        assert mgr.get(obj.id).progress == 1.0
        mgr.update_progress(obj.id, -0.5)
        assert mgr.get(obj.id).progress == 0.0

    def test_prioritize(self) -> None:
        mgr = ObjectiveManager()
        mgr.create("low", priority="low")
        mgr.create("high", priority="high")
        mgr.create("critical", priority="critical")
        prioritized = mgr.prioritize()
        assert prioritized[0].priority == ObjectivePriority.CRITICAL
        assert prioritized[1].priority == ObjectivePriority.HIGH

    def test_ready_objectives(self) -> None:
        mgr = ObjectiveManager()
        dep = mgr.create("dep")
        mgr.update_status(dep.id, "completed")
        obj = mgr.create("main", dependencies=[dep.id])
        ready = mgr.get_ready_objectives()
        assert len(ready) == 1

    def test_not_ready_with_unmet_deps(self) -> None:
        mgr = ObjectiveManager()
        dep = mgr.create("dep")
        main = mgr.create("main", dependencies=[dep.id])
        ready = mgr.get_ready_objectives()
        ready_ids = [o.id for o in ready]
        assert main.id not in ready_ids

    def test_analyze_dependencies(self) -> None:
        mgr = ObjectiveManager()
        dep = mgr.create("dep")
        mgr.update_status(dep.id, "completed")
        obj = mgr.create("main", dependencies=[dep.id])
        analysis = mgr.analyze_dependencies(obj.id)
        assert analysis["found"] is True
        assert analysis["all_met"] is True

    def test_analyze_dependencies_not_found(self) -> None:
        mgr = ObjectiveManager()
        assert mgr.analyze_dependencies("nonexistent")["found"] is False

    def test_score_completion(self) -> None:
        mgr = ObjectiveManager()
        obj = mgr.create("test", priority="critical")
        mgr.update_progress(obj.id, 0.8)
        score = mgr.score_completion(obj.id)
        assert score > 0.0

    def test_remove(self) -> None:
        mgr = ObjectiveManager()
        obj = mgr.create("test")
        assert mgr.remove(obj.id) is True
        assert mgr.get(obj.id) is None
        assert mgr.remove("nonexistent") is False

    def test_count(self) -> None:
        mgr = ObjectiveManager()
        mgr.create("a")
        mgr.create("b")
        assert mgr.count() == 2

    def test_objective_to_dict(self) -> None:
        obj = Objective("test", "desc")
        d = obj.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "desc"
        assert "id" in d


# ===== Evaluator =====

class TestEvaluator:
    def test_evaluate_objective(self) -> None:
        evaluator = Evaluator()
        result = evaluator.evaluate_objective({"id": "1", "priority": "high", "status": "in_progress", "progress": 0.5})
        assert "score" in result
        assert result["score"] > 0

    def test_score_completion(self) -> None:
        evaluator = Evaluator()
        score = evaluator.score_completion(
            {"priority": "high", "progress": 0.8},
            {"success_rate": 0.9, "efficiency": 0.8},
        )
        assert 0.0 <= score <= 1.0

    def test_rank_objectives(self) -> None:
        evaluator = Evaluator()
        objs = [
            {"id": "a", "priority": "low", "status": "pending", "progress": 0.1},
            {"id": "b", "priority": "critical", "status": "completed", "progress": 1.0},
        ]
        ranked = evaluator.rank_objectives(objs)
        assert ranked[0]["objective_id"] == "b"

    def test_get_evaluations(self) -> None:
        evaluator = Evaluator()
        evaluator.evaluate_objective({"id": "1", "priority": "medium", "status": "pending", "progress": 0.0})
        evals = evaluator.get_evaluations()
        assert len(evals) == 1


# ===== Reflection =====

class TestReflectionEngine:
    @pytest.mark.asyncio
    async def test_review_execution(self) -> None:
        engine = ReflectionEngine()
        result = await engine.review_execution("exec1", {"success": True, "duration_ms": 100})
        assert result["type"] == "execution_review"
        assert len(result["findings"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_failure(self) -> None:
        engine = ReflectionEngine()
        result = await engine.analyze_failure("exec1", "timeout")
        assert result["type"] == "failure_analysis"
        assert len(result["lessons"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_success(self) -> None:
        engine = ReflectionEngine()
        result = await engine.analyze_success("exec1", {"summary": "good"})
        assert result["type"] == "success_analysis"

    @pytest.mark.asyncio
    async def test_evaluate_outcome(self) -> None:
        engine = ReflectionEngine()
        result = await engine.evaluate_outcome("exec1", {"a": 1, "b": 2}, {"a": 1, "b": 3})
        assert "findings" in result

    @pytest.mark.asyncio
    async def test_extract_lessons(self) -> None:
        engine = ReflectionEngine()
        lessons = await engine.extract_lessons([{"findings": ["lesson1"], "type": "test"}])
        assert len(lessons) > 0

    def test_get_records(self) -> None:
        engine = ReflectionEngine()
        assert engine.get_records() == []

    def test_get_lessons(self) -> None:
        engine = ReflectionEngine()
        assert engine.get_lessons() == []

    def test_get_records_by_type(self) -> None:
        engine = ReflectionEngine()
        assert engine.get_records_by_type(ReflectionType.FAILURE_ANALYSIS) == []


# ===== Planner =====

class TestAutonomousPlanner:
    @pytest.mark.asyncio
    async def test_propose_plan(self) -> None:
        planner = AutonomousPlanner()
        plan = await planner.propose_plan("obj1")
        assert plan.objective_id == "obj1"
        assert len(plan.steps) > 0
        assert plan.status == "proposed"

    @pytest.mark.asyncio
    async def test_get_plan(self) -> None:
        planner = AutonomousPlanner()
        plan = await planner.propose_plan("obj1")
        assert planner.get_plan(plan.id) is not None

    @pytest.mark.asyncio
    async def test_approve_plan(self) -> None:
        planner = AutonomousPlanner()
        plan = await planner.propose_plan("obj1")
        assert planner.approve_plan(plan.id) is True
        assert plan.status == "approved"

    @pytest.mark.asyncio
    async def test_complete_plan(self) -> None:
        planner = AutonomousPlanner()
        plan = await planner.propose_plan("obj1")
        planner.complete_plan(plan.id)
        assert plan.status == "completed"

    @pytest.mark.asyncio
    async def test_cancel_plan(self) -> None:
        planner = AutonomousPlanner()
        plan = await planner.propose_plan("obj1")
        assert planner.cancel_plan(plan.id) is True
        assert plan.status == "cancelled"

    def test_count(self) -> None:
        planner = AutonomousPlanner()
        assert planner.count() == 0

    def test_plan_to_dict(self) -> None:
        plan = Plan("obj1")
        plan.add_step(PlanStep(action="test", order=0))
        d = plan.to_dict()
        assert d["objective_id"] == "obj1"
        assert "steps" in d

    def test_plan_step_to_dict(self) -> None:
        step = PlanStep(action="test", target="target")
        d = step.to_dict()
        assert d["action"] == "test"


# ===== Optimizer =====

class TestOptimizer:
    @pytest.mark.asyncio
    async def test_optimize_workflows(self) -> None:
        opt = Optimizer()
        result = await opt.optimize_workflows({"wf1": {"steps": ["a", "b", "c"]}})
        assert result.category == "workflow"
        assert result.gain >= 0.0

    @pytest.mark.asyncio
    async def test_optimize_task_execution(self) -> None:
        opt = Optimizer()
        result = await opt.optimize_task_execution([{"name": "t1", "priority": 1}])
        assert result.category == "task_execution"

    @pytest.mark.asyncio
    async def test_recommend_model_selection(self) -> None:
        opt = Optimizer()
        result = await opt.recommend_model_selection({"complexity": "low", "max_latency_ms": 500})
        assert "recommended_model" in result

    @pytest.mark.asyncio
    async def test_recommend_tool_selection(self) -> None:
        opt = Optimizer()
        result = await opt.recommend_tool_selection("do something", ["tool_a", "tool_b"])
        assert "recommended_tools" in result

    def test_get_total_gain(self) -> None:
        opt = Optimizer()
        assert opt.get_total_gain() == 0.0

    def test_get_results(self) -> None:
        opt = Optimizer()
        assert opt.get_results() == []

    def test_optimization_result_to_dict(self) -> None:
        from app.autonomy.optimizer import OptimizationResult
        r = OptimizationResult("test", {"a": 1}, {"b": 2}, 0.1)
        d = r.to_dict()
        assert d["category"] == "test"
        assert d["gain"] == 0.1


# ===== Adaptation =====

class TestAdaptationEngine:
    def test_get_default_strategy(self) -> None:
        engine = AdaptationEngine()
        assert engine.get_strategy("planning") == "default"

    def test_adapt_low_performance(self) -> None:
        engine = AdaptationEngine()
        result = engine.adapt("planning", {"performance": 0.1})
        assert result == "conservative"

    def test_adapt_high_performance(self) -> None:
        engine = AdaptationEngine()
        result = engine.adapt("planning", {"performance": 0.9})
        assert result == "aggressive"

    def test_adapt_medium_performance(self) -> None:
        engine = AdaptationEngine()
        result = engine.adapt("planning", {"performance": 0.5})
        assert result == "balanced"

    def test_set_strategy(self) -> None:
        engine = AdaptationEngine()
        engine.set_strategy("planning", "custom")
        assert engine.get_strategy("planning") == "custom"

    def test_get_all_strategies(self) -> None:
        engine = AdaptationEngine()
        all_s = engine.get_all_strategies()
        assert len(all_s) == len(StrategyType)

    def test_get_history(self) -> None:
        engine = AdaptationEngine()
        engine.adapt("planning", {"performance": 0.1})
        history = engine.get_history()
        assert len(history) == 1

    def test_reset(self) -> None:
        engine = AdaptationEngine()
        engine.set_strategy("planning", "custom")
        engine.reset()
        assert engine.get_strategy("planning") == "default"


# ===== Strategy Manager =====

class TestStrategyManager:
    def test_default_strategies(self) -> None:
        mgr = StrategyManager()
        for st in StrategyType:
            strategies = mgr.get_strategies(st.value)
            assert len(strategies) > 0

    def test_register(self) -> None:
        mgr = StrategyManager()
        entry = StrategyEntry(name="custom", strategy_type=StrategyType.PLANNING, description="Custom")
        mgr.register(entry)
        strategies = mgr.get_strategies("planning")
        assert any(s.name == "custom" for s in strategies)

    def test_select(self) -> None:
        mgr = StrategyManager()
        selected = mgr.select("planning", {"risk_tolerance": 0.5})
        assert selected is not None
        assert selected.name in ("default", "conservative", "balanced", "aggressive")

    def test_get_all_types(self) -> None:
        mgr = StrategyManager()
        types = mgr.get_all_types()
        assert "planning" in types

    def test_count(self) -> None:
        mgr = StrategyManager()
        assert mgr.count() > 0


# ===== Governor =====

class TestAutonomyGovernor:
    def test_default_level(self) -> None:
        gov = AutonomyGovernor()
        assert gov.level == AutonomyLevel.SUPERVISED

    def test_begin_action(self) -> None:
        gov = AutonomyGovernor()
        assert gov.begin_action() is True
        gov.end_action()

    def test_manual_blocks(self) -> None:
        gov = AutonomyGovernor(level=AutonomyLevel.MANUAL)
        assert gov.begin_action() is False

    def test_can_execute(self) -> None:
        gov = AutonomyGovernor()
        assert gov.can_execute() is True

    def test_requires_approval_supervised(self) -> None:
        gov = AutonomyGovernor(level=AutonomyLevel.SUPERVISED)
        assert gov.requires_approval("write") is True
        assert gov.requires_approval("read") is False

    def test_requires_approval_autonomous(self) -> None:
        gov = AutonomyGovernor(level=AutonomyLevel.AUTONOMOUS)
        assert gov.requires_approval("read") is False
        assert gov.requires_approval("deploy") is True

    def test_get_stats(self) -> None:
        gov = AutonomyGovernor()
        stats = gov.get_stats()
        assert "level" in stats
        assert "active_actions" in stats

    def test_set_max_concurrent(self) -> None:
        gov = AutonomyGovernor()
        gov.set_max_concurrent(10)
        stats = gov.get_stats()
        assert stats["max_concurrent"] == 10


# ===== Approval =====

class TestApprovalManager:
    @pytest.mark.asyncio
    async def test_auto_approve_high_confidence(self) -> None:
        mgr = ApprovalManager()
        result = await mgr.request_approval({"id": "rec1", "confidence": 0.9, "risk_level": "low"})
        assert result["status"] == "approved"

    @pytest.mark.asyncio
    async def test_pending_human_approval(self) -> None:
        mgr = ApprovalManager()
        result = await mgr.request_approval({"id": "rec1", "confidence": 0.5, "risk_level": "high"})
        assert result["status"] == "pending"

    def test_is_auto_approved(self) -> None:
        mgr = ApprovalManager()
        assert mgr.is_auto_approved({"confidence": 0.9, "risk_level": "low"}) is True
        assert mgr.is_auto_approved({"confidence": 0.3, "risk_level": "high"}) is False

    @pytest.mark.asyncio
    async def test_approve(self) -> None:
        mgr = ApprovalManager()
        result = await mgr.request_approval({"id": "rec1", "confidence": 0.5, "risk_level": "high"})
        record_id = result["id"]
        assert mgr.approve(record_id, "human") is True

    @pytest.mark.asyncio
    async def test_reject(self) -> None:
        mgr = ApprovalManager()
        result = await mgr.request_approval({"id": "rec1", "confidence": 0.5, "risk_level": "high"})
        record_id = result["id"]
        assert mgr.reject(record_id, "not safe") is True

    def test_get_stats(self) -> None:
        mgr = ApprovalManager()
        stats = mgr.get_stats()
        assert "total" in stats
        assert "approved" in stats

    def test_set_auto_approve_threshold(self) -> None:
        mgr = ApprovalManager()
        mgr.set_auto_approve_threshold(0.9)
        assert mgr._auto_approve_threshold == 0.9


# ===== Safety =====

class TestSafetyEngine:
    def test_check_safe_action(self) -> None:
        engine = SafetyEngine()
        result = engine.check_action("read", {"action_id": "a1", "requires_auth": True})
        assert result["safe"] is True

    def test_check_recursive(self) -> None:
        engine = SafetyEngine()
        for _ in range(4):
            engine.begin_action("loop")
        result = engine.check_action("loop", {"action_id": "loop"})
        assert result["safe"] is True
        engine.begin_action("loop")
        result2 = engine.check_action("loop", {"action_id": "loop"})
        assert result2["safe"] is False

    def test_record_retry(self) -> None:
        engine = SafetyEngine()
        assert engine.record_retry("action1") is True
        assert engine.record_retry("action1") is True
        assert engine.record_retry("action1") is True

    def test_reset_retries(self) -> None:
        engine = SafetyEngine()
        engine.record_retry("action1")
        engine.reset_retries("action1")

    def test_add_constraint(self) -> None:
        engine = SafetyEngine()
        engine.add_constraint(SafetyConstraint("custom", "Custom constraint"))
        constraints = engine.get_constraints()
        assert any(c["name"] == "custom" for c in constraints)

    def test_get_violations(self) -> None:
        engine = SafetyEngine()
        assert isinstance(engine.get_violations(), list)

    def test_end_action(self) -> None:
        engine = SafetyEngine()
        engine.begin_action("a1")
        engine.end_action("a1")


# ===== Lifecycle =====

class TestAutonomyLifecycle:
    def test_initial_state(self) -> None:
        lc = AutonomyLifecycle()
        assert lc.state == AutonomyState.REGISTERED

    def test_full_lifecycle(self) -> None:
        lc = AutonomyLifecycle()
        assert lc.transition(AutonomyState.INITIALIZED) is True
        assert lc.transition(AutonomyState.READY) is True
        assert lc.transition(AutonomyState.OBSERVING) is True
        assert lc.transition(AutonomyState.ANALYZING) is True
        assert lc.transition(AutonomyState.RECOMMENDING) is True
        assert lc.transition(AutonomyState.APPROVED) is True
        assert lc.transition(AutonomyState.EXECUTING) is True
        assert lc.transition(AutonomyState.LEARNING) is True
        assert lc.state == AutonomyState.LEARNING

    def test_invalid_transition(self) -> None:
        lc = AutonomyLifecycle()
        assert lc.transition(AutonomyState.EXECUTING) is False

    def test_is_running(self) -> None:
        lc = AutonomyLifecycle()
        assert lc.is_running() is False
        lc.transition(AutonomyState.INITIALIZED)
        lc.transition(AutonomyState.READY)
        assert lc.is_running() is True

    def test_shutdown(self) -> None:
        lc = AutonomyLifecycle()
        lc.transition(AutonomyState.INITIALIZED)
        lc.transition(AutonomyState.READY)
        lc.transition(AutonomyState.SHUTDOWN)
        assert lc.transition(AutonomyState.READY) is False

    def test_get_status(self) -> None:
        lc = AutonomyLifecycle()
        status = lc.get_status()
        assert "state" in status
        assert "uptime_seconds" in status

    def test_get_history(self) -> None:
        lc = AutonomyLifecycle()
        lc.transition(AutonomyState.INITIALIZED)
        history = lc.get_history()
        assert len(history) == 1


# ===== Persistence =====

class TestInMemoryRepository:
    @pytest.mark.asyncio
    async def test_save_and_get(self) -> None:
        repo = InMemoryAutonomyRepository()
        await repo.save("obj", "1", {"name": "test"})
        result = await repo.get("obj", "1")
        assert result is not None
        assert result["name"] == "test"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self) -> None:
        repo = InMemoryAutonomyRepository()
        assert await repo.get("obj", "none") is None

    @pytest.mark.asyncio
    async def test_list(self) -> None:
        repo = InMemoryAutonomyRepository()
        await repo.save("obj", "1", {"name": "a"})
        await repo.save("obj", "2", {"name": "b"})
        items = await repo.list("obj")
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        repo = InMemoryAutonomyRepository()
        await repo.save("obj", "1", {"name": "a"})
        assert await repo.delete("obj", "1") is True
        assert await repo.delete("obj", "1") is False

    @pytest.mark.asyncio
    async def test_count(self) -> None:
        repo = InMemoryAutonomyRepository()
        await repo.save("obj", "1", {"name": "a"})
        assert await repo.count("obj") == 1

    def test_clear(self) -> None:
        repo = InMemoryAutonomyRepository()
        repo.clear()


# ===== Metrics =====

class TestAutonomyMetricsCollector:
    def test_start(self) -> None:
        mc = AutonomyMetricsCollector()
        mc.start()
        s = mc.snapshot()
        assert s.recommendations_generated == 0

    def test_record_all(self) -> None:
        mc = AutonomyMetricsCollector()
        mc.start()
        mc.record_recommendation()
        mc.record_approval()
        mc.record_rejection()
        mc.record_optimization_gain(0.5)
        mc.record_policy_violation()
        mc.record_autonomous_execution()
        s = mc.snapshot()
        assert s.recommendations_generated == 1
        assert s.approvals == 1
        assert s.rejections == 1
        assert s.optimization_gains == 0.5
        assert s.policy_violations == 1
        assert s.autonomous_executions == 1

    def test_reset(self) -> None:
        mc = AutonomyMetricsCollector()
        mc.start()
        mc.record_recommendation()
        mc.reset()
        s = mc.snapshot()
        assert s.recommendations_generated == 0

    def test_to_dict(self) -> None:
        mc = AutonomyMetricsCollector()
        mc.start()
        s = mc.snapshot()
        d = s.to_dict()
        assert "recommendations_generated" in d
        assert "uptime_seconds" in d


# ===== Tracing =====

class TestAutonomyTracer:
    def test_start_and_finish(self) -> None:
        tracer = AutonomyTracer()
        tid = tracer.start_trace("op1")
        assert tracer.count() == 1
        tracer.finish_trace(tid)
        traces = tracer.get_traces()
        assert traces[0]["status"] == "completed"

    def test_finish_with_error(self) -> None:
        tracer = AutonomyTracer()
        tid = tracer.start_trace("op1")
        tracer.finish_trace(tid, "error", "boom")
        t = tracer.get_trace(tid)
        assert t is not None
        assert t["status"] == "error"

    def test_get_trace_not_found(self) -> None:
        tracer = AutonomyTracer()
        assert tracer.get_trace("none") is None

    def test_max_traces(self) -> None:
        tracer = AutonomyTracer(max_traces=5)
        for i in range(10):
            tracer.start_trace(f"op{i}")
        assert tracer.count() == 5

    def test_clear(self) -> None:
        tracer = AutonomyTracer()
        tracer.start_trace("op1")
        tracer.clear()
        assert tracer.count() == 0


# ===== Manager =====

class TestAutonomyManager:
    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        mgr = AutonomyManager()
        await mgr.start()
        assert mgr.is_running() is True
        await mgr.shutdown()
        assert mgr.is_running() is False

    @pytest.mark.asyncio
    async def test_evaluate_objectives(self) -> None:
        mgr = AutonomyManager()
        await mgr.start()
        result = await mgr.evaluate_objectives()
        assert isinstance(result, list)
        await mgr.shutdown()

    @pytest.mark.asyncio
    async def test_propose_plan(self) -> None:
        mgr = AutonomyManager()
        await mgr.start()
        plan = await mgr.propose_plan("obj1")
        assert "steps" in plan
        await mgr.shutdown()

    @pytest.mark.asyncio
    async def test_recommend_improvements(self) -> None:
        mgr = AutonomyManager()
        await mgr.start()
        recs = await mgr.recommend_improvements()
        assert len(recs) > 0
        await mgr.shutdown()

    @pytest.mark.asyncio
    async def test_adapt_strategy(self) -> None:
        mgr = AutonomyManager()
        await mgr.start()
        result = await mgr.adapt_strategy("planning", {"performance": 0.9})
        assert result["new_strategy"] == "aggressive"
        await mgr.shutdown()

    @pytest.mark.asyncio
    async def test_optimize_workflows(self) -> None:
        mgr = AutonomyManager()
        await mgr.start()
        result = await mgr.optimize_workflows({"wf1": {"steps": ["a", "b"]}})
        assert "gain" in result
        await mgr.shutdown()

    @pytest.mark.asyncio
    async def test_recommend_model_selection(self) -> None:
        mgr = AutonomyManager()
        await mgr.start()
        result = await mgr.recommend_model_selection({"complexity": "low"})
        assert "recommended_model" in result
        await mgr.shutdown()

    def test_get_status(self) -> None:
        mgr = AutonomyManager()
        status = mgr.get_status()
        assert "state" in status
        assert "autonomy_level" in status

    def test_get_policies(self) -> None:
        mgr = AutonomyManager()
        policies = mgr.get_policies()
        assert "default" in policies

    def test_properties(self) -> None:
        mgr = AutonomyManager()
        assert mgr.lifecycle is not None
        assert mgr.governor is not None
        assert mgr.policy is not None
        assert mgr.objectives is not None
        assert mgr.evaluator is not None
        assert mgr.reflection is not None
        assert mgr.planner is not None
        assert mgr.optimizer is not None
        assert mgr.adaptation is not None
        assert mgr.strategy is not None
        assert mgr.safety is not None
        assert mgr.approval is not None


# ===== Engine =====

class TestAutonomyEngine:
    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        engine = AutonomyEngine()
        await engine.start()
        assert engine.is_running() is True
        await engine.shutdown()
        assert engine.is_running() is False

    @pytest.mark.asyncio
    async def test_evaluate_objectives(self) -> None:
        engine = AutonomyEngine()
        await engine.start()
        result = await engine.evaluate_objectives()
        assert isinstance(result, list)
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_recommend_improvements(self) -> None:
        engine = AutonomyEngine()
        await engine.start()
        recs = await engine.recommend_improvements()
        assert len(recs) > 0
        await engine.shutdown()

    def test_get_status(self) -> None:
        engine = AutonomyEngine()
        status = engine.get_status()
        assert "state" in status

    def test_get_policies(self) -> None:
        engine = AutonomyEngine()
        policies = engine.get_policies()
        assert "default" in policies

    def test_get_metrics(self) -> None:
        engine = AutonomyEngine()
        metrics = engine.get_metrics()
        assert "recommendations_generated" in metrics

    def test_get_traces(self) -> None:
        engine = AutonomyEngine()
        assert engine.get_traces() == []

    def test_get_reflections(self) -> None:
        engine = AutonomyEngine()
        assert engine.get_reflections() == []

    def test_get_objectives(self) -> None:
        engine = AutonomyEngine()
        assert engine.get_objectives() == []

    def test_manager_property(self) -> None:
        engine = AutonomyEngine()
        assert isinstance(engine.manager, AutonomyManager)


# ===== Factory =====

class TestAutonomyFactory:
    def test_create_default(self) -> None:
        engine = AutonomyFactory.create_default()
        assert isinstance(engine, AutonomyEngine)

    def test_create(self) -> None:
        engine = AutonomyFactory.create(name="test")
        assert isinstance(engine, AutonomyEngine)

    def test_get_or_create(self) -> None:
        AutonomyFactory.reset()
        e1 = AutonomyFactory.get_or_create()
        e2 = AutonomyFactory.get_or_create()
        assert e1 is e2
        AutonomyFactory.reset()

    def test_reset(self) -> None:
        AutonomyFactory.reset()
        assert AutonomyFactory._instance is None
