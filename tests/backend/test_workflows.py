"""Tests for Workflow Engine v1 — models, state machine, executor, conditions,
scheduler, builder, registry, events, history, engine, and cognitive integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.cognitive.context import CognitiveContext, IntentType
from app.cognitive.decision import (
    CognitiveDecision,
    DecisionAction,
    WorkflowHandler,
    default_handler_registry,
)
from app.cognitive.engine import CognitiveEngine
from app.workflows.base import ConditionEvaluator, RollbackHandler, StepHandler, WorkflowExecutor
from app.workflows.builder import WorkflowBuilder
from app.workflows.conditions import DefaultConditionEvaluator
from app.workflows.engine import WorkflowEngine
from app.workflows.events import WorkflowEventBus, WorkflowEventType
from app.workflows.executor import SequentialExecutor
from app.workflows.history import WorkflowHistory
from app.workflows.models import (
    Condition,
    ConditionStep,
    LoopStep,
    ParallelBranch,
    ParallelStep,
    RetryPolicy,
    StepStatus,
    StepType,
    TimeoutPolicy,
    WorkflowDefinition,
    WorkflowEvent,
    WorkflowExecution,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepExecution,
)
from app.workflows.state_machine import WorkflowStateMachine
from app.workflows.registry import StepHandlerRegistry, WorkflowRegistry
from app.workflows.repository import WorkflowRepository
from app.workflows.scheduler import RetryManager, TimeoutManager
from app.workflows.state_machine import WorkflowStateMachine


# ======================================================================
# Domain model tests
# ======================================================================

class TestWorkflowStep:
    def test_default_construction(self):
        step = WorkflowStep(id="s1", name="test step")
        assert step.id == "s1"
        assert step.name == "test step"
        assert step.step_type == StepType.TASK
        assert step.depends_on == []
        assert step.retry_policy is None

    def test_to_dict(self):
        step = WorkflowStep(id="s1", name="Test", handler="echo")
        d = step.to_dict()
        assert d["id"] == "s1"
        assert d["handler"] == "echo"


class TestWorkflowDefinition:
    def test_default_construction(self):
        wf = WorkflowDefinition(name="test")
        assert wf.name == "test"
        assert wf.steps == []
        assert wf.version == "1.0.0"

    def test_to_dict(self):
        wf = WorkflowDefinition(
            id="wf1",
            name="My Workflow",
            steps=[WorkflowStep(id="s1", name="Step 1")],
        )
        d = wf.to_dict()
        assert d["name"] == "My Workflow"
        assert len(d["steps"]) == 1


class TestWorkflowExecution:
    def test_default_construction(self):
        exec_ = WorkflowExecution(id="exec1", workflow_id="wf1", workflow_name="test")
        assert exec_.status == WorkflowStatus.PENDING
        assert exec_.step_executions == []

    def test_to_dict(self):
        exec_ = WorkflowExecution(
            id="exec1",
            workflow_id="wf1",
            workflow_name="test",
            status=WorkflowStatus.COMPLETED,
        )
        d = exec_.to_dict()
        assert d["status"] == "COMPLETED"
        assert d["step_count"] == 0


class TestWorkflowStepExecution:
    def test_defaults(self):
        se = WorkflowStepExecution(step_id="s1")
        assert se.status == StepStatus.PENDING
        assert se.retry_count == 0

    def test_to_dict(self):
        se = WorkflowStepExecution(step_id="s1", status=StepStatus.COMPLETED)
        d = se.to_dict()
        assert d["status"] == "COMPLETED"


class TestWorkflowEvent:
    def test_defaults(self):
        ev = WorkflowEvent(execution_id="exec1", event_type=WorkflowEventType.CREATED)
        assert ev.event_type == WorkflowEventType.CREATED

    def test_to_dict(self):
        ev = WorkflowEvent(id="e1", execution_id="exec1", event_type=WorkflowEventType.STARTED)
        d = ev.to_dict()
        assert d["event_type"] == "STARTED"


class TestRetryPolicy:
    def test_defaults(self):
        rp = RetryPolicy()
        assert rp.max_retries == 3
        assert rp.delay_seconds == 1.0


class TestTimeoutPolicy:
    def test_defaults(self):
        tp = TimeoutPolicy()
        assert tp.step_timeout_seconds == 300.0


# ======================================================================
# State machine tests
# ======================================================================

class TestWorkflowStateMachine:
    def test_valid_workflow_transitions(self):
        assert WorkflowStateMachine.can_transition_workflow(
            WorkflowStatus.PENDING, WorkflowStatus.RUNNING
        )
        assert WorkflowStateMachine.can_transition_workflow(
            WorkflowStatus.RUNNING, WorkflowStatus.PAUSED
        )
        assert WorkflowStateMachine.can_transition_workflow(
            WorkflowStatus.RUNNING, WorkflowStatus.COMPLETED
        )
        assert WorkflowStateMachine.can_transition_workflow(
            WorkflowStatus.RUNNING, WorkflowStatus.FAILED
        )
        assert WorkflowStateMachine.can_transition_workflow(
            WorkflowStatus.PAUSED, WorkflowStatus.RUNNING
        )
        assert WorkflowStateMachine.can_transition_workflow(
            WorkflowStatus.FAILED, WorkflowStatus.RUNNING
        )

    def test_invalid_workflow_transitions(self):
        assert not WorkflowStateMachine.can_transition_workflow(
            WorkflowStatus.PENDING, WorkflowStatus.COMPLETED
        )
        assert not WorkflowStateMachine.can_transition_workflow(
            WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING
        )
        assert not WorkflowStateMachine.can_transition_workflow(
            WorkflowStatus.CANCELLED, WorkflowStatus.RUNNING
        )

    def test_valid_step_transitions(self):
        assert WorkflowStateMachine.can_transition_step(
            StepStatus.PENDING, StepStatus.RUNNING
        )
        assert WorkflowStateMachine.can_transition_step(
            StepStatus.RUNNING, StepStatus.COMPLETED
        )
        assert WorkflowStateMachine.can_transition_step(
            StepStatus.FAILED, StepStatus.RETRYING
        )

    def test_invalid_step_transitions(self):
        assert not WorkflowStateMachine.can_transition_step(
            StepStatus.PENDING, StepStatus.COMPLETED
        )
        assert not WorkflowStateMachine.can_transition_step(
            StepStatus.COMPLETED, StepStatus.RUNNING
        )

    def test_assert_valid_transition(self):
        WorkflowStateMachine.assert_can_transition_workflow(
            WorkflowStatus.PENDING, WorkflowStatus.RUNNING
        )

    def test_assert_invalid_transition_raises(self):
        with pytest.raises(ValueError):
            WorkflowStateMachine.assert_can_transition_workflow(
                WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING
            )

    def test_list_workflow_transitions(self):
        transitions = WorkflowStateMachine.list_workflow_transitions(
            WorkflowStatus.PENDING
        )
        assert "RUNNING" in transitions
        assert "CANCELLED" in transitions

    def test_list_step_transitions(self):
        transitions = WorkflowStateMachine.list_step_transitions(StepStatus.PENDING)
        assert "RUNNING" in transitions
        assert "SKIPPED" in transitions


# ======================================================================
# ABC verification
# ======================================================================

class TestABCs:
    def test_workflow_executor_cannot_instantiate(self):
        with pytest.raises(TypeError):
            WorkflowExecutor()

    def test_step_handler_cannot_instantiate(self):
        with pytest.raises(TypeError):
            StepHandler()

    def test_condition_evaluator_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ConditionEvaluator()

    def test_rollback_handler_cannot_instantiate(self):
        with pytest.raises(TypeError):
            RollbackHandler()


# ======================================================================
# Condition evaluator tests
# ======================================================================

class TestDefaultConditionEvaluator:
    @pytest.mark.asyncio
    async def test_eq(self):
        evaluator = DefaultConditionEvaluator()
        assert await evaluator.evaluate(
            {"field": "value", "operator": "eq", "value": 42},
            {"value": 42},
        )
        assert not await evaluator.evaluate(
            {"field": "value", "operator": "eq", "value": 42},
            {"value": 43},
        )

    @pytest.mark.asyncio
    async def test_gt(self):
        evaluator = DefaultConditionEvaluator()
        assert await evaluator.evaluate(
            {"field": "count", "operator": "gt", "value": 5},
            {"count": 10},
        )
        assert not await evaluator.evaluate(
            {"field": "count", "operator": "gt", "value": 5},
            {"count": 3},
        )

    @pytest.mark.asyncio
    async def test_in(self):
        evaluator = DefaultConditionEvaluator()
        assert await evaluator.evaluate(
            {"field": "tag", "operator": "in", "value": ["a", "b"]},
            {"tag": "a"},
        )

    @pytest.mark.asyncio
    async def test_exists(self):
        evaluator = DefaultConditionEvaluator()
        assert await evaluator.evaluate(
            {"field": "name", "operator": "exists"},
            {"name": "hello"},
        )
        assert not await evaluator.evaluate(
            {"field": "missing", "operator": "exists"},
            {"name": "hello"},
        )

    @pytest.mark.asyncio
    async def test_truthy(self):
        evaluator = DefaultConditionEvaluator()
        assert await evaluator.evaluate(
            {"field": "flag", "operator": "truthy"},
            {"flag": True},
        )
        assert not await evaluator.evaluate(
            {"field": "flag", "operator": "truthy"},
            {"flag": False},
        )

    @pytest.mark.asyncio
    async def test_unknown_operator_raises(self):
        evaluator = DefaultConditionEvaluator()
        with pytest.raises(ValueError):
            await evaluator.evaluate(
                {"field": "x", "operator": "unknown_op", "value": 1},
                {"x": 1},
            )

    @pytest.mark.asyncio
    async def test_nested_field(self):
        evaluator = DefaultConditionEvaluator()
        context = {"user": {"name": "Alice", "age": 30}}
        assert await evaluator.evaluate(
            {"field": "user.name", "operator": "eq", "value": "Alice"},
            context,
        )
        assert await evaluator.evaluate(
            {"field": "user.age", "operator": "gte", "value": 18},
            context,
        )

    @pytest.mark.asyncio
    async def test_contains(self):
        evaluator = DefaultConditionEvaluator()
        assert await evaluator.evaluate(
            {"field": "text", "operator": "contains", "value": "world"},
            {"text": "hello world"},
        )


# ======================================================================
# WorkflowBuilder tests
# ======================================================================

class TestWorkflowBuilder:
    def test_build_empty(self):
        builder = WorkflowBuilder("test")
        wf = builder.build()
        assert wf.name == "test"
        assert wf.id is not None

    def test_with_description(self):
        wf = WorkflowBuilder("test").with_description("desc").build()
        assert wf.description == "desc"

    def test_with_version(self):
        wf = WorkflowBuilder("test").with_version("2.0.0").build()
        assert wf.version == "2.0.0"

    def test_with_tags(self):
        wf = WorkflowBuilder("test").with_tags("urgent", "critical").build()
        assert "urgent" in wf.tags
        assert "critical" in wf.tags

    def test_add_task_step(self):
        wf = (
            WorkflowBuilder("test")
            .task_step("s1", "Step 1", "echo", {"msg": "hello"})
            .task_step("s2", "Step 2", "echo", depends_on=["s1"])
            .build()
        )
        assert len(wf.steps) == 2
        assert wf.steps[0].id == "s1"
        assert wf.steps[0].handler == "echo"
        assert wf.steps[1].depends_on == ["s1"]

    def test_condition_step(self):
        wf = (
            WorkflowBuilder("test")
            .condition_step(
                "c1", "Check",
                [Condition(field="value", operator="eq", value=1)],
            )
            .build()
        )
        assert len(wf.steps) == 1
        assert wf.steps[0].step_type == StepType.CONDITION

    def test_parallel_step(self):
        branch = ParallelBranch(id="b1", steps=[WorkflowStep(id="p1", name="Parallel Task")])
        wf = (
            WorkflowBuilder("test")
            .parallel_step("p", "Parallel", [branch])
            .build()
        )
        assert len(wf.steps) == 1
        assert wf.steps[0].step_type == StepType.PARALLEL

    def test_loop_step(self):
        body = [WorkflowStep(id="l1", name="Loop Body")]
        wf = (
            WorkflowBuilder("test")
            .loop_step("loop", "Loop", "items", body, max_iterations=5)
            .build()
        )
        assert len(wf.steps) == 1
        assert wf.steps[0].step_type == StepType.LOOP

    def test_fluent_chaining(self):
        wf = (
            WorkflowBuilder("Chain")
            .with_description("chained")
            .with_version("1.5.0")
            .with_tags("test")
            .task_step("s1", "One", "echo")
            .task_step("s2", "Two", "echo", depends_on=["s1"])
            .build()
        )
        assert wf.name == "Chain"
        assert wf.description == "chained"
        assert wf.version == "1.5.0"
        assert len(wf.steps) == 2

    def test_with_input_schema(self):
        wf = WorkflowBuilder("test").with_input_schema({"type": "object"}).build()
        assert wf.input_schema == {"type": "object"}

    def test_with_timeout(self):
        wf = WorkflowBuilder("test").with_timeout(step_timeout=60.0).build()
        assert wf.timeout_policy is not None
        assert wf.timeout_policy.step_timeout_seconds == 60.0


# ======================================================================
# Registry tests
# ======================================================================

class TestWorkflowRegistry:
    def test_register_and_get(self):
        registry = WorkflowRegistry()
        wf = WorkflowDefinition(id="wf1", name="test")
        registry.register(wf)
        assert registry.get("wf1") is wf

    def test_unregister(self):
        registry = WorkflowRegistry()
        wf = WorkflowDefinition(id="wf1", name="test")
        registry.register(wf)
        registry.unregister("wf1")
        assert registry.get("wf1") is None

    def test_list(self):
        registry = WorkflowRegistry()
        registry.register(WorkflowDefinition(id="wf1", name="a"))
        registry.register(WorkflowDefinition(id="wf2", name="b"))
        assert len(registry.list()) == 2

    def test_find_by_tag(self):
        registry = WorkflowRegistry()
        wf = WorkflowDefinition(id="wf1", name="test", tags=["urgent"])
        registry.register(wf)
        found = registry.find_by_tag("urgent")
        assert len(found) == 1
        assert found[0].id == "wf1"

    def test_definitions_property(self):
        registry = WorkflowRegistry()
        wf = WorkflowDefinition(id="wf1", name="test")
        registry.register(wf)
        assert "wf1" in registry.definitions


class TestStepHandlerRegistry:
    def test_register_and_get(self):
        registry = StepHandlerRegistry()
        handler = MagicMock(spec=StepHandler)
        handler.handler_name = "echo"
        registry.register(handler)
        assert registry.get("echo") is handler

    def test_unregister(self):
        registry = StepHandlerRegistry()
        handler = MagicMock(spec=StepHandler)
        handler.handler_name = "echo"
        registry.register(handler)
        registry.unregister("echo")
        assert registry.get("echo") is None

    def test_handlers_property(self):
        registry = StepHandlerRegistry()
        handler = MagicMock(spec=StepHandler)
        handler.handler_name = "echo"
        registry.register(handler)
        assert "echo" in registry.handlers


# ======================================================================
# EventBus tests
# ======================================================================

class TestWorkflowEventBus:
    def test_publish_event(self):
        bus = WorkflowEventBus()
        event = bus.publish(WorkflowEventType.CREATED, "exec1")
        assert event.execution_id == "exec1"
        assert event.event_type == WorkflowEventType.CREATED

    def test_publish_with_payload(self):
        bus = WorkflowEventBus()
        event = bus.publish(
            WorkflowEventType.STARTED, "exec1",
            step_id="s1", payload={"key": "val"},
        )
        assert event.step_id == "s1"
        assert event.payload == {"key": "val"}

    def test_subscribe_and_notify(self):
        bus = WorkflowEventBus()
        handler = MagicMock()
        bus.subscribe(WorkflowEventType.COMPLETED, handler)
        bus.publish(WorkflowEventType.COMPLETED, "exec1")
        handler.assert_called_once()

    def test_unsubscribe(self):
        bus = WorkflowEventBus()
        handler = MagicMock()
        bus.subscribe(WorkflowEventType.COMPLETED, handler)
        bus.unsubscribe(WorkflowEventType.COMPLETED, handler)
        bus.publish(WorkflowEventType.COMPLETED, "exec1")
        handler.assert_not_called()

    def test_get_events(self):
        bus = WorkflowEventBus()
        bus.publish(WorkflowEventType.CREATED, "exec1")
        bus.publish(WorkflowEventType.STARTED, "exec1")
        bus.publish(WorkflowEventType.CREATED, "exec2")
        assert len(bus.get_events("exec1")) == 2
        assert len(bus.get_events()) == 3

    def test_clear(self):
        bus = WorkflowEventBus()
        bus.publish(WorkflowEventType.CREATED, "exec1")
        bus.clear()
        assert len(bus.get_events()) == 0


# ======================================================================
# History tests
# ======================================================================

class TestWorkflowHistory:
    def test_record_and_get(self):
        history = WorkflowHistory()
        exec_ = WorkflowExecution(id="exec1", workflow_id="wf1", workflow_name="test")
        history.record(exec_)
        assert history.get("exec1") is exec_

    def test_list(self):
        history = WorkflowHistory()
        history.record(WorkflowExecution(id="e1", workflow_id="wf1", workflow_name="a"))
        history.record(WorkflowExecution(id="e2", workflow_id="wf1", workflow_name="b"))
        history.record(WorkflowExecution(id="e3", workflow_id="wf2", workflow_name="c"))
        assert len(history.list()) == 3
        assert len(history.list(workflow_id="wf1")) == 2
        assert len(history.list(workflow_id="wf2")) == 1

    def test_delete(self):
        history = WorkflowHistory()
        history.record(WorkflowExecution(id="e1", workflow_id="wf1", workflow_name="a"))
        assert history.delete("e1") is True
        assert history.delete("nonexistent") is False

    def test_count(self):
        history = WorkflowHistory()
        history.record(WorkflowExecution(id="e1", workflow_id="wf1", workflow_name="a"))
        history.record(WorkflowExecution(id="e2", workflow_id="wf1", workflow_name="b"))
        assert history.count() == 2
        assert history.count(workflow_id="wf1") == 2


# ======================================================================
# Scheduler tests
# ======================================================================

class TestRetryManager:
    @pytest.mark.asyncio
    async def test_execute_with_retry_succeeds_first(self):
        handler = MagicMock(spec=StepHandler)
        handler.execute = AsyncMock(
            return_value=WorkflowStepExecution(step_id="s1", status=StepStatus.COMPLETED)
        )
        mgr = RetryManager()
        step = WorkflowStep(id="s1", name="test")
        result = await mgr.execute_with_retry(handler, step, WorkflowExecution(), {})
        assert result.status == StepStatus.COMPLETED
        handler.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_with_retry_retries_on_failure(self):
        handler = MagicMock(spec=StepHandler)
        handler.execute = AsyncMock(
            side_effect=ValueError("oops")
        )
        mgr = RetryManager()
        step = WorkflowStep(id="s1", name="test", retry_policy=RetryPolicy(max_retries=2, delay_seconds=0.01))
        result = await mgr.execute_with_retry(handler, step, WorkflowExecution(), {})
        assert result.status == StepStatus.FAILED
        assert handler.execute.await_count == 3


class TestTimeoutManager:
    @pytest.mark.asyncio
    async def test_execute_within_timeout(self):
        mgr = TimeoutManager()
        async def fast():
            return "done"
        result = await mgr.execute_with_timeout(fast(), default_timeout=1.0)
        assert result == "done"

    @pytest.mark.asyncio
    async def test_execute_exceeds_timeout(self):
        mgr = TimeoutManager()
        async def slow():
            import asyncio
            await asyncio.sleep(0.5)
            return "done"
        with pytest.raises(TimeoutError):
            await mgr.execute_with_timeout(slow(), default_timeout=0.01)


# ======================================================================
# SequentialExecutor tests
# ======================================================================

class TestSequentialExecutor:
    @pytest.mark.asyncio
    async def test_execute_single_step(self):
        handler = MagicMock(spec=StepHandler)
        handler.execute = AsyncMock(
            return_value=WorkflowStepExecution(step_id="s1", status=StepStatus.COMPLETED, output={"result": "ok"})
        )
        step_handlers = {"echo": handler}
        evaluator = DefaultConditionEvaluator()
        executor = SequentialExecutor(step_handlers, evaluator)

        definition = WorkflowDefinition(
            id="wf1", name="test",
            steps=[WorkflowStep(id="s1", name="Step 1", handler="echo")],
        )
        execution = WorkflowExecution(id="exec1", workflow_id="wf1", workflow_name="test", status=WorkflowStatus.RUNNING)

        result = await executor.execute(definition, execution)
        assert len(result.step_executions) == 1
        assert result.step_executions[0].step_id == "s1"

    @pytest.mark.asyncio
    async def test_execute_multiple_steps(self):
        handler = MagicMock(spec=StepHandler)
        handler.execute = AsyncMock(
            return_value=WorkflowStepExecution(step_id="s1", status=StepStatus.COMPLETED, output={})
        )
        step_handlers = {"echo": handler}
        evaluator = DefaultConditionEvaluator()
        executor = SequentialExecutor(step_handlers, evaluator)

        definition = WorkflowDefinition(
            id="wf1", name="test",
            steps=[
                WorkflowStep(id="s1", name="Step 1", handler="echo"),
                WorkflowStep(id="s2", name="Step 2", handler="echo", depends_on=["s1"]),
            ],
        )
        execution = WorkflowExecution(id="exec1", workflow_id="wf1", workflow_name="test", status=WorkflowStatus.RUNNING)

        result = await executor.execute(definition, execution)
        assert len(result.step_executions) == 2

    @pytest.mark.asyncio
    async def test_execute_step_failure(self):
        handler = MagicMock(spec=StepHandler)
        handler.execute = AsyncMock(
            side_effect=ValueError("step failed")
        )
        step_handlers = {"echo": handler}
        evaluator = DefaultConditionEvaluator()
        executor = SequentialExecutor(step_handlers, evaluator)

        definition = WorkflowDefinition(
            id="wf1", name="test",
            steps=[WorkflowStep(id="s1", name="Step 1", handler="echo")],
        )
        execution = WorkflowExecution(id="exec1", workflow_id="wf1", workflow_name="test", status=WorkflowStatus.RUNNING)

        result = await executor.execute(definition, execution)
        assert result.step_executions[0].status == StepStatus.FAILED
        assert "step failed" in result.step_executions[0].error

    @pytest.mark.asyncio
    async def test_topological_sort(self):
        handler = MagicMock(spec=StepHandler)
        handler.execute = AsyncMock(
            return_value=WorkflowStepExecution(step_id="s1", status=StepStatus.COMPLETED, output={})
        )
        step_handlers = {"echo": handler}
        evaluator = DefaultConditionEvaluator()
        executor = SequentialExecutor(step_handlers, evaluator)

        definition = WorkflowDefinition(
            id="wf1", name="test",
            steps=[
                WorkflowStep(id="s3", name="Step 3", handler="echo", depends_on=["s1"]),
                WorkflowStep(id="s1", name="Step 1", handler="echo"),
                WorkflowStep(id="s2", name="Step 2", handler="echo", depends_on=["s1"]),
            ],
        )
        execution = WorkflowExecution(id="exec1", workflow_id="wf1", workflow_name="test", status=WorkflowStatus.RUNNING)

        result = await executor.execute(definition, execution)
        # Should be executed in order: s1, s2, s3
        step_ids = [se.step_id for se in result.step_executions]
        assert step_ids.index("s1") < step_ids.index("s2")
        assert step_ids.index("s1") < step_ids.index("s3")


# ======================================================================
# WorkflowEngine tests
# ======================================================================

class TestWorkflowEngine:
    @pytest.mark.asyncio
    async def test_register_and_list_workflows(self):
        engine = WorkflowEngine()
        wf = WorkflowDefinition(id="wf1", name="test")
        engine.register_workflow(wf)
        assert len(engine.list_workflows()) == 1
        assert engine.get_workflow("wf1") is wf

    @pytest.mark.asyncio
    async def test_create_execution(self):
        engine = WorkflowEngine()
        wf = WorkflowDefinition(id="wf1", name="test", steps=[WorkflowStep(id="s1", name="S1")])
        engine.register_workflow(wf)

        execution = await engine.create_execution(
            workflow_id="wf1", input_data={"key": "val"}, user_id="u1",
        )
        assert execution.workflow_id == "wf1"
        assert execution.status == WorkflowStatus.PENDING
        assert execution.input == {"key": "val"}
        assert execution.user_id == "u1"

    @pytest.mark.asyncio
    async def test_create_execution_unknown_workflow(self):
        engine = WorkflowEngine()
        with pytest.raises(ValueError):
            await engine.create_execution(workflow_id="nonexistent")

    @pytest.mark.asyncio
    async def test_start_execution(self):
        engine = WorkflowEngine()
        wf = WorkflowDefinition(
            id="wf1", name="test",
            steps=[WorkflowStep(id="s1", name="S1", handler="echo")],
        )
        engine.register_workflow(wf)

        execution = await engine.create_execution(workflow_id="wf1")
        result = await engine.start_execution(execution.id)
        assert result.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)

    @pytest.mark.asyncio
    async def test_pause_and_resume(self):
        engine = WorkflowEngine()
        wf = WorkflowDefinition(id="wf1", name="test")
        engine.register_workflow(wf)
        execution = await engine.create_execution(workflow_id="wf1")
        execution.status = WorkflowStatus.RUNNING
        engine._history.record(execution)

        paused = await engine.pause_execution(execution.id)
        assert paused.status == WorkflowStatus.PAUSED

        resumed = await engine.resume_execution(execution.id)
        assert resumed.status == WorkflowStatus.RUNNING

    @pytest.mark.asyncio
    async def test_cancel_execution(self):
        engine = WorkflowEngine()
        wf = WorkflowDefinition(id="wf1", name="test")
        engine.register_workflow(wf)
        execution = await engine.create_execution(workflow_id="wf1")

        cancelled = await engine.cancel_execution(execution.id)
        assert cancelled.status == WorkflowStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_rollback_execution(self):
        engine = WorkflowEngine()
        wf = WorkflowDefinition(id="wf1", name="test")
        engine.register_workflow(wf)
        execution = await engine.create_execution(workflow_id="wf1")

        # Need to have it running first to rollback
        execution.status = WorkflowStatus.RUNNING
        engine._history.record(execution)

        rolled_back = await engine.rollback_execution(execution.id)
        assert rolled_back.status in (WorkflowStatus.ROLLING_BACK, WorkflowStatus.ROLLED_BACK)

    @pytest.mark.asyncio
    async def test_get_execution(self):
        engine = WorkflowEngine()
        wf = WorkflowDefinition(id="wf1", name="test")
        engine.register_workflow(wf)
        execution = await engine.create_execution(workflow_id="wf1")
        assert engine.get_execution(execution.id) is execution

    @pytest.mark.asyncio
    async def test_list_executions(self):
        engine = WorkflowEngine()
        wf = WorkflowDefinition(id="wf1", name="test")
        engine.register_workflow(wf)
        await engine.create_execution(workflow_id="wf1")
        await engine.create_execution(workflow_id="wf1")
        assert len(engine.list_executions()) == 2

    @pytest.mark.asyncio
    async def test_get_events(self):
        engine = WorkflowEngine()
        wf = WorkflowDefinition(id="wf1", name="test")
        engine.register_workflow(wf)
        execution = await engine.create_execution(workflow_id="wf1")
        events = engine.get_events(execution.id)
        assert len(events) == 1
        assert events[0].event_type == WorkflowEventType.CREATED

    @pytest.mark.asyncio
    async def test_register_step_handler(self):
        engine = WorkflowEngine()
        handler = MagicMock(spec=StepHandler)
        handler.handler_name = "my_handler"
        engine.register_step_handler(handler)
        assert engine.step_handler_registry.get("my_handler") is handler

    @pytest.mark.asyncio
    async def test_start_execution_unknown(self):
        engine = WorkflowEngine()
        with pytest.raises(ValueError):
            await engine.start_execution("nonexistent")

    @pytest.mark.asyncio
    async def test_pause_unknown(self):
        engine = WorkflowEngine()
        with pytest.raises(ValueError):
            await engine.pause_execution("nonexistent")

    @pytest.mark.asyncio
    async def test_resume_unknown(self):
        engine = WorkflowEngine()
        with pytest.raises(ValueError):
            await engine.resume_execution("nonexistent")

    @pytest.mark.asyncio
    async def test_cancel_unknown(self):
        engine = WorkflowEngine()
        with pytest.raises(ValueError):
            await engine.cancel_execution("nonexistent")

    @pytest.mark.asyncio
    async def test_rollback_without_handler(self):
        engine = WorkflowEngine()
        wf = WorkflowDefinition(id="wf1", name="test")
        engine.register_workflow(wf)
        execution = await engine.create_execution(workflow_id="wf1")
        execution.status = WorkflowStatus.RUNNING
        engine._history.record(execution)
        result = await engine.rollback_execution(execution.id)
        assert result.status == WorkflowStatus.ROLLED_BACK


# ======================================================================
# WorkflowRepository tests
# ======================================================================

class TestWorkflowRepository:
    @pytest.mark.asyncio
    async def test_save_and_get_definition(self):
        repo = WorkflowRepository()
        wf = WorkflowDefinition(id="wf1", name="test")
        saved = await repo.save_definition(wf)
        assert saved.id == "wf1"
        retrieved = await repo.get_definition("wf1")
        assert retrieved is not None
        assert retrieved.name == "test"

    @pytest.mark.asyncio
    async def test_list_definitions(self):
        repo = WorkflowRepository()
        await repo.save_definition(WorkflowDefinition(id="wf1", name="a"))
        await repo.save_definition(WorkflowDefinition(id="wf2", name="b"))
        assert len(await repo.list_definitions()) == 2

    @pytest.mark.asyncio
    async def test_delete_definition(self):
        repo = WorkflowRepository()
        await repo.save_definition(WorkflowDefinition(id="wf1", name="test"))
        assert await repo.delete_definition("wf1") is True
        assert await repo.delete_definition("nonexistent") is False

    @pytest.mark.asyncio
    async def test_save_and_get_execution(self):
        repo = WorkflowRepository()
        exec_ = WorkflowExecution(id="e1", workflow_id="wf1", workflow_name="test")
        saved = await repo.save_execution(exec_)
        assert saved.id == "e1"
        retrieved = await repo.get_execution("e1")
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_list_executions(self):
        repo = WorkflowRepository()
        await repo.save_execution(WorkflowExecution(id="e1", workflow_id="wf1", workflow_name="a"))
        await repo.save_execution(WorkflowExecution(id="e2", workflow_id="wf1", workflow_name="b"))
        assert len(await repo.list_executions()) == 2
        assert len(await repo.list_executions(workflow_id="wf1")) == 2

    @pytest.mark.asyncio
    async def test_delete_execution(self):
        repo = WorkflowRepository()
        await repo.save_execution(WorkflowExecution(id="e1", workflow_id="wf1", workflow_name="a"))
        assert await repo.delete_execution("e1") is True


# ======================================================================
# Cognitive integration tests
# ======================================================================

class TestWorkflowCognitiveIntegration:
    @pytest.mark.asyncio
    async def test_workflow_handler_returns_workflow_action(self):
        handler = WorkflowHandler()
        assert IntentType.WORKFLOW in handler.handled_intents
        ctx = CognitiveContext(raw_input="run the deployment workflow")
        dec = await handler.decide(ctx)
        assert dec.action == DecisionAction.EXECUTE_WORKFLOW
        assert dec.handler_name == "workflow"

    @pytest.mark.asyncio
    async def test_default_handler_registry_includes_workflow(self):
        registry = default_handler_registry()
        assert IntentType.WORKFLOW in registry

    @pytest.mark.asyncio
    async def test_intent_type_has_workflow(self):
        assert IntentType.WORKFLOW.value == "WORKFLOW"

    @pytest.mark.asyncio
    async def test_decision_action_has_execute_workflow(self):
        assert DecisionAction.EXECUTE_WORKFLOW.value == "EXECUTE_WORKFLOW"

    @pytest.mark.asyncio
    async def test_workflow_detection_pattern(self):
        from app.cognitive.router import RuleBasedIntentDetector
        detector = RuleBasedIntentDetector()
        ctx = CognitiveContext(raw_input="start the deployment workflow")
        intent, conf = await detector.detect(ctx)
        assert intent == IntentType.WORKFLOW
        assert conf > 0

    @pytest.mark.asyncio
    async def test_workflow_detection_pipeline(self):
        from app.cognitive.router import RuleBasedIntentDetector
        detector = RuleBasedIntentDetector()
        ctx = CognitiveContext(raw_input="run the automation pipeline")
        intent, conf = await detector.detect(ctx)
        assert intent == IntentType.WORKFLOW

    @pytest.mark.asyncio
    async def test_cognitive_engine_with_workflow(self):
        mock_gm = MagicMock()
        mock_gm.list_goals = AsyncMock(return_value=[])
        mock_tm = MagicMock()
        mock_tm.list_tasks = AsyncMock(return_value=[])
        mock_am = MagicMock()
        mock_am.list_runtime_agents = MagicMock(return_value=[])
        mock_pm = MagicMock()
        mock_pm.get_profile = AsyncMock(return_value={})
        mock_cm = MagicMock()
        mock_cm.get_history = AsyncMock(return_value=[])

        workflow_engine = WorkflowEngine()

        engine = CognitiveEngine(
            goal_manager=mock_gm,
            task_manager=mock_tm,
            agent_manager=mock_am,
            profile_memory=mock_pm,
            conversation_memory=mock_cm,
            workflow_engine=workflow_engine,
        )

        state = await engine.process(
            raw_input="run the deployment workflow"
        )
        assert state.decision is not None
        assert state.error is None

    @pytest.mark.asyncio
    async def test_cognitive_engine_workflow_execution(self):
        mock_gm = MagicMock()
        mock_gm.list_goals = AsyncMock(return_value=[])
        mock_tm = MagicMock()
        mock_tm.list_tasks = AsyncMock(return_value=[])
        mock_am = MagicMock()
        mock_am.list_runtime_agents = MagicMock(return_value=[])
        mock_pm = MagicMock()
        mock_pm.get_profile = AsyncMock(return_value={})
        mock_cm = MagicMock()
        mock_cm.get_history = AsyncMock(return_value=[])

        workflow_engine = WorkflowEngine()
        wf = WorkflowDefinition(id="wf1", name="deployment")
        workflow_engine.register_workflow(wf)

        engine = CognitiveEngine(
            goal_manager=mock_gm,
            task_manager=mock_tm,
            agent_manager=mock_am,
            profile_memory=mock_pm,
            conversation_memory=mock_cm,
            workflow_engine=workflow_engine,
        )

        ctx = CognitiveContext(raw_input="run deployment")
        decision = CognitiveDecision(
            action=DecisionAction.EXECUTE_WORKFLOW,
            handler_name="workflow",
            payload={"task": "deployment", "user_id": "u1", "session_id": "s1"},
        )
        result = await engine._execute_decision(decision, ctx)
        assert result is not None
        assert "workflow_execution" in result
        assert result["workflow_name"] == "deployment"

    @pytest.mark.asyncio
    async def test_cognitive_engine_workflow_without_engine(self):
        mock_gm = MagicMock()
        mock_gm.list_goals = AsyncMock(return_value=[])
        mock_tm = MagicMock()
        mock_tm.list_tasks = AsyncMock(return_value=[])
        mock_am = MagicMock()
        mock_am.list_runtime_agents = MagicMock(return_value=[])
        mock_pm = MagicMock()
        mock_pm.get_profile = AsyncMock(return_value={})
        mock_cm = MagicMock()
        mock_cm.get_history = AsyncMock(return_value=[])

        engine = CognitiveEngine(
            goal_manager=mock_gm,
            task_manager=mock_tm,
            agent_manager=mock_am,
            profile_memory=mock_pm,
            conversation_memory=mock_cm,
        )

        ctx = CognitiveContext(raw_input="run workflow")
        decision = CognitiveDecision(
            action=DecisionAction.EXECUTE_WORKFLOW,
            handler_name="workflow",
            payload={"task": "test", "user_id": None, "session_id": None},
        )
        result = await engine._execute_decision(decision, ctx)
        assert result is not None
        assert "error" in result
        assert "WorkflowEngine not available" in result["error"]

    @pytest.mark.asyncio
    async def test_workflow_execution_no_match(self):
        mock_gm = MagicMock()
        mock_gm.list_goals = AsyncMock(return_value=[])
        mock_tm = MagicMock()
        mock_tm.list_tasks = AsyncMock(return_value=[])
        mock_am = MagicMock()
        mock_am.list_runtime_agents = MagicMock(return_value=[])
        mock_pm = MagicMock()
        mock_pm.get_profile = AsyncMock(return_value={})
        mock_cm = MagicMock()
        mock_cm.get_history = AsyncMock(return_value=[])

        workflow_engine = WorkflowEngine()
        wf = WorkflowDefinition(id="wf1", name="unrelated")
        workflow_engine.register_workflow(wf)

        engine = CognitiveEngine(
            goal_manager=mock_gm,
            task_manager=mock_tm,
            agent_manager=mock_am,
            profile_memory=mock_pm,
            conversation_memory=mock_cm,
            workflow_engine=workflow_engine,
        )

        ctx = CognitiveContext(raw_input="something completely different")
        decision = CognitiveDecision(
            action=DecisionAction.EXECUTE_WORKFLOW,
            handler_name="workflow",
            payload={"task": "xyzzy", "user_id": None, "session_id": None},
        )
        result = await engine._execute_decision(decision, ctx)
        assert "error" in result


# ======================================================================
# Edge cases
# ======================================================================

class TestEdgeCases:
    def test_workflow_status_enum_values(self):
        assert WorkflowStatus.PENDING.value == "PENDING"
        assert WorkflowStatus.RUNNING.value == "RUNNING"
        assert WorkflowStatus.PAUSED.value == "PAUSED"
        assert WorkflowStatus.COMPLETED.value == "COMPLETED"
        assert WorkflowStatus.FAILED.value == "FAILED"
        assert WorkflowStatus.CANCELLED.value == "CANCELLED"
        assert WorkflowStatus.ROLLING_BACK.value == "ROLLING_BACK"
        assert WorkflowStatus.ROLLED_BACK.value == "ROLLED_BACK"

    def test_step_type_enum_values(self):
        assert StepType.TASK.value == "TASK"
        assert StepType.CONDITION.value == "CONDITION"
        assert StepType.PARALLEL.value == "PARALLEL"
        assert StepType.LOOP.value == "LOOP"
        assert StepType.SUB_WORKFLOW.value == "SUB_WORKFLOW"
        assert StepType.WAIT.value == "WAIT"
        assert StepType.DECISION.value == "DECISION"

    def test_workflow_event_type_values(self):
        assert WorkflowEventType.CREATED.value == "CREATED"
        assert WorkflowEventType.STARTED.value == "STARTED"
        assert WorkflowEventType.COMPLETED.value == "COMPLETED"

    @pytest.mark.asyncio
    async def test_builder_with_retry_policy(self):
        rp = RetryPolicy(max_retries=5, delay_seconds=2.0)
        wf = (
            WorkflowBuilder("test")
            .task_step("s1", "Step 1", "echo", retry_policy=rp)
            .build()
        )
        step = wf.steps[0]
        assert step.retry_policy is not None
        assert step.retry_policy.max_retries == 5

    def test_condition_step_defaults(self):
        cs = ConditionStep(id="c1", name="cond")
        assert cs.conditions == []
        assert cs.if_branch == []
        assert cs.else_branch == []

    def test_parallel_step_defaults(self):
        ps = ParallelStep(id="p1", name="parallel")
        assert ps.branches == []

    def test_loop_step_defaults(self):
        ls = LoopStep(id="l1", name="loop", loop_over="items")
        assert ls.max_iterations == 10
        assert ls.body == []
        assert ls.convergence_condition is None
