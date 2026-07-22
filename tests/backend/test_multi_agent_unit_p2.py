"""Part 2: Tests for Registry, Dispatcher, Scheduler, Coordinator, Executor, Runtime, Factory."""

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


class TestAgentRegistry:
    def test_register_and_get(self):
        reg = AgentRegistry()
        agent = _MockAgent("m1")
        reg.register(agent)
        assert reg.get("m1") is agent

    def test_unregister(self):
        reg = AgentRegistry()
        agent = _MockAgent("m1")
        reg.register(agent)
        reg.unregister("m1")
        assert reg.get("m1") is None

    def test_list_agents(self):
        reg = AgentRegistry()
        reg.register(_MockAgent("a"))
        reg.register(_MockAgent("b"))
        assert len(reg.list_agents()) == 2

    def test_list_agent_ids(self):
        reg = AgentRegistry()
        reg.register(_MockAgent("a"))
        assert "a" in reg.list_agent_ids()

    def test_capability_extracted(self):
        reg = AgentRegistry()
        agent = _MockAgent("m1", role="planner")
        reg.register(agent)
        cap = reg.get_capability("m1")
        assert cap is not None
        assert "planner" in cap.supported_intents

    def test_lifecycle_created(self):
        reg = AgentRegistry()
        agent = _MockAgent("m1")
        reg.register(agent)
        lc = reg.get_lifecycle("m1")
        assert lc is not None
        assert lc.state == AgentState.READY

    def test_get_ready_agents(self):
        reg = AgentRegistry()
        reg.register(_MockAgent("a"))
        reg.register(_MockAgent("b"))
        ready = reg.get_ready_agents()
        assert "a" in ready
        assert "b" in ready

    def test_has_capacity(self):
        reg = AgentRegistry()
        reg.register(_MockAgent("a"))
        assert reg.has_capacity("a")

    def test_find_capable(self):
        reg = AgentRegistry()
        agent = _MockAgent("m1", role="planner")
        cap = AgentCapability(supported_intents=["planning"])
        reg.register(agent, cap)
        results = reg.find_capable(intent="planning")
        assert len(results) >= 1

    def test_register_with_custom_capability(self):
        reg = AgentRegistry()
        agent = _MockAgent("m1")
        cap = AgentCapability(priority=2, concurrency_limit=3)
        reg.register(agent, cap)
        assert reg.get_capability("m1").priority == 2

    def test_to_dict(self):
        reg = AgentRegistry()
        reg.register(_MockAgent("a"))
        d = reg.to_dict()
        assert "a" in d
        assert "capability" in d["a"]
        assert "lifecycle" in d["a"]


class TestAgentDispatcher:
    def test_score_agents(self):
        cap_reg = CapabilityRegistry()
        cap_reg.register("p", AgentCapability(supported_intents=["planning"], priority=3))
        cap_reg.register("c", AgentCapability(supported_intents=["coding"], priority=5))
        dispatcher = AgentDispatcher(cap_reg)
        ctx = AgentExecutionContext(goal="plan something")
        candidates = cap_reg.find_capable(intent="planning")
        results = dispatcher.score_agents(candidates, ctx)
        assert len(results) == 1
        assert results[0].agent_id == "p"

    def test_dispatch(self):
        cap_reg = CapabilityRegistry()
        cap_reg.register("p", AgentCapability(supported_intents=["planning"], priority=3))
        dispatcher = AgentDispatcher(cap_reg)
        ctx = AgentExecutionContext(goal="plan", metadata={"intent": "planning"})
        result = dispatcher.dispatch(ctx)
        assert result is not None
        assert result.agent_id == "p"

    def test_dispatch_no_candidates(self):
        cap_reg = CapabilityRegistry()
        dispatcher = AgentDispatcher(cap_reg)
        ctx = AgentExecutionContext(goal="nothing")
        result = dispatcher.dispatch(ctx)
        assert result is None

    def test_release(self):
        cap_reg = CapabilityRegistry()
        cap_reg.register("a", AgentCapability())
        dispatcher = AgentDispatcher(cap_reg)
        ctx = AgentExecutionContext(goal="t")
        dispatcher.dispatch(ctx)
        assert dispatcher.get_workload("a") == 1
        dispatcher.release("a")
        assert dispatcher.get_workload("a") == 0

    def test_get_all_workloads(self):
        cap_reg = CapabilityRegistry()
        cap_reg.register("a", AgentCapability())
        dispatcher = AgentDispatcher(cap_reg)
        ctx = AgentExecutionContext(goal="t")
        dispatcher.dispatch(ctx)
        wl = dispatcher.get_all_workloads()
        assert wl["a"] == 1

    def test_dispatch_result_to_dict(self):
        r = DispatchResult(agent_id="a", confidence=0.9, reason="test", score=0.8)
        d = r.to_dict()
        assert d["agent_id"] == "a"
        assert d["confidence"] == 0.9

    def test_score_with_lifecycle(self):
        cap_reg = CapabilityRegistry()
        cap_reg.register("p", AgentCapability(priority=3))
        dispatcher = AgentDispatcher(cap_reg)
        lc = AgentLifecycle("p")
        lc.register()
        lc.initialize()
        candidates = cap_reg.find_capable()
        results = dispatcher.score_agents(candidates, AgentExecutionContext(goal="t"), {"p": lc})
        assert len(results) >= 1

    def test_to_dict(self):
        cap_reg = CapabilityRegistry()
        dispatcher = AgentDispatcher(cap_reg)
        d = dispatcher.to_dict()
        assert "workloads" in d


class TestAgentScheduler:
    def test_enqueue_dequeue(self):
        sched = AgentScheduler()
        sched.enqueue("t1", "a1", "task 1", priority=5)
        assert sched.queue_size == 1
        entry = sched.dequeue()
        assert entry is not None
        assert entry.task_id == "t1"

    def test_priority_ordering(self):
        sched = AgentScheduler()
        sched.enqueue("t_high", "a1", "high", priority=1)
        sched.enqueue("t_low", "a1", "low", priority=10)
        sched.enqueue("t_mid", "a1", "mid", priority=5)
        first = sched.dequeue()
        assert first.task_id == "t_high"

    def test_can_dispatch(self):
        sched = AgentScheduler(max_concurrency=2)
        assert sched.can_dispatch("a1")

    def test_can_dispatch_reached_limit(self):
        sched = AgentScheduler(max_concurrency=1)
        sched.set_agent_limit("a1", 1)
        entry = sched.enqueue("t1", "a1", "task")
        sched.start_running(entry)
        assert not sched.can_dispatch("a1")

    def test_start_and_complete(self):
        sched = AgentScheduler()
        entry = sched.enqueue("t1", "a1", "task")
        sched.start_running(entry)
        assert sched.running_count == 1
        result = sched.complete("t1", success=True)
        assert sched.running_count == 0
        assert result is not None

    def test_cancel_queued(self):
        sched = AgentScheduler()
        sched.enqueue("t1", "a1", "task")
        assert sched.cancel("t1")
        assert sched.queue_size == 0

    def test_cancel_running(self):
        sched = AgentScheduler()
        entry = sched.enqueue("t1", "a1", "task")
        sched.start_running(entry)
        assert sched.cancel("t1")
        assert sched.running_count == 0

    def test_cancel_nonexistent(self):
        sched = AgentScheduler()
        assert not sched.cancel("nonexistent")

    def test_retry(self):
        sched = AgentScheduler()
        sched.enqueue("t1", "a1", "task", max_retries=1)
        entry = sched.dequeue()
        sched.start_running(entry)
        sched.complete("t1", success=False)
        assert sched.queue_size == 1

    def test_retry_exhausted(self):
        sched = AgentScheduler()
        sched.enqueue("t1", "a1", "task", max_retries=1)
        entry = sched.dequeue()
        sched.start_running(entry)
        sched.complete("t1", success=False)
        entry = sched.dequeue()
        sched.start_running(entry)
        sched.complete("t1", success=False)
        assert sched.queue_size == 0

    def test_get_running(self):
        sched = AgentScheduler()
        entry = sched.enqueue("t1", "a1", "task")
        sched.start_running(entry)
        running = sched.get_running()
        assert len(running) == 1

    def test_get_queue(self):
        sched = AgentScheduler()
        sched.enqueue("t1", "a1", "task")
        q = sched.get_queue()
        assert len(q) == 1

    def test_get_completed(self):
        sched = AgentScheduler()
        entry = sched.enqueue("t1", "a1", "task")
        sched.start_running(entry)
        sched.complete("t1")
        assert len(sched.get_completed()) == 1

    def test_clear(self):
        sched = AgentScheduler()
        sched.enqueue("t1", "a1", "task")
        sched.clear()
        assert sched.queue_size == 0

    def test_set_agent_limit(self):
        sched = AgentScheduler()
        sched.set_agent_limit("a1", 2)
        entry = sched.enqueue("t1", "a1", "task")
        sched.start_running(entry)
        assert sched.can_dispatch("a1")

    def test_to_dict(self):
        sched = AgentScheduler()
        d = sched.to_dict()
        assert "queue_size" in d

    def test_scheduled_task_to_dict(self):
        entry = ScheduledTask(priority=5, task_id="t1", agent_id="a1")
        d = entry.to_dict()
        assert d["task_id"] == "t1"
        assert "age_seconds" in d

    def test_complete_nonexistent(self):
        sched = AgentScheduler()
        result = sched.complete("nonexistent")
        assert result is None


async def _mock_dispatch(agent_id: str, task: str, context: dict) -> dict:
    return {"agent": agent_id, "status": "completed", "result": task}


class TestAgentCoordinator:
    @pytest.mark.asyncio
    async def test_execute_sequential(self):
        coord = AgentCoordinator(dispatch_fn=_mock_dispatch)
        steps = [
            CoordinationStep(agent_id="a1", task="task 1"),
            CoordinationStep(agent_id="a2", task="task 2"),
        ]
        result = await coord.execute_sequential(steps)
        assert result.status == "completed"
        assert len(result.steps) == 2
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_execute_sequential_failure(self):
        async def _fail_dispatch(agent_id, task, context):
            raise RuntimeError("fail")

        coord = AgentCoordinator(dispatch_fn=_fail_dispatch)
        steps = [
            CoordinationStep(agent_id="a1", task="task 1"),
            CoordinationStep(agent_id="a2", task="task 2"),
        ]
        result = await coord.execute_sequential(steps)
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_execute_parallel(self):
        coord = AgentCoordinator(dispatch_fn=_mock_dispatch)
        steps = [
            CoordinationStep(agent_id="a1", task="task 1"),
            CoordinationStep(agent_id="a2", task="task 2"),
        ]
        result = await coord.execute_parallel(steps)
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_execute_fan_out_fan_in(self):
        coord = AgentCoordinator(dispatch_fn=_mock_dispatch)
        steps = [
            CoordinationStep(agent_id="a1", task="task 1"),
            CoordinationStep(agent_id="a2", task="task 2"),
        ]
        result = await coord.execute_fan_out_fan_in(steps, "aggregator")
        assert result.status == "completed"
        assert len(result.steps) == 3

    @pytest.mark.asyncio
    async def test_execute_delegation(self):
        coord = AgentCoordinator(dispatch_fn=_mock_dispatch)
        result = await coord.execute_delegation("a1", "a2", "delegate task")
        assert result.status == "completed"
        assert result.pattern == "delegation"

    @pytest.mark.asyncio
    async def test_execute_aggregation(self):
        coord = AgentCoordinator(dispatch_fn=_mock_dispatch)
        steps = [
            CoordinationStep(agent_id="a1", task="task 1"),
            CoordinationStep(agent_id="a2", task="task 2"),
        ]
        result = await coord.execute_aggregation(steps, "aggregator")
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_execute_arbitration(self):
        coord = AgentCoordinator(dispatch_fn=_mock_dispatch)
        candidates = [
            CoordinationStep(agent_id="a1", task="option 1"),
            CoordinationStep(agent_id="a2", task="option 2"),
        ]
        result = await coord.execute_arbitration(candidates, "arbitrator")
        assert result.status == "completed"
        assert len(result.steps) == 3

    @pytest.mark.asyncio
    async def test_no_dispatch_fn(self):
        coord = AgentCoordinator()
        result = await coord.execute_sequential([CoordinationStep(agent_id="a1", task="t")])
        assert result.status == "failed"
        assert "No dispatch function" in (result.error or "")

    def test_coordination_step_to_dict(self):
        step = CoordinationStep(agent_id="a1", task="task")
        d = step.to_dict()
        assert d["agent_id"] == "a1"
        assert "duration_ms" in d

    def test_coordinator_result_to_dict(self):
        r = CoordinatorResult(pattern="sequential")
        d = r.to_dict()
        assert d["pattern"] == "sequential"

    def test_to_dict(self):
        coord = AgentCoordinator(dispatch_fn=_mock_dispatch)
        d = coord.to_dict()
        assert d["has_dispatch_fn"] is True


class TestAgentExecutor:
    @pytest.mark.asyncio
    async def test_execute_success(self):
        agent = _MockAgent("test")
        executor = AgentExecutor()
        result = await executor.execute(agent, "do something")
        assert result.success
        assert result.status == "completed"
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_execute_failure(self):
        agent = _FailAgent()
        executor = AgentExecutor(max_retries=0)
        result = await executor.execute(agent, "fail")
        assert not result.success
        assert result.status == "failed"
        assert "intentional failure" in result.error

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        agent = _SlowAgent(delay=2.0)
        executor = AgentExecutor(default_timeout=0.1)
        result = await executor.execute(agent, "slow task")
        assert not result.success
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_with_retry(self):
        agent = _MockAgent("test")
        executor = AgentExecutor(max_retries=1)
        result = await executor.execute(agent, "task")
        assert result.success

    @pytest.mark.asyncio
    async def test_execute_with_lifecycle(self):
        agent = _MockAgent("test")
        lc = AgentLifecycle("test")
        lc.register()
        lc.initialize()
        executor = AgentExecutor()
        result = await executor.execute(agent, "task", lifecycle=lc)
        assert result.success
        assert lc.state == AgentState.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_lifecycle_on_failure(self):
        agent = _FailAgent()
        lc = AgentLifecycle("fail")
        lc.register()
        lc.initialize()
        executor = AgentExecutor(max_retries=0)
        result = await executor.execute(agent, "fail", lifecycle=lc)
        assert not result.success
        assert lc.state == AgentState.FAILED

    def test_execution_result_to_dict(self):
        r = ExecutionResult(agent_id="a", task_id="t", success=True, result={"k": "v"})
        d = r.to_dict()
        assert d["agent_id"] == "a"
        assert d["status"] == "completed"

    def test_executor_to_dict(self):
        e = AgentExecutor(max_retries=3, default_timeout=60)
        d = e.to_dict()
        assert d["max_retries"] == 3


class TestAgentRuntime:
    @pytest.mark.asyncio
    async def test_register_and_dispatch(self):
        runtime = AgentRuntime()
        agent = _MockAgent("test")
        runtime.register(agent)
        result = await runtime.dispatch("test", "do something")
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_dispatch_not_found(self):
        runtime = AgentRuntime()
        result = await runtime.dispatch("unknown", "task")
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_delegate(self):
        runtime = AgentRuntime()
        a1 = _MockAgent("a1")
        a2 = _MockAgent("a2")
        runtime.register(a1)
        runtime.register(a2)
        result = await runtime.delegate("a1", "a2", "delegated")
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_coordinate_sequential(self):
        runtime = AgentRuntime()
        runtime.register(_MockAgent("a1"))
        runtime.register(_MockAgent("a2"))
        result = await runtime.coordinate(
            steps=[{"agent": "a1", "task": "t1"}, {"agent": "a2", "task": "t2"}],
            pattern="sequential",
        )
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_coordinate_parallel(self):
        runtime = AgentRuntime()
        runtime.register(_MockAgent("a1"))
        runtime.register(_MockAgent("a2"))
        result = await runtime.coordinate(
            steps=[{"agent": "a1", "task": "t1"}, {"agent": "a2", "task": "t2"}],
            pattern="parallel",
        )
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        runtime = AgentRuntime()
        runtime.register(_MockAgent("a1"))
        await runtime.shutdown()

    @pytest.mark.asyncio
    async def test_health(self):
        runtime = AgentRuntime()
        runtime.register(_MockAgent("a1"))
        h = await runtime.health()
        assert "a1" in h
        assert h["a1"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_cancel(self):
        runtime = AgentRuntime()
        result = await runtime.cancel("nonexistent")
        assert result is False

    def test_unregister(self):
        runtime = AgentRuntime()
        runtime.register(_MockAgent("a1"))
        runtime.unregister("a1")
        assert runtime.get_agent("a1") is None

    def test_list_agents(self):
        runtime = AgentRuntime()
        runtime.register(_MockAgent("a1"))
        assert len(runtime.list_agents()) == 1

    def test_to_dict(self):
        runtime = AgentRuntime()
        d = runtime.to_dict()
        assert "agents" in d
        assert "metrics" in d


class TestAgentFactory:
    def test_register_all_builtins(self):
        runtime = AgentRuntime()
        factory = AgentFactory(runtime=runtime)
        agents = factory.register_all_builtins()
        assert len(agents) == 6
        ids = [a.agent_id for a in agents]
        assert "planner" in ids
        assert "researcher" in ids
        assert "coder" in ids
        assert "reviewer" in ids
        assert "memory" in ids
        assert "executor" in ids

    def test_create_and_register(self):
        runtime = AgentRuntime()
        factory = AgentFactory(runtime=runtime)
        agent = factory.create_and_register(_MockAgent)
        assert agent.agent_id == "mock"
        assert runtime.get_agent("mock") is agent

    def test_to_dict(self):
        runtime = AgentRuntime()
        factory = AgentFactory(runtime=runtime)
        d = factory.to_dict()
        assert "templates" in d
