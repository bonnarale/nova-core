"""Comprehensive tests for the Multi-Agent Runtime (Chapter 14)."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import AgentDefinition, BaseAgent
from app.agents.capabilities import AgentCapability, CapabilityRegistry
from app.agents.context import AgentExecutionContext
from app.agents.coordinator import (
    AgentCoordinator,
    CoordinationPattern,
    CoordinationStep,
    CoordinatorResult,
)
from app.agents.dispatcher import AgentDispatcher, DispatchResult
from app.agents.executor import AgentExecutor, ExecutionResult
from app.agents.factory import AgentFactory
from app.agents.lifecycle import AgentLifecycle, AgentState
from app.agents.metrics import MetricsCollector
from app.agents.policies import (
    BackgroundPolicy,
    ExclusivePolicy,
    get_policy,
    IdempotentPolicy,
    ImmediatePolicy,
    list_policies,
    ParallelPolicy,
    PolicyType,
    RetryablePolicy,
    SequentialPolicy,
)
from app.agents.registry import AgentRegistry
from app.agents.runtime import AgentRuntime
from app.agents.scheduler import AgentScheduler, ScheduledTask


class _MockAgent(BaseAgent):
    def __init__(self, agent_id: str = "mock", role: str = "tester") -> None:
        super().__init__(agent_id)
        self._role = role
        self._execute_fn = AsyncMock(return_value={"status": "completed", "agent": agent_id})

    @property
    def definition(self) -> AgentDefinition:
        return AgentDefinition(
            agent_id=self.agent_id,
            name=self.agent_id.title(),
            role=self._role,
            allowed_tools=["test_tool"],
        )

    async def execute(self, task: str, context: dict) -> dict:
        return await self._execute_fn(task, context)

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health(self) -> dict:
        return {"agent_id": self.agent_id, "status": "healthy"}


class _FailAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("fail_agent")

    @property
    def definition(self) -> AgentDefinition:
        return AgentDefinition(agent_id="fail_agent", name="Fail", role="fail")

    async def execute(self, task: str, context: dict) -> dict:
        raise RuntimeError("intentional failure")

    async def health(self) -> dict:
        return {"agent_id": "fail_agent", "status": "unhealthy"}


class _SlowAgent(BaseAgent):
    def __init__(self, delay: float = 0.5) -> None:
        super().__init__("slow_agent")
        self._delay = delay

    @property
    def definition(self) -> AgentDefinition:
        return AgentDefinition(agent_id="slow_agent", name="Slow", role="slow")

    async def execute(self, task: str, context: dict) -> dict:
        await asyncio.sleep(self._delay)
        return {"status": "completed"}


class TestAgentExecutionContext:
    def test_from_dict_basic(self):
        ctx = AgentExecutionContext.from_dict({"task_id": "t1", "goal": "do something"})
        assert ctx.task_id == "t1"
        assert ctx.goal == "do something"

    def test_from_dict_ignores_unknown_keys(self):
        ctx = AgentExecutionContext.from_dict({"task_id": "t1", "unknown_key": "val"})
        assert ctx.task_id == "t1"

    def test_from_dict_with_overrides(self):
        ctx = AgentExecutionContext.from_dict({"task_id": "t1"}, task_id="t2")
        assert ctx.task_id == "t2"

    def test_cancel(self):
        ctx = AgentExecutionContext()
        assert not ctx.is_cancelled
        ctx.cancel("reason")
        assert ctx.is_cancelled
        assert ctx.cancel_reason == "reason"

    def test_elapsed(self):
        ctx = AgentExecutionContext()
        assert ctx.elapsed >= 0

    def test_is_timed_out(self):
        ctx = AgentExecutionContext(timeout_seconds=0.0)
        time.sleep(0.01)
        assert ctx.is_timed_out

    def test_is_not_timed_out_when_no_timeout(self):
        ctx = AgentExecutionContext()
        assert not ctx.is_timed_out

    def test_with_agent(self):
        ctx = AgentExecutionContext(task_id="t1", assigned_agent="a1")
        new_ctx = ctx.with_agent("a2")
        assert new_ctx.task_id == "t1"
        assert new_ctx.assigned_agent == "a2"
        assert new_ctx.delegated_from == "a1"

    def test_child(self):
        ctx = AgentExecutionContext(task_id="t1", goal="goal", assigned_agent="a1")
        child = ctx.child("child_1")
        assert child.task_id == "child_1"
        assert child.goal == "goal"
        assert child.delegated_from == "a1"

    def test_to_dict(self):
        ctx = AgentExecutionContext(task_id="t1", goal="g")
        d = ctx.to_dict()
        assert d["task_id"] == "t1"
        assert "elapsed" in d
        assert "is_cancelled" in d


class TestAgentCapability:
    def test_matches_intent(self):
        cap = AgentCapability(supported_intents=["planning", "decomposition"])
        assert cap.matches_intent("planning")
        assert cap.matches_intent("Planning")
        assert not cap.matches_intent("coding")

    def test_matches_task_type(self):
        cap = AgentCapability(supported_task_types=["code", "implement"])
        assert cap.matches_task_type("code")
        assert not cap.matches_task_type("research")

    def test_matches_tool(self):
        cap = AgentCapability(supported_tools=["file_read", "file_write"])
        assert cap.matches_tool("file_read")
        assert not cap.matches_tool("web_search")

    def test_has_tag(self):
        cap = AgentCapability(tags=["python", "async"])
        assert cap.has_tag("python")
        assert not cap.has_tag("rust")

    def test_to_dict(self):
        cap = AgentCapability(priority=3)
        d = cap.to_dict()
        assert d["priority"] == 3


class TestCapabilityRegistry:
    def test_register_and_get(self):
        reg = CapabilityRegistry()
        cap = AgentCapability(supported_intents=["planning"])
        reg.register("planner", cap)
        assert reg.get("planner") is cap

    def test_unregister(self):
        reg = CapabilityRegistry()
        reg.register("a", AgentCapability())
        reg.unregister("a")
        assert reg.get("a") is None

    def test_find_by_intent(self):
        reg = CapabilityRegistry()
        reg.register("planner", AgentCapability(supported_intents=["planning"]))
        reg.register("coder", AgentCapability(supported_intents=["coding"]))
        results = reg.find_by_intent("planning")
        assert len(results) == 1
        assert results[0][0] == "planner"

    def test_find_by_task_type(self):
        reg = CapabilityRegistry()
        reg.register("a", AgentCapability(supported_task_types=["code"]))
        assert len(reg.find_by_task_type("code")) == 1

    def test_find_by_tool(self):
        reg = CapabilityRegistry()
        reg.register("a", AgentCapability(supported_tools=["file_read"]))
        assert len(reg.find_by_tool("file_read")) == 1

    def test_find_by_tag(self):
        reg = CapabilityRegistry()
        reg.register("a", AgentCapability(tags=["python"]))
        assert len(reg.find_by_tag("python")) == 1

    def test_find_by_policy(self):
        reg = CapabilityRegistry()
        reg.register("a", AgentCapability(execution_policy="immediate"))
        assert len(reg.find_by_policy("immediate")) == 1

    def test_find_capable_combined(self):
        reg = CapabilityRegistry()
        reg.register("p", AgentCapability(supported_intents=["planning"], priority=3))
        reg.register("c", AgentCapability(supported_intents=["coding"], priority=5))
        results = reg.find_capable(intent="planning")
        assert len(results) == 1

    def test_list_all(self):
        reg = CapabilityRegistry()
        reg.register("a", AgentCapability())
        reg.register("b", AgentCapability())
        assert len(reg.list_all()) == 2

    def test_to_dict(self):
        reg = CapabilityRegistry()
        reg.register("a", AgentCapability(priority=1))
        d = reg.to_dict()
        assert "a" in d


class TestPolicies:
    def test_immediate_policy(self):
        p = ImmediatePolicy()
        assert p.name == "immediate"
        assert p.can_run_concurrently()
        assert not p.should_retry_on_failure()
        assert not p.is_idempotent()
        assert not p.should_run_in_background()

    def test_background_policy(self):
        p = BackgroundPolicy()
        assert p.name == "background"
        assert p.can_run_concurrently()
        assert p.should_retry_on_failure()
        assert p.should_run_in_background()

    def test_exclusive_policy(self):
        p = ExclusivePolicy()
        assert p.name == "exclusive"
        assert not p.can_run_concurrently()

    def test_parallel_policy(self):
        p = ParallelPolicy()
        assert p.name == "parallel"
        assert p.can_run_concurrently()

    def test_sequential_policy(self):
        p = SequentialPolicy()
        assert p.name == "sequential"
        assert not p.can_run_concurrently()

    def test_retryable_policy(self):
        p = RetryablePolicy(max_retries=5)
        assert p.name == "retryable"
        assert p.should_retry_on_failure()
        assert p.is_idempotent()
        assert p.max_retries == 5

    def test_idempotent_policy(self):
        p = IdempotentPolicy()
        assert p.name == "idempotent"
        assert p.is_idempotent()

    def test_get_policy(self):
        p = get_policy("immediate")
        assert isinstance(p, ImmediatePolicy)

    def test_get_policy_unknown(self):
        with pytest.raises(ValueError, match="Unknown execution policy"):
            get_policy("nonexistent")

    def test_list_policies(self):
        policies = list_policies()
        assert "immediate" in policies
        assert "background" in policies
        assert len(policies) == 7


class TestAgentLifecycle:
    def test_initial_state(self):
        lc = AgentLifecycle("a1")
        assert lc.state == AgentState.REGISTERED

    def test_register_then_initialize(self):
        lc = AgentLifecycle("a1")
        assert lc.register()
        assert lc.state == AgentState.INITIALIZING
        assert lc.initialize()
        assert lc.state == AgentState.READY

    def test_running_cycle(self):
        lc = AgentLifecycle("a1")
        lc.register()
        lc.initialize()
        assert lc.start_running()
        assert lc.state == AgentState.RUNNING
        assert lc.complete()
        assert lc.state == AgentState.COMPLETED

    def test_wait_and_resume(self):
        lc = AgentLifecycle("a1")
        lc.register()
        lc.initialize()
        lc.start_running()
        assert lc.wait("waiting for data")
        assert lc.state == AgentState.WAITING
        assert lc.unblock()
        assert lc.state == AgentState.RUNNING

    def test_block_and_unblock(self):
        lc = AgentLifecycle("a1")
        lc.register()
        lc.initialize()
        lc.start_running()
        assert lc.block("blocked on dependency")
        assert lc.state == AgentState.BLOCKED
        assert lc.unblock()
        assert lc.state == AgentState.RUNNING

    def test_fail(self):
        lc = AgentLifecycle("a1")
        lc.register()
        lc.initialize()
        lc.start_running()
        assert lc.fail("error")
        assert lc.state == AgentState.FAILED

    def test_cancel(self):
        lc = AgentLifecycle("a1")
        lc.register()
        lc.initialize()
        lc.start_running()
        assert lc.cancel("user cancelled")
        assert lc.state == AgentState.CANCELLED

    def test_shutdown(self):
        lc = AgentLifecycle("a1")
        lc.register()
        lc.initialize()
        assert lc.shutdown()
        assert lc.state == AgentState.SHUTDOWN

    def test_invalid_transition(self):
        lc = AgentLifecycle("a1")
        assert not lc.transition_to(AgentState.RUNNING)

    def test_reset_to_ready(self):
        lc = AgentLifecycle("a1")
        lc.register()
        lc.initialize()
        lc.start_running()
        lc.complete()
        assert lc.reset_to_ready()
        assert lc.state == AgentState.READY

    def test_can_transition_to(self):
        lc = AgentLifecycle("a1")
        assert lc.can_transition_to(AgentState.INITIALIZING)
        assert not lc.can_transition_to(AgentState.RUNNING)

    def test_history(self):
        lc = AgentLifecycle("a1")
        lc.register()
        lc.initialize()
        assert len(lc.history) == 2

    def test_transitions_count(self):
        lc = AgentLifecycle("a1")
        lc.register()
        lc.initialize()
        assert lc.transitions_count == 2

    def test_to_dict(self):
        lc = AgentLifecycle("a1")
        d = lc.to_dict()
        assert d["agent_id"] == "a1"
        assert d["state"] == "REGISTERED"
