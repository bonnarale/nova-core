"""Comprehensive tests for Chapter 21 — Workflow Engine."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import pytest
import pytest_asyncio

from app.workflows.base import (
    ConditionEvaluator,
    RollbackHandler,
    StepHandler,
    WorkflowCompilerABC,
    WorkflowDispatcherABC,
    WorkflowExecutor,
    WorkflowProvider,
    WorkflowRepositoryABC,
    WorkflowValidatorABC,
)
from app.workflows.compiler import WorkflowCompiler
from app.workflows.context import Checkpoint, WorkflowContext
from app.workflows.dispatcher import WorkflowDispatcher
from app.workflows.edge import EdgeType, WorkflowEdge
from app.workflows.factory import WorkflowFactory
from app.workflows.graph import WorkflowGraph
from app.workflows.lifecycle import WorkflowLifecycle, WorkflowLifecycleState
from app.workflows.metrics import WorkflowMetrics, get_workflow_metrics
from app.workflows.node import (
    ActionNode,
    AgentNode,
    ConditionNode,
    DecisionNode,
    DelayNode,
    EndNode,
    EventNode,
    GoalNode,
    HumanApprovalNode,
    LoopNode,
    MergeNode,
    NodeStatus,
    NodeType,
    ParallelNode,
    StartNode,
    SubworkflowNode,
    TaskNode,
    ToolNode,
    WaitNode,
    WorkflowNode,
)
from app.workflows.orchestrator import WorkflowOrchestrator
from app.workflows.persistence import InMemoryWorkflowPersistence
from app.workflows.schemas import (
    WorkflowCloneRequest,
    WorkflowCreate,
    WorkflowEdgeSchema,
    WorkflowGraphRequest,
    WorkflowHealthResponse,
    WorkflowImportRequest,
    WorkflowMetricsResponse,
    WorkflowNodeSchema,
    WorkflowStatisticsResponse,
    WorkflowTemplateResponse,
    WorkflowTracesResponse,
)
from app.workflows.templates import (
    DEFAULT_TEMPLATES,
    create_chat_workflow,
    create_coding_workflow,
    create_goal_execution_workflow,
    create_multi_agent_workflow,
    create_planning_workflow,
    create_rag_workflow,
    create_research_workflow,
    create_task_automation_workflow,
    get_template,
    list_templates,
)
from app.workflows.tracing import WorkflowTracer, WorkflowTraceSpan
from app.workflows.validation import WorkflowValidator
from app.workflows.variables import VariableScope, VariableStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_node(node_id: str = "n1", name: str = "Node 1", node_type: NodeType = NodeType.ACTION, handler: str = "test_handler") -> WorkflowNode:
    return WorkflowNode(node_id=node_id, name=name, node_type=node_type, handler=handler)


def _make_edge(edge_id: str = "e1", source: str = "n1", target: str = "n2") -> WorkflowEdge:
    return WorkflowEdge(edge_id=edge_id, source_node_id=source, target_node_id=target)


def _make_definition(workflow_id: str = "wf-1", name: str = "Test Workflow") -> Any:
    from app.workflows.models import WorkflowDefinition, WorkflowStep, StepType
    step = WorkflowStep(id="step-1", name="Test Step", step_type=StepType.TASK, handler="test_handler")
    return WorkflowDefinition(id=workflow_id, name=name, description="Test", tags=["test"], steps=[step])


# ===================================================================
# SECTION 1 — Node Types
# ===================================================================

class TestNodeTypes:
    def test_node_type_enum(self) -> None:
        assert NodeType.START == "start"
        assert NodeType.END == "end"
        assert NodeType.ACTION == "action"
        assert NodeType.TOOL == "tool"
        assert NodeType.AGENT == "agent"
        assert NodeType.TASK == "task"
        assert NodeType.GOAL == "goal"
        assert NodeType.DECISION == "decision"
        assert NodeType.CONDITION == "condition"
        assert NodeType.LOOP == "loop"
        assert NodeType.PARALLEL == "parallel"
        assert NodeType.MERGE == "merge"
        assert NodeType.WAIT == "wait"
        assert NodeType.DELAY == "delay"
        assert NodeType.EVENT == "event"
        assert NodeType.HUMAN_APPROVAL == "human_approval"
        assert NodeType.SUBWORKFLOW == "subworkflow"

    def test_node_status_enum(self) -> None:
        assert NodeStatus.PENDING == "pending"
        assert NodeStatus.RUNNING == "running"
        assert NodeStatus.COMPLETED == "completed"
        assert NodeStatus.FAILED == "failed"

    def test_workflow_node_creation(self) -> None:
        node = WorkflowNode(node_id="n1", name="Test", node_type=NodeType.ACTION)
        assert node.node_id == "n1"
        assert node.name == "Test"
        assert node.status == NodeStatus.PENDING

    def test_workflow_node_to_dict(self) -> None:
        node = WorkflowNode(node_id="n1", name="Test")
        d = node.to_dict()
        assert d["node_id"] == "n1"
        assert d["node_type"] == "action"

    def test_start_node(self) -> None:
        node = StartNode(node_id="s", name="Start")
        assert node.node_type == NodeType.START

    def test_end_node(self) -> None:
        node = EndNode(node_id="e", name="End")
        assert node.node_type == NodeType.END

    def test_tool_node(self) -> None:
        node = ToolNode(node_id="t", name="Tool", tool_name="my_tool")
        assert node.node_type == NodeType.TOOL
        assert node.tool_name == "my_tool"

    def test_agent_node(self) -> None:
        node = AgentNode(node_id="a", name="Agent", agent_id="agent-1", prompt="do stuff")
        assert node.node_type == NodeType.AGENT
        assert node.agent_id == "agent-1"

    def test_task_node(self) -> None:
        node = TaskNode(node_id="t", name="Task", task_type="compute")
        assert node.node_type == NodeType.TASK

    def test_goal_node(self) -> None:
        node = GoalNode(node_id="g", name="Goal", goal_id="goal-1")
        assert node.node_type == NodeType.GOAL

    def test_decision_node(self) -> None:
        node = DecisionNode(node_id="d", name="Decision", conditions=[{"field": "x", "op": "eq", "value": 1}])
        assert node.node_type == NodeType.DECISION
        assert len(node.conditions) == 1

    def test_condition_node(self) -> None:
        node = ConditionNode(node_id="c", name="Cond", true_branch="n2", false_branch="n3")
        assert node.node_type == NodeType.CONDITION

    def test_loop_node(self) -> None:
        node = LoopNode(node_id="l", name="Loop", max_iterations=5)
        assert node.node_type == NodeType.LOOP
        assert node.max_iterations == 5

    def test_parallel_node(self) -> None:
        node = ParallelNode(node_id="p", name="Parallel", branch_node_ids=[["a", "b"], ["c"]])
        assert node.node_type == NodeType.PARALLEL

    def test_merge_node(self) -> None:
        node = MergeNode(node_id="m", name="Merge", merge_strategy="all")
        assert node.node_type == NodeType.MERGE

    def test_wait_node(self) -> None:
        node = WaitNode(node_id="w", name="Wait", wait_for_event="approval")
        assert node.node_type == NodeType.WAIT

    def test_delay_node(self) -> None:
        node = DelayNode(node_id="d", name="Delay", delay_seconds=5.0)
        assert node.node_type == NodeType.DELAY

    def test_event_node(self) -> None:
        node = EventNode(node_id="e", name="Event", event_type="data_ready")
        assert node.node_type == NodeType.EVENT

    def test_human_approval_node(self) -> None:
        node = HumanApprovalNode(node_id="h", name="Approve", approvers=["user1"], message="Please approve")
        assert node.node_type == NodeType.HUMAN_APPROVAL

    def test_subworkflow_node(self) -> None:
        node = SubworkflowNode(node_id="sw", name="Sub", subworkflow_id="wf-sub")
        assert node.node_type == NodeType.SUBWORKFLOW


# ===================================================================
# SECTION 2 — Edge
# ===================================================================

class TestEdge:
    def test_edge_creation(self) -> None:
        edge = WorkflowEdge(edge_id="e1", source_node_id="n1", target_node_id="n2")
        assert edge.source_node_id == "n1"
        assert edge.target_node_id == "n2"
        assert edge.edge_type == EdgeType.NORMAL

    def test_edge_types(self) -> None:
        assert EdgeType.NORMAL == "normal"
        assert EdgeType.CONDITIONAL == "conditional"
        assert EdgeType.ERROR == "error"
        assert EdgeType.FALLBACK == "fallback"

    def test_edge_to_dict(self) -> None:
        edge = WorkflowEdge(edge_id="e1", source_node_id="n1", target_node_id="n2", label="go")
        d = edge.to_dict()
        assert d["edge_id"] == "e1"
        assert d["label"] == "go"

    def test_conditional_edge(self) -> None:
        edge = WorkflowEdge(edge_id="e1", source_node_id="n1", target_node_id="n2", edge_type=EdgeType.CONDITIONAL, condition={"field": "x", "op": "eq", "value": 1})
        assert edge.edge_type == EdgeType.CONDITIONAL
        assert edge.condition is not None


# ===================================================================
# SECTION 3 — Graph
# ===================================================================

class TestWorkflowGraph:
    @pytest.fixture
    def graph(self) -> WorkflowGraph:
        return WorkflowGraph()

    def test_empty_graph(self, graph: WorkflowGraph) -> None:
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_add_node(self, graph: WorkflowGraph) -> None:
        node = _make_node(node_id="n1", name="N1")
        graph.add_node(node)
        assert graph.node_count == 1
        assert graph.get_node("n1") is node

    def test_add_edge(self, graph: WorkflowGraph) -> None:
        n1 = _make_node(node_id="n1", name="N1")
        n2 = _make_node(node_id="n2", name="N2")
        graph.add_node(n1)
        graph.add_node(n2)
        edge = _make_edge(edge_id="e1", source="n1", target="n2")
        graph.add_edge(edge)
        assert graph.edge_count == 1

    def test_successors(self, graph: WorkflowGraph) -> None:
        n1 = _make_node(node_id="n1", name="N1")
        n2 = _make_node(node_id="n2", name="N2")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_edge(_make_edge(source="n1", target="n2"))
        succs = graph.get_successors("n1")
        assert len(succs) == 1
        assert succs[0].node_id == "n2"

    def test_predecessors(self, graph: WorkflowGraph) -> None:
        n1 = _make_node(node_id="n1", name="N1")
        n2 = _make_node(node_id="n2", name="N2")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_edge(_make_edge(source="n1", target="n2"))
        preds = graph.get_predecessors("n2")
        assert len(preds) == 1
        assert preds[0].node_id == "n1"

    def test_start_nodes(self, graph: WorkflowGraph) -> None:
        graph.add_node(StartNode(node_id="start", name="Start"))
        graph.add_node(EndNode(node_id="end", name="End"))
        starts = graph.get_start_nodes()
        assert len(starts) == 1
        assert starts[0].node_type == NodeType.START

    def test_end_nodes(self, graph: WorkflowGraph) -> None:
        graph.add_node(StartNode(node_id="start", name="Start"))
        graph.add_node(EndNode(node_id="end", name="End"))
        ends = graph.get_end_nodes()
        assert len(ends) == 1
        assert ends[0].node_type == NodeType.END

    def test_topological_sort(self, graph: WorkflowGraph) -> None:
        graph.add_node(_make_node(node_id="n2", name="N2"))
        graph.add_node(_make_node(node_id="n1", name="N1"))
        graph.add_edge(_make_edge(source="n1", target="n2"))
        sorted_nodes = graph.topological_sort()
        ids = [n.node_id for n in sorted_nodes]
        assert ids.index("n1") < ids.index("n2")

    def test_detect_cycles_no_cycle(self, graph: WorkflowGraph) -> None:
        graph.add_node(_make_node(node_id="n1", name="N1"))
        graph.add_node(_make_node(node_id="n2", name="N2"))
        graph.add_edge(_make_edge(source="n1", target="n2"))
        cycles = graph.detect_cycles()
        assert cycles == []

    def test_detect_cycles_with_cycle(self) -> None:
        graph = WorkflowGraph()
        n1 = _make_node(node_id="n1", name="N1")
        n2 = _make_node(node_id="n2", name="N2")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_edge(_make_edge(source="n1", target="n2"))
        graph.add_edge(_make_edge(edge_id="e2", source="n2", target="n1"))
        cycles = graph.detect_cycles()
        assert len(cycles) > 0

    def test_is_valid_dag(self) -> None:
        graph = WorkflowGraph()
        graph.add_node(StartNode(node_id="start", name="Start"))
        graph.add_node(_make_node(node_id="n1", name="N1"))
        graph.add_node(EndNode(node_id="end", name="End"))
        graph.add_edge(_make_edge(source="start", target="n1"))
        graph.add_edge(_make_edge(edge_id="e2", source="n1", target="end"))
        valid, msg = graph.is_valid_dag()
        assert valid is True

    def test_is_valid_dag_no_start(self) -> None:
        graph = WorkflowGraph()
        graph.add_node(_make_node(node_id="n1", name="N1"))
        graph.add_node(EndNode(node_id="end", name="End"))
        valid, msg = graph.is_valid_dag()
        assert valid is False
        assert "No start node" in msg

    def test_is_valid_dag_no_end(self) -> None:
        graph = WorkflowGraph()
        graph.add_node(StartNode(node_id="start", name="Start"))
        graph.add_node(_make_node(node_id="n1", name="N1"))
        valid, msg = graph.is_valid_dag()
        assert valid is False
        assert "No end node" in msg

    def test_is_valid_dag_cycle(self) -> None:
        graph = WorkflowGraph()
        graph.add_node(StartNode(node_id="start", name="Start"))
        graph.add_node(_make_node(node_id="n1", name="N1"))
        graph.add_node(_make_node(node_id="n2", name="N2"))
        graph.add_edge(_make_edge(source="start", target="n1"))
        graph.add_edge(_make_edge(edge_id="e2", source="n1", target="n2"))
        graph.add_edge(_make_edge(edge_id="e3", source="n2", target="n1"))
        valid, msg = graph.is_valid_dag()
        assert valid is False
        assert "Cycle" in msg

    def test_get_reachable_nodes(self, graph: WorkflowGraph) -> None:
        graph.add_node(_make_node(node_id="n1", name="N1"))
        graph.add_node(_make_node(node_id="n2", name="N2"))
        graph.add_node(_make_node(node_id="n3", name="N3"))
        graph.add_edge(_make_edge(source="n1", target="n2"))
        reachable = graph.get_reachable_nodes("n1")
        ids = {n.node_id for n in reachable}
        assert "n1" in ids
        assert "n2" in ids

    def test_get_execution_paths(self) -> None:
        graph = WorkflowGraph()
        graph.add_node(StartNode(node_id="start", name="Start"))
        graph.add_node(_make_node(node_id="n1", name="N1"))
        graph.add_node(EndNode(node_id="end", name="End"))
        graph.add_edge(_make_edge(source="start", target="n1"))
        graph.add_edge(_make_edge(edge_id="e2", source="n1", target="end"))
        paths = graph.get_execution_paths()
        assert len(paths) >= 1

    def test_clear(self, graph: WorkflowGraph) -> None:
        graph.add_node(_make_node(node_id="n1", name="N1"))
        graph.clear()
        assert graph.node_count == 0


# ===================================================================
# SECTION 4 — Variables
# ===================================================================

class TestVariableStore:
    @pytest.fixture
    def store(self) -> VariableStore:
        return VariableStore()

    def test_global_variable(self, store: VariableStore) -> None:
        store.set_global("key", "value")
        assert store.get_global("key") == "value"

    def test_workflow_variable(self, store: VariableStore) -> None:
        store.set_workflow("key", 42)
        assert store.get_workflow("key") == 42

    def test_execution_variable(self, store: VariableStore) -> None:
        store.set_execution("key", True)
        assert store.get_execution("key") is True

    def test_local_variable(self, store: VariableStore) -> None:
        store.set_local("scope1", "key", "val")
        assert store.get_local("scope1", "key") == "val"

    def test_get_priority(self, store: VariableStore) -> None:
        store.set_global("x", 1)
        store.set_workflow("x", 2)
        store.set_execution("x", 3)
        assert store.get("x") == 3

    def test_get_default(self, store: VariableStore) -> None:
        assert store.get("missing", "default") == "default"

    def test_set_with_scope(self, store: VariableStore) -> None:
        store.set("key", "val", VariableScope.GLOBAL)
        assert store.get_global("key") == "val"

    def test_resolve(self, store: VariableStore) -> None:
        store.set_execution("input_val", 10)
        result = store.resolve({"target": "input_val"})
        assert result["target"] == 10

    def test_clear_local(self, store: VariableStore) -> None:
        store.set_local("s1", "k", "v")
        store.clear_local("s1")
        assert store.get_local("s1", "k") is None

    def test_clear_all(self, store: VariableStore) -> None:
        store.set_global("a", 1)
        store.set_workflow("b", 2)
        store.clear_all()
        assert store.get_global("a") is None


# ===================================================================
# SECTION 5 — Context
# ===================================================================

class TestWorkflowContext:
    def test_creation(self) -> None:
        ctx = WorkflowContext(workflow_id="wf1", execution_id="ex1")
        assert ctx.workflow_id == "wf1"
        assert ctx.execution_id == "ex1"

    def test_input_data(self) -> None:
        ctx = WorkflowContext(input_data={"key": "val"})
        assert ctx.get_variable("key") == "val"

    def test_set_get_variable(self) -> None:
        ctx = WorkflowContext()
        ctx.set_variable("x", 42)
        assert ctx.get_variable("x") == 42

    def test_output(self) -> None:
        ctx = WorkflowContext()
        ctx.set_output("result", "done")
        assert ctx.output["result"] == "done"

    def test_state(self) -> None:
        ctx = WorkflowContext()
        ctx.set_state("step", "running")
        assert ctx.get_state("step") == "running"

    def test_record_error(self) -> None:
        ctx = WorkflowContext()
        ctx.record_error("n1", "boom")
        assert len(ctx.errors) == 1
        assert ctx.errors[0]["error"] == "boom"

    def test_checkpoint(self) -> None:
        ctx = WorkflowContext()
        ctx.set_state("x", 1)
        cp = ctx.save_checkpoint("n1")
        assert cp.step_id == "n1"
        assert ctx.get_last_checkpoint() is cp

    def test_restore_checkpoint(self) -> None:
        ctx = WorkflowContext()
        ctx.set_state("x", 1)
        cp = ctx.save_checkpoint("n1")
        ctx.set_state("x", 2)
        assert ctx.restore_checkpoint(cp.checkpoint_id)
        assert ctx.get_state("x") == 1

    def test_restore_nonexistent_checkpoint(self) -> None:
        ctx = WorkflowContext()
        assert ctx.restore_checkpoint("nope") is False

    def test_to_dict(self) -> None:
        ctx = WorkflowContext(workflow_id="wf1", execution_id="ex1")
        d = ctx.to_dict()
        assert d["workflow_id"] == "wf1"


# ===================================================================
# SECTION 6 — Lifecycle
# ===================================================================

class TestWorkflowLifecycle:
    @pytest.fixture
    def lifecycle(self) -> WorkflowLifecycle:
        return WorkflowLifecycle()

    def test_initial_state(self, lifecycle: WorkflowLifecycle) -> None:
        assert lifecycle.state == WorkflowLifecycleState.REGISTERED

    def test_transitions(self, lifecycle: WorkflowLifecycle) -> None:
        assert lifecycle.transition(WorkflowLifecycleState.INITIALIZED) is True
        assert lifecycle.transition(WorkflowLifecycleState.READY) is True
        assert lifecycle.transition(WorkflowLifecycleState.RUNNING) is True
        assert lifecycle.state == WorkflowLifecycleState.RUNNING

    def test_invalid_transition(self, lifecycle: WorkflowLifecycle) -> None:
        assert lifecycle.transition(WorkflowLifecycleState.RUNNING) is False

    def test_same_state(self, lifecycle: WorkflowLifecycle) -> None:
        assert lifecycle.transition(WorkflowLifecycleState.REGISTERED) is True

    def test_can_transition(self, lifecycle: WorkflowLifecycle) -> None:
        assert lifecycle.can_transition(WorkflowLifecycleState.INITIALIZED) is True
        assert lifecycle.can_transition(WorkflowLifecycleState.RUNNING) is False

    def test_uptime(self, lifecycle: WorkflowLifecycle) -> None:
        assert lifecycle.uptime_seconds == 0.0
        lifecycle.transition(WorkflowLifecycleState.INITIALIZED)
        lifecycle.transition(WorkflowLifecycleState.READY)
        lifecycle.transition(WorkflowLifecycleState.RUNNING)
        assert lifecycle.uptime_seconds >= 0.0

    def test_transition_history(self, lifecycle: WorkflowLifecycle) -> None:
        lifecycle.transition(WorkflowLifecycleState.INITIALIZED)
        lifecycle.transition(WorkflowLifecycleState.READY)
        assert len(lifecycle.transition_history) == 2

    def test_reset(self, lifecycle: WorkflowLifecycle) -> None:
        lifecycle.transition(WorkflowLifecycleState.INITIALIZED)
        lifecycle.reset()
        assert lifecycle.state == WorkflowLifecycleState.REGISTERED

    def test_shutdown(self, lifecycle: WorkflowLifecycle) -> None:
        assert lifecycle.transition(WorkflowLifecycleState.SHUTDOWN) is True
        assert lifecycle.transition(WorkflowLifecycleState.INITIALIZED) is False

    def test_wait(self, lifecycle: WorkflowLifecycle) -> None:
        lifecycle.transition(WorkflowLifecycleState.INITIALIZED)
        lifecycle.transition(WorkflowLifecycleState.READY)
        lifecycle.transition(WorkflowLifecycleState.RUNNING)
        lifecycle.transition(WorkflowLifecycleState.WAITING)
        assert lifecycle.state == WorkflowLifecycleState.WAITING

    def test_complete(self, lifecycle: WorkflowLifecycle) -> None:
        lifecycle.transition(WorkflowLifecycleState.INITIALIZED)
        lifecycle.transition(WorkflowLifecycleState.READY)
        lifecycle.transition(WorkflowLifecycleState.RUNNING)
        lifecycle.transition(WorkflowLifecycleState.COMPLETED)
        assert lifecycle.state == WorkflowLifecycleState.COMPLETED

    def test_cancel(self, lifecycle: WorkflowLifecycle) -> None:
        lifecycle.transition(WorkflowLifecycleState.INITIALIZED)
        lifecycle.transition(WorkflowLifecycleState.READY)
        lifecycle.transition(WorkflowLifecycleState.CANCELLED)
        assert lifecycle.state == WorkflowLifecycleState.CANCELLED


# ===================================================================
# SECTION 7 — Metrics
# ===================================================================

class TestWorkflowMetrics:
    @pytest.fixture(autouse=True)
    def _reset(self) -> None:
        WorkflowMetrics.reset_singleton()

    def test_singleton(self) -> None:
        m1 = get_workflow_metrics()
        m2 = get_workflow_metrics()
        assert m1 is m2

    def test_record_created(self) -> None:
        m = get_workflow_metrics()
        m.record_created()
        assert m.workflows_created == 1

    def test_record_executed(self) -> None:
        m = get_workflow_metrics()
        m.record_executed(100.0)
        assert m.workflows_executed == 1
        assert m.average_execution_time_ms == 100.0

    def test_record_success(self) -> None:
        m = get_workflow_metrics()
        m.record_success()
        assert m.successful_executions == 1

    def test_record_failure(self) -> None:
        m = get_workflow_metrics()
        m.record_failure()
        assert m.failed_executions == 1

    def test_record_node_execution(self) -> None:
        m = get_workflow_metrics()
        m.record_node_execution()
        assert m.node_execution_count == 1

    def test_record_retry(self) -> None:
        m = get_workflow_metrics()
        m.record_retry()
        assert m.retry_count == 1

    def test_record_rollback(self) -> None:
        m = get_workflow_metrics()
        m.record_rollback()
        assert m.rollback_count == 1

    def test_average_time(self) -> None:
        m = get_workflow_metrics()
        m.record_executed(100.0)
        m.record_executed(200.0)
        assert m.average_execution_time_ms == 150.0

    def test_to_dict(self) -> None:
        m = get_workflow_metrics()
        m.record_created()
        d = m.to_dict()
        assert d["workflows_created"] == 1

    def test_reset(self) -> None:
        m = get_workflow_metrics()
        m.record_created()
        m.reset()
        assert m.workflows_created == 0

    def test_uptime(self) -> None:
        m = get_workflow_metrics()
        assert m.uptime_seconds >= 0.0


# ===================================================================
# SECTION 8 — Tracing
# ===================================================================

class TestWorkflowTracer:
    @pytest.fixture
    def tracer(self) -> WorkflowTracer:
        return WorkflowTracer()

    def test_start_end_span(self, tracer: WorkflowTracer) -> None:
        span = tracer.start_span("test")
        assert span.name == "test"
        tracer.end_span(span)
        assert span.end_time is not None
        assert span.duration_ms is not None

    def test_span_attributes(self, tracer: WorkflowTracer) -> None:
        span = tracer.start_span("test")
        span.set_attribute("key", "value")
        assert span.attributes["key"] == "value"
        tracer.end_span(span)

    def test_span_error(self, tracer: WorkflowTracer) -> None:
        span = tracer.start_span("test")
        span.set_error("err")
        assert span.status == "error"
        tracer.end_span(span)

    def test_get_traces(self, tracer: WorkflowTracer) -> None:
        span = tracer.start_span("op1")
        tracer.end_span(span)
        traces = tracer.get_traces()
        assert len(traces) == 1

    def test_get_traces_by_name(self, tracer: WorkflowTracer) -> None:
        s1 = tracer.start_span("op1")
        tracer.end_span(s1)
        s2 = tracer.start_span("op2")
        tracer.end_span(s2)
        assert len(tracer.get_traces(name="op1")) == 1

    def test_get_span(self, tracer: WorkflowTracer) -> None:
        span = tracer.start_span("test")
        found = tracer.get_span(span.span_id)
        assert found is span
        tracer.end_span(span)

    def test_clear(self, tracer: WorkflowTracer) -> None:
        span = tracer.start_span("test")
        tracer.end_span(span)
        count = tracer.clear()
        assert count == 1

    def test_max_spans(self) -> None:
        tracer = WorkflowTracer(max_spans=3)
        for i in range(5):
            span = tracer.start_span(f"s{i}")
            tracer.end_span(span)
        assert tracer.span_count == 3

    def test_to_dict(self, tracer: WorkflowTracer) -> None:
        span = tracer.start_span("test")
        tracer.end_span(span)
        d = tracer.to_dict()
        assert d["total"] == 1

    def test_trace_span_to_dict(self) -> None:
        span = WorkflowTraceSpan("test")
        span.set_attribute("k", "v")
        d = span.to_dict()
        assert d["name"] == "test"
        assert d["attributes"]["k"] == "v"


# ===================================================================
# SECTION 9 — Persistence
# ===================================================================

class TestInMemoryWorkflowPersistence:
    @pytest.fixture
    def persistence(self) -> InMemoryWorkflowPersistence:
        return InMemoryWorkflowPersistence()

    @pytest.mark.asyncio
    async def test_store_and_get_definition(self, persistence: InMemoryWorkflowPersistence) -> None:
        defn = _make_definition()
        await persistence.store_definition(defn)
        got = await persistence.get_definition("wf-1")
        assert got is not None

    @pytest.mark.asyncio
    async def test_get_nonexistent_definition(self, persistence: InMemoryWorkflowPersistence) -> None:
        assert await persistence.get_definition("nope") is None

    @pytest.mark.asyncio
    async def test_delete_definition(self, persistence: InMemoryWorkflowPersistence) -> None:
        await persistence.store_definition(_make_definition())
        assert await persistence.delete_definition("wf-1") is True
        assert await persistence.get_definition("wf-1") is None

    @pytest.mark.asyncio
    async def test_list_definitions(self, persistence: InMemoryWorkflowPersistence) -> None:
        await persistence.store_definition(_make_definition("wf-1"))
        await persistence.store_definition(_make_definition("wf-2", "WF2"))
        defs = await persistence.list_definitions()
        assert len(defs) == 2

    @pytest.mark.asyncio
    async def test_list_definitions_by_tag(self, persistence: InMemoryWorkflowPersistence) -> None:
        await persistence.store_definition(_make_definition("wf-1"))
        defs = await persistence.list_definitions(tag="test")
        assert len(defs) == 1

    @pytest.mark.asyncio
    async def test_count_definitions(self, persistence: InMemoryWorkflowPersistence) -> None:
        await persistence.store_definition(_make_definition())
        assert await persistence.count_definitions() == 1

    @pytest.mark.asyncio
    async def test_store_and_get_execution(self, persistence: InMemoryWorkflowPersistence) -> None:
        from app.workflows.models import WorkflowExecution, WorkflowStatus
        ex = WorkflowExecution(id="ex-1", workflow_id="wf-1", status=WorkflowStatus.PENDING)
        await persistence.store_execution(ex)
        got = await persistence.get_execution("ex-1")
        assert got is not None

    @pytest.mark.asyncio
    async def test_count_executions(self, persistence: InMemoryWorkflowPersistence) -> None:
        from app.workflows.models import WorkflowExecution, WorkflowStatus
        await persistence.store_execution(WorkflowExecution(id="ex-1", workflow_id="wf-1"))
        assert await persistence.count_executions() == 1

    @pytest.mark.asyncio
    async def test_clear(self, persistence: InMemoryWorkflowPersistence) -> None:
        await persistence.store_definition(_make_definition())
        from app.workflows.models import WorkflowExecution
        await persistence.store_execution(WorkflowExecution(id="ex-1", workflow_id="wf-1"))
        count = await persistence.clear()
        assert count == 2


# ===================================================================
# SECTION 10 — Validation
# ===================================================================

class TestWorkflowValidator:
    @pytest.fixture
    def validator(self) -> WorkflowValidator:
        return WorkflowValidator()

    def test_validate_valid_definition(self, validator: WorkflowValidator) -> None:
        valid, errors = validator.validate_definition({"name": "Test", "steps": [{"id": "s1"}]})
        assert valid is True

    def test_validate_no_name(self, validator: WorkflowValidator) -> None:
        valid, errors = validator.validate_definition({"steps": []})
        assert valid is False
        assert any("name" in e.lower() for e in errors)

    def test_validate_no_steps(self, validator: WorkflowValidator) -> None:
        valid, errors = validator.validate_definition({"name": "Test"})
        assert valid is False

    def test_validate_valid_graph(self, validator: WorkflowValidator) -> None:
        graph = WorkflowGraph()
        graph.add_node(StartNode(node_id="start", name="Start"))
        graph.add_node(_make_node(node_id="n1", name="N1"))
        graph.add_node(EndNode(node_id="end", name="End"))
        graph.add_edge(_make_edge(source="start", target="n1"))
        graph.add_edge(_make_edge(edge_id="e2", source="n1", target="end"))
        valid, errors = validator.validate_graph(graph)
        assert valid is True

    def test_validate_graph_no_start(self, validator: WorkflowValidator) -> None:
        graph = WorkflowGraph()
        graph.add_node(_make_node(node_id="n1", name="N1"))
        graph.add_node(EndNode(node_id="end", name="End"))
        valid, errors = validator.validate_graph(graph)
        assert valid is False

    def test_validate_node(self, validator: WorkflowValidator) -> None:
        valid, errors = validator.validate_node(_make_node(node_id="n1", name="N1"))
        assert valid is True

    def test_validate_node_no_id(self, validator: WorkflowValidator) -> None:
        valid, errors = validator.validate_node(WorkflowNode(name="N1"))
        assert valid is False

    def test_validate_edge(self, validator: WorkflowValidator) -> None:
        edge = _make_edge(source="n1", target="n2")
        valid, errors = validator.validate_edge(edge, {"n1", "n2"})
        assert valid is True

    def test_validate_edge_unknown_node(self, validator: WorkflowValidator) -> None:
        edge = _make_edge(source="n1", target="n2")
        valid, errors = validator.validate_edge(edge, {"n1"})
        assert valid is False

    def test_validate_edge_self_ref(self, validator: WorkflowValidator) -> None:
        edge = _make_edge(source="n1", target="n1")
        valid, errors = validator.validate_edge(edge, {"n1"})
        assert valid is False


# ===================================================================
# SECTION 11 — Compiler
# ===================================================================

class TestWorkflowCompiler:
    @pytest.fixture
    def compiler(self) -> WorkflowCompiler:
        return WorkflowCompiler()

    def test_compile_from_steps(self, compiler: WorkflowCompiler) -> None:
        steps = [
            {"id": "s1", "name": "Step 1", "step_type": "TASK", "handler": "h1"},
            {"id": "s2", "name": "Step 2", "step_type": "TASK", "handler": "h2"},
        ]
        graph = compiler.compile_from_steps(steps, "wf1")
        assert graph.node_count >= 3
        valid, _ = graph.is_valid_dag()
        assert valid is True

    def test_compile_empty_steps(self, compiler: WorkflowCompiler) -> None:
        graph = compiler.compile_from_steps([], "wf1")
        assert graph.get_start_nodes()
        assert graph.get_end_nodes()

    def test_compile_from_graph_def(self, compiler: WorkflowCompiler) -> None:
        nodes = [
            {"node_id": "n1", "node_type": "start", "name": "Start"},
            {"node_id": "n2", "node_type": "action", "name": "Action", "handler": "h1"},
            {"node_id": "n3", "node_type": "end", "name": "End"},
        ]
        edges = [
            {"edge_id": "e1", "source_node_id": "n1", "target_node_id": "n2"},
            {"edge_id": "e2", "source_node_id": "n2", "target_node_id": "n3"},
        ]
        graph = compiler.compile_from_graph_def(nodes, edges, "wf1")
        assert graph.node_count == 3
        assert graph.edge_count == 2

    def test_compile_cache(self, compiler: WorkflowCompiler) -> None:
        steps = [{"id": "s1", "name": "S1"}]
        compiler.compile_from_steps(steps, "wf1")
        assert compiler.get_compiled("wf1") is not None

    def test_invalidate(self, compiler: WorkflowCompiler) -> None:
        steps = [{"id": "s1", "name": "S1"}]
        compiler.compile_from_steps(steps, "wf1")
        assert compiler.invalidate("wf1") is True
        assert compiler.get_compiled("wf1") is None

    def test_compile_all_node_types(self, compiler: WorkflowCompiler) -> None:
        nodes = [
            {"node_id": "start", "node_type": "start", "name": "Start"},
            {"node_id": "action", "node_type": "action", "name": "Action", "handler": "h"},
            {"node_id": "tool", "node_type": "tool", "name": "Tool", "handler": "h"},
            {"node_id": "agent", "node_type": "agent", "name": "Agent", "handler": "h"},
            {"node_id": "task", "node_type": "task", "name": "Task", "handler": "h"},
            {"node_id": "goal", "node_type": "goal", "name": "Goal", "handler": "h"},
            {"node_id": "condition", "node_type": "condition", "name": "Cond"},
            {"node_id": "loop", "node_type": "loop", "name": "Loop"},
            {"node_id": "parallel", "node_type": "parallel", "name": "Parallel"},
            {"node_id": "merge", "node_type": "merge", "name": "Merge"},
            {"node_id": "wait", "node_type": "wait", "name": "Wait"},
            {"node_id": "delay", "node_type": "delay", "name": "Delay"},
            {"node_id": "event", "node_type": "event", "name": "Event"},
            {"node_id": "human", "node_type": "human_approval", "name": "Human"},
            {"node_id": "subwf", "node_type": "subworkflow", "name": "Sub"},
            {"node_id": "decision", "node_type": "decision", "name": "Decision"},
            {"node_id": "end", "node_type": "end", "name": "End"},
        ]
        edges = [
            {"edge_id": f"e{i}", "source_node_id": nodes[i]["node_id"], "target_node_id": nodes[i+1]["node_id"]}
            for i in range(len(nodes) - 1)
        ]
        graph = compiler.compile_from_graph_def(nodes, edges, "wf1")
        assert graph.node_count == 17
        assert graph.edge_count == 16


# ===================================================================
# SECTION 12 — Dispatcher
# ===================================================================

class TestWorkflowDispatcher:
    @pytest.fixture
    def dispatcher(self) -> WorkflowDispatcher:
        return WorkflowDispatcher()

    @pytest.mark.asyncio
    async def test_start_stop(self, dispatcher: WorkflowDispatcher) -> None:
        assert dispatcher.is_running is False
        await dispatcher.start()
        assert dispatcher.is_running is True
        await dispatcher.stop()
        assert dispatcher.is_running is False

    def test_register_handler(self, dispatcher: WorkflowDispatcher) -> None:
        async def handler(node: Any, ctx: Any) -> str:
            return "ok"
        dispatcher.register_handler("test", handler)
        assert dispatcher.get_handler("test") is not None

    def test_register_type_handler(self, dispatcher: WorkflowDispatcher) -> None:
        async def handler(node: Any, ctx: Any) -> str:
            return "ok"
        dispatcher.register_type_handler(NodeType.ACTION, handler)
        assert dispatcher.get_type_handler(NodeType.ACTION) is not None

    def test_list_handlers(self, dispatcher: WorkflowDispatcher) -> None:
        dispatcher.register_handler("h1", lambda n, c: None)
        assert "h1" in dispatcher.list_handlers()

    @pytest.mark.asyncio
    async def test_dispatch(self, dispatcher: WorkflowDispatcher) -> None:
        async def handler(node: Any, ctx: Any) -> str:
            return "result"
        dispatcher.register_handler("test", handler)
        await dispatcher.start()
        ctx = WorkflowContext()
        node = _make_node(handler="test")
        result = await dispatcher.dispatch(node, ctx)
        assert result == "result"
        await dispatcher.stop()

    @pytest.mark.asyncio
    async def test_dispatch_no_handler(self, dispatcher: WorkflowDispatcher) -> None:
        await dispatcher.start()
        ctx = WorkflowContext()
        node = _make_node(handler="nonexistent")
        result = await dispatcher.dispatch(node, ctx)
        assert result["status"] == "skipped"
        await dispatcher.stop()

    @pytest.mark.asyncio
    async def test_dispatch_batch(self, dispatcher: WorkflowDispatcher) -> None:
        async def handler(node: Any, ctx: Any) -> str:
            return f"done-{node.node_id}"
        dispatcher.register_handler("test", handler)
        await dispatcher.start()
        ctx = WorkflowContext()
        nodes = [_make_node(node_id=f"n{i}", handler="test") for i in range(3)]
        results = await dispatcher.dispatch_batch(nodes, ctx)
        assert len(results) == 3
        await dispatcher.stop()

    def test_active_count(self, dispatcher: WorkflowDispatcher) -> None:
        assert dispatcher.active_count == 0


# ===================================================================
# SECTION 13 — Orchestrator
# ===================================================================

class TestWorkflowOrchestrator:
    @pytest_asyncio.fixture
    async def orchestrator(self) -> WorkflowOrchestrator:
        o = WorkflowFactory.create_orchestrator()
        await o.start()
        return o

    @pytest.mark.asyncio
    async def test_create_workflow(self, orchestrator: WorkflowOrchestrator) -> None:
        defn = _make_definition()
        result = await orchestrator.create_workflow(defn)
        assert result.id == "wf-1"

    @pytest.mark.asyncio
    async def test_update_workflow(self, orchestrator: WorkflowOrchestrator) -> None:
        await orchestrator.create_workflow(_make_definition())
        updated = await orchestrator.update_workflow("wf-1", {"name": "Updated"})
        assert updated is not None
        assert updated.name == "Updated"

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, orchestrator: WorkflowOrchestrator) -> None:
        result = await orchestrator.update_workflow("nope", {"name": "X"})
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_workflow(self, orchestrator: WorkflowOrchestrator) -> None:
        await orchestrator.create_workflow(_make_definition())
        assert await orchestrator.delete_workflow("wf-1") is True

    @pytest.mark.asyncio
    async def test_validate_workflow(self, orchestrator: WorkflowOrchestrator) -> None:
        defn = _make_definition()
        valid, errors = await orchestrator.validate_workflow(defn)
        assert valid is True

    @pytest.mark.asyncio
    async def test_compile_workflow(self, orchestrator: WorkflowOrchestrator) -> None:
        defn = _make_definition()
        defn.steps = []
        await orchestrator.create_workflow(defn)
        graph = await orchestrator.compile_workflow("wf-1")
        assert graph is not None

    @pytest.mark.asyncio
    async def test_compile_nonexistent(self, orchestrator: WorkflowOrchestrator) -> None:
        assert await orchestrator.compile_workflow("nope") is None

    @pytest.mark.asyncio
    async def test_execute_workflow(self, orchestrator: WorkflowOrchestrator) -> None:
        await orchestrator.create_workflow(_make_definition())
        execution = await orchestrator.execute_workflow("wf-1", {"input": "test"})
        assert execution.status.value == "COMPLETED"

    @pytest.mark.asyncio
    async def test_execute_nonexistent(self, orchestrator: WorkflowOrchestrator) -> None:
        with pytest.raises(ValueError, match="not found"):
            await orchestrator.execute_workflow("nope")

    @pytest.mark.asyncio
    async def test_clone_workflow(self, orchestrator: WorkflowOrchestrator) -> None:
        await orchestrator.create_workflow(_make_definition())
        cloned = await orchestrator.clone_workflow("wf-1")
        assert cloned is not None
        assert cloned.id != "wf-1"
        assert "copy" in cloned.name.lower()

    @pytest.mark.asyncio
    async def test_clone_nonexistent(self, orchestrator: WorkflowOrchestrator) -> None:
        assert await orchestrator.clone_workflow("nope") is None

    @pytest.mark.asyncio
    async def test_export_workflow(self, orchestrator: WorkflowOrchestrator) -> None:
        await orchestrator.create_workflow(_make_definition())
        data = await orchestrator.export_workflow("wf-1")
        assert data is not None
        assert data["name"] == "Test Workflow"

    @pytest.mark.asyncio
    async def test_export_nonexistent(self, orchestrator: WorkflowOrchestrator) -> None:
        assert await orchestrator.export_workflow("nope") is None

    @pytest.mark.asyncio
    async def test_import_workflow(self, orchestrator: WorkflowOrchestrator) -> None:
        data = {"name": "Imported", "description": "test", "tags": ["imported"]}
        defn = await orchestrator.import_workflow(data)
        assert defn.name == "Imported"

    @pytest.mark.asyncio
    async def test_get_workflow(self, orchestrator: WorkflowOrchestrator) -> None:
        await orchestrator.create_workflow(_make_definition())
        got = await orchestrator.get_workflow("wf-1")
        assert got is not None

    @pytest.mark.asyncio
    async def test_list_workflows(self, orchestrator: WorkflowOrchestrator) -> None:
        await orchestrator.create_workflow(_make_definition("wf-1"))
        await orchestrator.create_workflow(_make_definition("wf-2", "WF2"))
        defs = await orchestrator.list_workflows()
        assert len(defs) == 2

    @pytest.mark.asyncio
    async def test_get_statistics(self, orchestrator: WorkflowOrchestrator) -> None:
        stats = await orchestrator.get_statistics()
        assert "total_definitions" in stats
        assert "metrics" in stats

    def test_get_metrics_dict(self, orchestrator: WorkflowOrchestrator) -> None:
        d = orchestrator.get_metrics_dict()
        assert "workflows_created" in d

    def test_get_traces_dict(self, orchestrator: WorkflowOrchestrator) -> None:
        d = orchestrator.get_traces_dict()
        assert "traces" in d

    @pytest.mark.asyncio
    async def test_start_stop(self, orchestrator: WorkflowOrchestrator) -> None:
        assert orchestrator.lifecycle.state == WorkflowLifecycleState.RUNNING
        await orchestrator.stop()
        assert orchestrator.lifecycle.state == WorkflowLifecycleState.CANCELLED


# ===================================================================
# SECTION 14 — Factory
# ===================================================================

class TestWorkflowFactory:
    @pytest.mark.asyncio
    async def test_create_orchestrator(self) -> None:
        o = WorkflowFactory.create_orchestrator()
        assert o is not None
        assert o.persistence is not None
        assert o.dispatcher is not None
        assert o.metrics is not None
        assert o.tracer is not None

    @pytest.mark.asyncio
    async def test_create_with_components(self) -> None:
        components = WorkflowFactory.create_orchestrator_with_components()
        assert "orchestrator" in components
        assert "persistence" in components
        assert "compiler" in components
        assert "validator" in components
        assert "dispatcher" in components
        assert "metrics" in components
        assert "tracer" in components
        assert "lifecycle" in components


# ===================================================================
# SECTION 15 — ABCs
# ===================================================================

class TestABCs:
    def test_workflow_provider_is_abstract(self) -> None:
        assert hasattr(WorkflowProvider, "__abstractmethods__")

    def test_workflow_repository_is_abstract(self) -> None:
        assert hasattr(WorkflowRepositoryABC, "__abstractmethods__")

    def test_workflow_compiler_is_abstract(self) -> None:
        assert hasattr(WorkflowCompilerABC, "__abstractmethods__")

    def test_workflow_validator_is_abstract(self) -> None:
        assert hasattr(WorkflowValidatorABC, "__abstractmethods__")

    def test_workflow_dispatcher_is_abstract(self) -> None:
        assert hasattr(WorkflowDispatcherABC, "__abstractmethods__")

    def test_workflow_executor_is_abstract(self) -> None:
        assert hasattr(WorkflowExecutor, "__abstractmethods__")

    def test_step_handler_is_abstract(self) -> None:
        assert hasattr(StepHandler, "__abstractmethods__")

    def test_condition_evaluator_is_abstract(self) -> None:
        assert hasattr(ConditionEvaluator, "__abstractmethods__")

    def test_rollback_handler_is_abstract(self) -> None:
        assert hasattr(RollbackHandler, "__abstractmethods__")

    def test_cannot_instantiate_workflow_provider(self) -> None:
        with pytest.raises(TypeError):
            WorkflowProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_workflow_repository(self) -> None:
        with pytest.raises(TypeError):
            WorkflowRepositoryABC()  # type: ignore[abstract]

    def test_cannot_instantiate_workflow_compiler(self) -> None:
        with pytest.raises(TypeError):
            WorkflowCompilerABC()  # type: ignore[abstract]

    def test_cannot_instantiate_workflow_validator(self) -> None:
        with pytest.raises(TypeError):
            WorkflowValidatorABC()  # type: ignore[abstract]

    def test_cannot_instantiate_workflow_dispatcher(self) -> None:
        with pytest.raises(TypeError):
            WorkflowDispatcherABC()  # type: ignore[abstract]


# ===================================================================
# SECTION 16 — Templates
# ===================================================================

class TestTemplates:
    def test_chat_workflow(self) -> None:
        wf = create_chat_workflow()
        assert wf.name == "Chat Workflow"
        assert "chat" in wf.tags

    def test_research_workflow(self) -> None:
        wf = create_research_workflow()
        assert wf.name == "Research Workflow"

    def test_coding_workflow(self) -> None:
        wf = create_coding_workflow()
        assert wf.name == "Coding Workflow"

    def test_planning_workflow(self) -> None:
        wf = create_planning_workflow()
        assert wf.name == "Planning Workflow"

    def test_goal_execution_workflow(self) -> None:
        wf = create_goal_execution_workflow()
        assert wf.name == "Goal Execution Workflow"

    def test_task_automation_workflow(self) -> None:
        wf = create_task_automation_workflow()
        assert wf.name == "Task Automation Workflow"

    def test_rag_workflow(self) -> None:
        wf = create_rag_workflow()
        assert wf.name == "RAG Workflow"

    def test_multi_agent_workflow(self) -> None:
        wf = create_multi_agent_workflow()
        assert wf.name == "Multi-Agent Collaboration Workflow"

    def test_default_templates(self) -> None:
        assert len(DEFAULT_TEMPLATES) == 8

    def test_get_template(self) -> None:
        t = get_template("chat")
        assert t is not None
        assert t.name == "Chat Workflow"

    def test_get_template_nonexistent(self) -> None:
        assert get_template("nope") is None

    def test_list_templates(self) -> None:
        templates = list_templates()
        assert len(templates) == 8
        assert all("name" in t for t in templates)


# ===================================================================
# SECTION 17 — Schemas
# ===================================================================

class TestSchemas:
    def test_workflow_clone_request(self) -> None:
        req = WorkflowCloneRequest(name="Clone")
        assert req.name == "Clone"

    def test_workflow_import_request(self) -> None:
        req = WorkflowImportRequest(name="Imported", tags=["imported"])
        assert req.name == "Imported"

    def test_workflow_statistics_response(self) -> None:
        resp = WorkflowStatisticsResponse(total_definitions=5, total_executions=10)
        assert resp.total_definitions == 5

    def test_workflow_metrics_response(self) -> None:
        resp = WorkflowMetricsResponse(workflows_created=3)
        assert resp.workflows_created == 3

    def test_workflow_health_response(self) -> None:
        resp = WorkflowHealthResponse(status="ok", lifecycle_state="running")
        assert resp.status == "ok"

    def test_workflow_traces_response(self) -> None:
        resp = WorkflowTracesResponse(traces=[{"name": "test"}], total=1)
        assert resp.total == 1

    def test_workflow_template_response(self) -> None:
        resp = WorkflowTemplateResponse(name="chat", description="Chat", tags=["chat"])
        assert resp.name == "chat"

    def test_workflow_node_schema(self) -> None:
        node = WorkflowNodeSchema(node_id="n1", node_type="action", name="Test")
        assert node.node_id == "n1"

    def test_workflow_edge_schema(self) -> None:
        edge = WorkflowEdgeSchema(edge_id="e1", source_node_id="n1", target_node_id="n2")
        assert edge.source_node_id == "n1"

    def test_workflow_graph_request(self) -> None:
        req = WorkflowGraphRequest(
            nodes=[WorkflowNodeSchema(node_id="n1", name="N1")],
            edges=[WorkflowEdgeSchema(edge_id="e1", source_node_id="n1", target_node_id="n2")],
        )
        assert len(req.nodes) == 1


# ===================================================================
# SECTION 18 — Integration / End-to-End
# ===================================================================

class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_workflow_lifecycle(self) -> None:
        orchestrator = WorkflowFactory.create_orchestrator()
        await orchestrator.start()

        defn = _make_definition()
        await orchestrator.create_workflow(defn)

        execution = await orchestrator.execute_workflow("wf-1", {"data": "test"})
        assert execution.status.value == "COMPLETED"
        assert execution.input == {"data": "test"}

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_validate_compile_execute(self) -> None:
        orchestrator = WorkflowFactory.create_orchestrator()
        await orchestrator.start()

        defn = _make_definition()
        valid, _ = await orchestrator.validate_workflow(defn)
        assert valid is True

        await orchestrator.create_workflow(defn)
        graph = await orchestrator.compile_workflow("wf-1")
        assert graph is not None
        valid, _ = graph.is_valid_dag()
        assert valid is True

        execution = await orchestrator.execute_workflow("wf-1")
        assert execution.status.value == "COMPLETED"

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_clone_and_export(self) -> None:
        orchestrator = WorkflowFactory.create_orchestrator()
        await orchestrator.start()

        await orchestrator.create_workflow(_make_definition())
        cloned = await orchestrator.clone_workflow("wf-1")
        assert cloned is not None

        exported = await orchestrator.export_workflow(cloned.id)
        assert exported is not None
        assert exported["name"] == "Test Workflow (copy)"

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_import_workflow(self) -> None:
        orchestrator = WorkflowFactory.create_orchestrator()
        await orchestrator.start()

        data = {"name": "Imported WF", "description": "imported", "tags": ["imported"]}
        defn = await orchestrator.import_workflow(data)
        assert defn.name == "Imported WF"

        got = await orchestrator.get_workflow(defn.id)
        assert got is not None

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_graph_validation(self) -> None:
        graph = WorkflowGraph()
        graph.add_node(StartNode(node_id="start", name="Start"))
        graph.add_node(ActionNode(node_id="a1", name="Action", handler="h1"))
        graph.add_node(EndNode(node_id="end", name="End"))
        graph.add_edge(WorkflowEdge(edge_id="e1", source_node_id="start", target_node_id="a1"))
        graph.add_edge(WorkflowEdge(edge_id="e2", source_node_id="a1", target_node_id="end"))

        validator = WorkflowValidator()
        valid, errors = validator.validate_graph(graph)
        assert valid is True
        assert errors == []

    @pytest.mark.asyncio
    async def test_multiple_workflows(self) -> None:
        orchestrator = WorkflowFactory.create_orchestrator()
        await orchestrator.start()

        for i in range(5):
            await orchestrator.create_workflow(_make_definition(f"wf-{i}", f"WF {i}"))

        defs = await orchestrator.list_workflows()
        assert len(defs) == 5

        stats = await orchestrator.get_statistics()
        assert stats["total_definitions"] == 5

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_metrics_after_operations(self) -> None:
        WorkflowMetrics.reset_singleton()
        orchestrator = WorkflowFactory.create_orchestrator()
        await orchestrator.start()

        await orchestrator.create_workflow(_make_definition())
        metrics = orchestrator.get_metrics_dict()
        assert metrics["workflows_created"] == 1

        await orchestrator.shutdown()
        WorkflowMetrics.reset_singleton()

    @pytest.mark.asyncio
    async def test_traces_after_operations(self) -> None:
        orchestrator = WorkflowFactory.create_orchestrator()
        await orchestrator.start()

        await orchestrator.create_workflow(_make_definition())
        traces = orchestrator.get_traces_dict()
        assert traces["total"] >= 1

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        orchestrator = WorkflowFactory.create_orchestrator()
        await orchestrator.start()

        stats = await orchestrator.get_statistics()
        health = {
            "status": "ok" if orchestrator.lifecycle.state.value == "running" else "stopped",
            "lifecycle_state": orchestrator.lifecycle.state.value,
            "total_definitions": stats.get("total_definitions", 0),
            "total_executions": stats.get("total_executions", 0),
            "uptime_seconds": orchestrator.lifecycle.uptime_seconds,
        }
        assert health["status"] == "ok"
        assert health["lifecycle_state"] == "running"

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_dispatcher_integration(self) -> None:
        dispatcher = WorkflowDispatcher()
        await dispatcher.start()

        results: list[str] = []
        async def handler(node: Any, ctx: Any) -> str:
            results.append(node.node_id)
            return "ok"

        dispatcher.register_handler("test", handler)
        ctx = WorkflowContext()
        node = _make_node(handler="test")
        await dispatcher.dispatch(node, ctx)
        assert len(results) == 1
        assert results[0] == "n1"

        await dispatcher.stop()

    @pytest.mark.asyncio
    async def test_variable_store_integration(self) -> None:
        store = VariableStore()
        store.set_global("g", 1)
        store.set_workflow("w", 2)
        store.set_execution("e", 3)

        ctx = WorkflowContext(input_data={"input_key": "input_val"})
        ctx.variables.set_global("custom", "val")

        assert ctx.get_variable("input_key") == "input_val"
        assert ctx.get_variable("custom") == "val"
        assert store.get("g") == 1

    @pytest.mark.asyncio
    async def test_checkpoint_restore_flow(self) -> None:
        ctx = WorkflowContext()
        ctx.set_state("step", "running")
        ctx.save_checkpoint("n1")

        ctx.set_state("step", "completed")
        assert ctx.get_state("step") == "completed"

        last_cp = ctx.get_last_checkpoint()
        assert last_cp is not None
        ctx.restore_checkpoint(last_cp.checkpoint_id)
        assert ctx.get_state("step") == "running"

    @pytest.mark.asyncio
    async def test_lifecycle_transitions(self) -> None:
        lifecycle = WorkflowLifecycle()
        assert lifecycle.transition(WorkflowLifecycleState.INITIALIZED) is True
        assert lifecycle.transition(WorkflowLifecycleState.READY) is True
        assert lifecycle.transition(WorkflowLifecycleState.RUNNING) is True
        assert lifecycle.transition(WorkflowLifecycleState.WAITING) is True
        assert lifecycle.transition(WorkflowLifecycleState.RUNNING) is True
        assert lifecycle.transition(WorkflowLifecycleState.PAUSED) is True
        assert lifecycle.transition(WorkflowLifecycleState.RUNNING) is True
        assert lifecycle.transition(WorkflowLifecycleState.COMPLETED) is True

    @pytest.mark.asyncio
    async def test_graph_dag_with_multiple_paths(self) -> None:
        graph = WorkflowGraph()
        graph.add_node(StartNode(node_id="start", name="Start"))
        graph.add_node(ActionNode(node_id="a1", name="A1"))
        graph.add_node(ActionNode(node_id="a2", name="A2"))
        graph.add_node(ActionNode(node_id="a3", name="A3"))
        graph.add_node(EndNode(node_id="end", name="End"))
        graph.add_edge(WorkflowEdge(edge_id="e1", source_node_id="start", target_node_id="a1"))
        graph.add_edge(WorkflowEdge(edge_id="e2", source_node_id="start", target_node_id="a2"))
        graph.add_edge(WorkflowEdge(edge_id="e3", source_node_id="a1", target_node_id="a3"))
        graph.add_edge(WorkflowEdge(edge_id="e4", source_node_id="a2", target_node_id="a3"))
        graph.add_edge(WorkflowEdge(edge_id="e5", source_node_id="a3", target_node_id="end"))

        valid, msg = graph.is_valid_dag()
        assert valid is True
        paths = graph.get_execution_paths()
        assert len(paths) >= 1

    @pytest.mark.asyncio
    async def test_compiler_with_all_node_types(self) -> None:
        compiler = WorkflowCompiler()
        steps = [
            {"id": "s1", "name": "S1", "step_type": "TASK", "handler": "h1"},
            {"id": "s2", "name": "S2", "step_type": "TOOL", "handler": "h2"},
            {"id": "s3", "name": "S3", "step_type": "AGENT", "handler": "h3"},
            {"id": "s4", "name": "S4", "step_type": "GOAL", "handler": "h4"},
            {"id": "s5", "name": "S5", "step_type": "PARALLEL", "handler": "h5"},
            {"id": "s6", "name": "S6", "step_type": "LOOP", "handler": "h6"},
            {"id": "s7", "name": "S7", "step_type": "CONDITION", "handler": "h7"},
            {"id": "s8", "name": "S8", "step_type": "DECISION", "handler": "h8"},
            {"id": "s9", "name": "S9", "step_type": "MERGE", "handler": "h9"},
            {"id": "s10", "name": "S10", "step_type": "WAIT", "handler": "h10"},
            {"id": "s11", "name": "S11", "step_type": "DELAY", "handler": "h11"},
        ]
        graph = compiler.compile_from_steps(steps, "wf1")
        assert graph.node_count >= 13
        valid, _ = graph.is_valid_dag()
        assert valid is True
