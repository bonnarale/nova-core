"""Integration tests for Multi-Agent Runtime (Chapter 14)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents import (
    AgentCapability,
    AgentCoordinator,
    AgentDispatcher,
    AgentExecutor,
    AgentFactory,
    AgentRegistry,
    AgentRuntime,
    AgentScheduler,
    CoderAgent,
    CoordinatorAgent,
    ExecutorAgent,
    MemoryAgent,
    MetricsCollector,
    PlannerAgent,
    ResearchAgent,
    ReviewerAgent,
    Tracer,
)
from app.agents.context import AgentExecutionContext
from app.agents.lifecycle import AgentLifecycle, AgentState
from app.agents.policies import get_policy, list_policies


@pytest.fixture
def runtime():
    rt = AgentRuntime(max_concurrency=5)
    for agent in [
        PlannerAgent(),
        ResearchAgent(),
        CoderAgent(),
        ReviewerAgent(),
        MemoryAgent(),
        ExecutorAgent(),
        CoordinatorAgent(),
    ]:
        rt.register(agent)
    return rt


@pytest.fixture
def factory():
    rt = AgentRuntime()
    return AgentFactory(runtime=rt)


class TestRegistrationIntegration:
    def test_register_all_builtins(self, runtime):
        agents = runtime.list_agents()
        ids = [a.agent_id for a in agents]
        assert "planner" in ids
        assert "researcher" in ids
        assert "coder" in ids
        assert "reviewer" in ids
        assert "memory" in ids
        assert "executor" in ids
        assert "coordinator" in ids

    def test_capabilities_registered(self, runtime):
        for aid in ["planner", "researcher", "coder", "reviewer", "memory", "executor"]:
            cap = runtime.registry.get_capability(aid)
            assert cap is not None

    def test_lifecycles_ready(self, runtime):
        for aid in runtime.registry.list_agent_ids():
            lc = runtime.registry.get_lifecycle(aid)
            assert lc is not None
            assert lc.state == AgentState.READY


class TestDispatchIntegration:
    @pytest.mark.asyncio
    async def test_dispatch_to_each_agent(self, runtime):
        for aid in ["planner", "researcher", "coder", "reviewer", "memory", "executor"]:
            result = await runtime.dispatch(aid, f"test task for {aid}", {"goal": "test"})
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_dispatch_with_context(self, runtime):
        result = await runtime.dispatch(
            "planner", "Plan feature", {"goal": "Feature X", "task_id": "t-1"}
        )
        assert result["status"] == "completed"
        assert result["agent_id"] == "planner"

    @pytest.mark.asyncio
    async def test_delegate_chain(self, runtime):
        r1 = await runtime.delegate("planner", "researcher", "Research")
        assert r1["status"] == "completed"

        r2 = await runtime.delegate("researcher", "coder", "Code")
        assert r2["status"] == "completed"

        r3 = await runtime.delegate("coder", "reviewer", "Review")
        assert r3["status"] == "completed"

    @pytest.mark.asyncio
    async def test_dispatch_not_found(self, runtime):
        result = await runtime.dispatch("nonexistent", "task")
        assert result["status"] == "error"


class TestCoordinationIntegration:
    @pytest.mark.asyncio
    async def test_sequential_pipeline(self, runtime):
        result = await runtime.coordinate(
            steps=[
                {"agent": "planner", "task": "Plan"},
                {"agent": "researcher", "task": "Research"},
                {"agent": "coder", "task": "Code"},
            ],
            pattern="sequential",
        )
        assert result["status"] == "completed"
        assert len(result["steps"]) == 3

    @pytest.mark.asyncio
    async def test_parallel_execution(self, runtime):
        result = await runtime.coordinate(
            steps=[
                {"agent": "researcher", "task": "Research A"},
                {"agent": "coder", "task": "Code B"},
            ],
            pattern="parallel",
        )
        assert result["status"] == "completed"
        assert len(result["steps"]) == 2

    @pytest.mark.asyncio
    async def test_full_pipeline_plan_research_code_review(self, runtime):
        result = await runtime.coordinate(
            steps=[
                {"agent": "planner", "task": "Plan auth module"},
                {"agent": "researcher", "task": "Research auth patterns"},
                {"agent": "coder", "task": "Implement auth"},
                {"agent": "reviewer", "task": "Review auth code"},
            ],
            pattern="sequential",
        )
        assert result["status"] == "completed"


class TestMetricsIntegration:
    @pytest.mark.asyncio
    async def test_metrics_collected(self, runtime):
        await runtime.dispatch("planner", "Task A")
        await runtime.dispatch("coder", "Task B")
        await runtime.delegate("planner", "reviewer", "Review")

        snap = runtime.metrics.snapshot()
        assert snap["counters"]["dispatch.total"] == 3
        assert snap["counters"]["dispatch.planner"] >= 1
        assert "derived" in snap

    @pytest.mark.asyncio
    async def test_tracing_collected(self, runtime):
        await runtime.dispatch("planner", "Task A", {"task_id": "t1"})
        traces = runtime.tracer.to_dict()
        assert len(traces) >= 1

    def test_metrics_clear(self, runtime):
        runtime.metrics.increment("test", 5)
        runtime.metrics.clear()
        assert runtime.metrics.snapshot()["counters"] == {}


class TestSchedulerIntegration:
    def test_scheduler_queue_priority(self, runtime):
        sched = runtime.scheduler
        sched.enqueue("t1", "planner", "high", priority=1)
        sched.enqueue("t2", "executor", "low", priority=10)
        first = sched.dequeue()
        assert first.task_id == "t1"

    def test_scheduler_run_complete(self, runtime):
        sched = runtime.scheduler
        entry = sched.enqueue("t1", "planner", "task")
        sched.start_running(entry)
        assert sched.running_count == 1
        sched.complete("t1")
        assert sched.running_count == 0


class TestDispatcherIntegration:
    def test_dispatcher_finds_best_agent(self, runtime):
        dispatcher = runtime.dispatcher
        ctx = AgentExecutionContext(
            goal="plan something", metadata={"intent": "planning"}
        )
        result = dispatcher.dispatch(ctx)
        assert result is not None

    def test_dispatcher_releases_workload(self, runtime):
        dispatcher = runtime.dispatcher
        ctx = AgentExecutionContext(goal="task")
        dispatcher.dispatch(ctx)
        dispatcher.release("planner")
        assert dispatcher.get_workload("planner") == 0


class TestFactoryIntegration:
    @pytest.mark.asyncio
    async def test_factory_registers_builtins(self, factory):
        agents = factory.register_all_builtins()
        assert len(agents) == 6
        runtime = factory.runtime
        assert runtime.get_agent("planner") is not None

    def test_factory_create_custom(self, factory):
        from app.agents.base import AgentDefinition, BaseAgent

        class CustomAgent(BaseAgent):
            def __init__(self):
                super().__init__("custom")

            @property
            def definition(self):
                return AgentDefinition(agent_id="custom", name="Custom", role="custom")

            async def execute(self, task, context):
                return {"status": "completed"}

        agent = factory.create_and_register(
            CustomAgent,
            AgentCapability(supported_intents=["custom"], priority=1),
        )
        assert factory.runtime.get_agent("custom") is agent


class TestLifecycleIntegration:
    def test_full_lifecycle(self, runtime):
        lc = runtime.registry.get_lifecycle("planner")
        assert lc is not None
        assert lc.state == AgentState.READY
        lc.start_running()
        assert lc.state == AgentState.RUNNING
        lc.complete()
        assert lc.state == AgentState.COMPLETED
        lc.reset_to_ready()
        assert lc.state == AgentState.READY

    def test_agent_health(self, runtime):
        h = runtime.registry.get_lifecycle("planner")
        assert h is not None

    @pytest.mark.asyncio
    async def test_shutdown(self, runtime):
        await runtime.shutdown()


class TestPoliciesIntegration:
    def test_all_policies_available(self):
        policies = list_policies()
        assert len(policies) == 7
        for name in policies:
            p = get_policy(name)
            assert p.name == name

    def test_policy_properties(self):
        p = get_policy("immediate")
        assert p.can_run_concurrently()
        assert not p.should_run_in_background()

    def test_retryable_policy_retries(self):
        p = get_policy("retryable")
        assert p.should_retry_on_failure()
        assert p.max_retries == 3
