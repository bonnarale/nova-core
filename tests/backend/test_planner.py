"""Tests for Autonomous Planner v1 — models, strategy, executor, reviewer,
replanner, and the main Planner orchestrator.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.planner.executor import AgentStepExecutor, StepExecutor
from app.planner.plan import Plan, PlanStatus, RetryPolicy, Step, StepStatus, ToolCall
from app.planner.planner import Planner
from app.planner.replanner import BasicReplanStrategy, ReplanStrategy
from app.planner.reviewer import ResultStepReviewer, ReviewResult, ReviewVerdict, StepReviewer
from app.planner.strategy import PlanDecompositionStrategy, RuleBasedDecompositionStrategy


# ======================================================================
# Fakes
# ======================================================================

class FakeAgentManager:
    """In-memory fake for AgentManager."""

    def __init__(self) -> None:
        self._agents: dict[str, MagicMock] = {
            "planner": MagicMock(),
            "coder": MagicMock(),
            "researcher": MagicMock(),
            "reviewer": MagicMock(),
            "executor": MagicMock(),
        }
        self.dispatches: list[dict] = []

    def get_runtime_agent(self, agent_id: str) -> MagicMock | None:
        return self._agents.get(agent_id)

    def list_runtime_agents(self) -> list[MagicMock]:
        return list(self._agents.values())

    async def dispatch(self, agent_id: str, task: str, context: dict | None = None) -> dict:
        self.dispatches.append({"agent_id": agent_id, "task": task})
        return {"status": "success", "result": {"output": f"Executed: {task[:40]}"}}


# ======================================================================
# Plan / Step data model tests
# ======================================================================

class TestPlanModel:
    def test_default_creation(self):
        plan = Plan()
        assert plan.id
        assert plan.status == PlanStatus.DRAFT
        assert plan.progress == 0.0
        assert plan.created_at
        assert plan.updated_at

    def test_plan_with_steps(self):
        s1 = Step(id="s1", title="Step 1", status=StepStatus.SUCCEEDED)
        s2 = Step(id="s2", title="Step 2", status=StepStatus.PENDING, dependencies=["s1"])
        plan = Plan(id="p1", objective="Test", steps=[s1, s2])
        assert plan.progress == 50.0
        assert plan.next_ready_steps == [s2]

    def test_next_ready_steps_respects_dependencies(self):
        s1 = Step(id="s1", title="A", dependencies=[])
        s2 = Step(id="s2", title="B", dependencies=["s1"])
        s3 = Step(id="s3", title="C", dependencies=["s1", "s2"])
        plan = Plan(steps=[s1, s2, s3])
        # s1 is PENDING with no deps -> ready
        assert s1 in plan.next_ready_steps
        assert s2 not in plan.next_ready_steps
        assert s3 not in plan.next_ready_steps

    def test_to_dict(self):
        plan = Plan(id="p1", objective="test", status=PlanStatus.ACTIVE)
        d = plan.to_dict()
        assert d["id"] == "p1"
        assert d["objective"] == "test"
        assert d["status"] == "ACTIVE"
        assert "progress" in d

    def test_active_step(self):
        s1 = Step(id="s1", status=StepStatus.SUCCEEDED)
        s2 = Step(id="s2", status=StepStatus.RUNNING)
        plan = Plan(steps=[s1, s2])
        assert plan.active_step == s2

    def test_no_active_step(self):
        s1 = Step(id="s1", status=StepStatus.SUCCEEDED)
        plan = Plan(steps=[s1])
        assert plan.active_step is None

    def test_progress_empty(self):
        assert Plan().progress == 0.0


class TestStepModel:
    def test_default_creation(self):
        step = Step()
        assert step.id
        assert step.status == StepStatus.PENDING
        assert step.retry_policy.max_retries == 2

    def test_custom_retry(self):
        step = Step(retry_policy=RetryPolicy(max_retries=0))
        assert step.retry_policy.max_retries == 0

    def test_tool_calls_default(self):
        step = Step()
        assert step.tool_calls == []

    def test_succeeded_status(self):
        step = Step(status=StepStatus.SUCCEEDED)
        step.result = {"output": "done"}
        assert step.status == StepStatus.SUCCEEDED


# ======================================================================
# Strategy tests
# ======================================================================

class TestRuleBasedDecompositionStrategy:
    @pytest.mark.asyncio
    async def test_decompose_landing_page(self):
        strategy = RuleBasedDecompositionStrategy()
        plan = await strategy.decompose("Build a landing page for my startup")
        assert plan.objective == "Build a landing page for my startup"
        assert plan.status == PlanStatus.DRAFT
        assert len(plan.steps) >= 4
        assert any("HTML" in s.title for s in plan.steps)

    @pytest.mark.asyncio
    async def test_decompose_backend(self):
        strategy = RuleBasedDecompositionStrategy()
        plan = await strategy.decompose("Create a backend API")
        assert len(plan.steps) >= 4
        assert any("API" in s.title or "endpoint" in s.title.lower() for s in plan.steps)

    @pytest.mark.asyncio
    async def test_decompose_research(self):
        strategy = RuleBasedDecompositionStrategy()
        plan = await strategy.decompose("Research about machine learning")
        assert len(plan.steps) >= 3
        assert any("research" in s.title.lower() or "gather" in s.title.lower() for s in plan.steps)

    @pytest.mark.asyncio
    async def test_decompose_unknown_fallback(self):
        strategy = RuleBasedDecompositionStrategy()
        plan = await strategy.decompose("Do something random")
        assert len(plan.steps) >= 3
        assert plan.metadata.get("domain") == "unknown"

    @pytest.mark.asyncio
    async def test_decompose_sets_user_id(self):
        strategy = RuleBasedDecompositionStrategy()
        plan = await strategy.decompose("Build a site", user_id="user-1")
        assert plan.user_id == "user-1"


# ======================================================================
# Executor tests
# ======================================================================

class TestAgentStepExecutor:
    @pytest.mark.asyncio
    async def test_execute_success(self):
        agent_manager = FakeAgentManager()
        executor = AgentStepExecutor(agent_manager)
        step = Step(
            id="s1",
            title="Build HTML",
            description="Create index.html",
            assigned_agent="coder",
        )
        result = await executor.execute(step)

        assert result.status == StepStatus.SUCCEEDED
        assert result.started_at is not None
        assert result.completed_at is not None
        assert len(result.tool_calls) == 1
        assert len(agent_manager.dispatches) == 1
        assert agent_manager.dispatches[0]["agent_id"] == "coder"

    @pytest.mark.asyncio
    async def test_execute_fails_when_agent_missing(self):
        agent_manager = FakeAgentManager()
        executor = AgentStepExecutor(agent_manager)
        step = Step(id="s1", title="X", assigned_agent="nonexistent")
        result = await executor.execute(step)

        assert result.status == StepStatus.FAILED
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_execute_defaults_to_executor(self):
        agent_manager = FakeAgentManager()
        executor = AgentStepExecutor(agent_manager)
        step = Step(id="s1", title="Default agent", assigned_agent=None)
        result = await executor.execute(step)

        assert result.status == StepStatus.SUCCEEDED


# ======================================================================
# Reviewer tests
# ======================================================================

class TestResultStepReviewer:
    @pytest.mark.asyncio
    async def test_review_success(self):
        reviewer = ResultStepReviewer()
        step = Step(title="OK", status=StepStatus.SUCCEEDED, result={"output": "done"})
        review = await reviewer.review(step)
        assert review.verdict == ReviewVerdict.SUCCESS

    @pytest.mark.asyncio
    async def test_review_success_with_error_in_result(self):
        reviewer = ResultStepReviewer()
        step = Step(
            title="Has error",
            status=StepStatus.SUCCEEDED,
            result={"error": "Something wrong"},
        )
        review = await reviewer.review(step)
        assert review.verdict == ReviewVerdict.REPLAN
        assert step.status == StepStatus.FAILED

    @pytest.mark.asyncio
    async def test_review_failure_with_retry_remaining(self):
        reviewer = ResultStepReviewer()
        step = Step(
            title="Retry me",
            status=StepStatus.FAILED,
            retry_policy=RetryPolicy(max_retries=3, delay_seconds=0.1),
            retry_count=0,
        )
        review = await reviewer.review(step)
        assert review.verdict == ReviewVerdict.RETRY
        assert step.retry_count == 1

    @pytest.mark.asyncio
    async def test_review_failure_exhausts_retries(self):
        reviewer = ResultStepReviewer()
        step = Step(
            title="Exhausted",
            status=StepStatus.FAILED,
            retry_policy=RetryPolicy(max_retries=1, delay_seconds=0.1),
            retry_count=1,
        )
        review = await reviewer.review(step)
        assert review.verdict == ReviewVerdict.REPLAN

    @pytest.mark.asyncio
    async def test_review_unexpected_status(self):
        reviewer = ResultStepReviewer()
        step = Step(title="Strange", status=StepStatus.RUNNING)
        review = await reviewer.review(step)
        assert review.verdict == ReviewVerdict.FAIL


# ======================================================================
# Replanner tests
# ======================================================================

class TestBasicReplanStrategy:
    @pytest.mark.asyncio
    async def test_replan_inserts_fallback_step(self):
        replanner = BasicReplanStrategy()
        s1 = Step(id="s1", title="Step 1", status=StepStatus.SUCCEEDED)
        s2 = Step(id="s2", title="Step 2", status=StepStatus.FAILED, assigned_agent="coder")
        plan = Plan(steps=[s1, s2])

        result = await replanner.replan(plan, s2, "Compilation error")
        assert len(result.steps) == 3  # original 2 + fallback
        assert result.steps[2].title.startswith("Fallback:")
        assert "coder" in result.steps[2].assigned_agent

    @pytest.mark.asyncio
    async def test_replan_marks_downstream_blocked(self):
        replanner = BasicReplanStrategy()
        s1 = Step(id="s1", title="A", status=StepStatus.SUCCEEDED)
        s2 = Step(id="s2", title="B", status=StepStatus.FAILED)
        s3 = Step(id="s3", title="C", status=StepStatus.PENDING)
        plan = Plan(steps=[s1, s2, s3])

        result = await replanner.replan(plan, s2, "Error")
        assert result.steps[3].status == StepStatus.BLOCKED

    @pytest.mark.asyncio
    async def test_replan_fallback_agent_mapping(self):
        replanner = BasicReplanStrategy()
        s1 = Step(id="s1", title="Research", status=StepStatus.FAILED, assigned_agent="researcher")
        plan = Plan(steps=[s1])
        result = await replanner.replan(plan, s1, "Not found")
        fallback = result.steps[1]
        assert "gather more information" in fallback.description.lower() or "research" in fallback.description.lower()


# ======================================================================
# Planner orchestrator tests
# ======================================================================

class TestPlanner:
    @pytest.fixture
    def fake_agent_manager(self) -> FakeAgentManager:
        return FakeAgentManager()

    @pytest.fixture
    def planner(self, fake_agent_manager: FakeAgentManager) -> Planner:
        return Planner(
            agent_manager=fake_agent_manager,
        )

    @pytest.mark.asyncio
    async def test_create_plan(self, planner: Planner):
        plan = await planner.create_plan(
            objective="Build a landing page",
            user_id="user-1",
            session_id="session-1",
        )
        assert plan.objective == "Build a landing page"
        assert plan.status == PlanStatus.ACTIVE
        assert plan.user_id == "user-1"
        assert plan.session_id == "session-1"
        assert len(plan.steps) >= 4

    @pytest.mark.asyncio
    async def test_execute_plan_all_succeed(
        self,
        planner: Planner,
        fake_agent_manager: FakeAgentManager,
    ):
        plan = await planner.create_plan("Build a landing page")
        result = await planner.execute_plan(plan)

        assert result.status == PlanStatus.COMPLETED
        assert result.progress == 100.0
        assert len(fake_agent_manager.dispatches) >= 4

    @pytest.mark.asyncio
    async def test_cancel_plan(
        self,
        planner: Planner,
        fake_agent_manager: FakeAgentManager,
    ):
        plan = await planner.create_plan("Build a landing page")
        cancelled = await planner.cancel_plan(plan)
        assert cancelled.status == PlanStatus.CANCELLED
        assert all(s.status == StepStatus.SKIPPED for s in cancelled.steps if s.status == StepStatus.RUNNING)

    @pytest.mark.asyncio
    async def test_cancel_non_active_plan(
        self,
        planner: Planner,
    ):
        plan = Plan(objective="test", status=PlanStatus.COMPLETED)
        result = await planner.cancel_plan(plan)
        assert result.status == PlanStatus.COMPLETED  # unchanged

    @pytest.mark.asyncio
    async def test_get_plan_status(
        self,
        planner: Planner,
    ):
        plan = await planner.create_plan("Build a landing page")
        result = await planner.execute_plan(plan)
        status = await planner.get_plan_status(result)
        assert status["status"] == "COMPLETED"
        assert status["progress"] == 100.0
        assert status["steps_completed"] > 0

    @pytest.mark.asyncio
    async def test_execute_already_completed_plan(
        self,
        planner: Planner,
    ):
        plan = Plan(objective="done", status=PlanStatus.COMPLETED)
        result = await planner.execute_plan(plan)
        assert result.status == PlanStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_replan_on_failure(
        self,
        fake_agent_manager: FakeAgentManager,
    ):
        """Simulate a step failure that triggers replanning."""
        class FailingExecutor(StepExecutor):
            def __init__(self):
                self.call_count = 0
                self.max_fails = 3  # only fail the first few steps

            async def execute(self, step, context=None):
                self.call_count += 1
                if self.call_count <= self.max_fails:
                    step.status = StepStatus.FAILED
                    step.error = "Simulated failure"
                else:
                    step.status = StepStatus.SUCCEEDED
                    step.result = {"output": "recovered"}
                return step

        executor = FailingExecutor()
        strategy = RuleBasedDecompositionStrategy()

        planner = Planner(
            agent_manager=fake_agent_manager,
            step_executor=executor,
            decomposition_strategy=strategy,
        )
        plan = await planner.create_plan("Build a landing page")
        result = await planner.execute_plan(plan)

        assert result.status in (PlanStatus.COMPLETED, PlanStatus.FAILED)
        assert 1 <= sum(1 for s in result.steps if s.status == StepStatus.FAILED) <= 3

    @pytest.mark.asyncio
    async def test_strategy_setter(self, planner: Planner):
        new_strategy = RuleBasedDecompositionStrategy()
        planner.decomposition_strategy = new_strategy
        assert planner.decomposition_strategy is new_strategy

    @pytest.mark.asyncio
    async def test_executor_setter(self, planner: Planner, fake_agent_manager: FakeAgentManager):
        new_executor = AgentStepExecutor(fake_agent_manager)
        planner.step_executor = new_executor
        assert planner.step_executor is new_executor


# ======================================================================
# Edge cases
# ======================================================================

class TestPlannerEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_objective_creates_fallback_plan(self):
        planner = Planner(agent_manager=FakeAgentManager())
        plan = await planner.create_plan("")
        assert len(plan.steps) >= 3

    @pytest.mark.asyncio
    async def test_single_step_plan(self):
        planner = Planner(agent_manager=FakeAgentManager())
        plan = await planner.create_plan("Do one thing")
        await planner.execute_plan(plan)
        assert plan.status == PlanStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_plan_with_no_agents(self):
        from app.planner.reviewer import ReviewVerdict

        am = FakeAgentManager()
        am._agents = {}

        planner = Planner(
            agent_manager=am,
            max_replans=2,
        )
        plan = await planner.create_plan("Test")
        result = await planner.execute_plan(plan)

        assert result.status in (PlanStatus.FAILED,)
        assert any(s.status == StepStatus.FAILED for s in result.steps)


# ======================================================================
# Integration: Planner + Cognitive Engine
# ======================================================================

class TestPlannerCognitiveIntegration:
    @pytest.mark.asyncio
    async def test_create_plan_via_cognitive_engine(self):
        from uuid import uuid4

        from app.cognitive.engine import CognitiveEngine
        from app.cognitive.context import CognitiveContext, IntentType

        agent_manager = FakeAgentManager()
        planner = Planner(agent_manager=agent_manager)

        engine = CognitiveEngine(
            goal_manager=MagicMock(),
            task_manager=MagicMock(),
            agent_manager=agent_manager,
            profile_memory=MagicMock(),
            conversation_memory=MagicMock(),
            planner=planner,
        )

        state = await engine.process(raw_input="build a landing page", user_id=str(uuid4()))
        assert state.decision is not None
        assert state.decision.action.value == "CREATE_PLAN"
        assert state.execution_result is not None
        assert "created_plan" in state.execution_result
