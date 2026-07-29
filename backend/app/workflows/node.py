"""Workflow nodes — DAG node types for workflow graphs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    START = "start"
    END = "end"
    ACTION = "action"
    TOOL = "tool"
    AGENT = "agent"
    TASK = "task"
    GOAL = "goal"
    DECISION = "decision"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    MERGE = "merge"
    WAIT = "wait"
    DELAY = "delay"
    EVENT = "event"
    HUMAN_APPROVAL = "human_approval"
    SUBWORKFLOW = "subworkflow"


class NodeStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"
    BLOCKED = "blocked"


@dataclass
class WorkflowNode:
    node_id: str = ""
    node_type: NodeType = NodeType.ACTION
    name: str = ""
    description: str = ""
    handler: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    input_mapping: dict[str, str] = field(default_factory=dict)
    output_mapping: dict[str, str] = field(default_factory=dict)
    timeout_seconds: float | None = None
    retry_policy: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "description": self.description,
            "handler": self.handler,
            "config": self.config,
            "timeout_seconds": self.timeout_seconds,
            "retry_policy": self.retry_policy,
            "metadata": self.metadata,
            "status": self.status.value,
        }


@dataclass
class StartNode(WorkflowNode):
    node_type: NodeType = NodeType.START


@dataclass
class EndNode(WorkflowNode):
    node_type: NodeType = NodeType.END


@dataclass
class ActionNode(WorkflowNode):
    node_type: NodeType = NodeType.ACTION


@dataclass
class ToolNode(WorkflowNode):
    node_type: NodeType = NodeType.TOOL
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentNode(WorkflowNode):
    node_type: NodeType = NodeType.AGENT
    agent_id: str = ""
    prompt: str = ""


@dataclass
class TaskNode(WorkflowNode):
    node_type: NodeType = NodeType.TASK
    task_type: str = ""


@dataclass
class GoalNode(WorkflowNode):
    node_type: NodeType = NodeType.GOAL
    goal_id: str = ""


@dataclass
class DecisionNode(WorkflowNode):
    node_type: NodeType = NodeType.DECISION
    conditions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ConditionNode(WorkflowNode):
    node_type: NodeType = NodeType.CONDITION
    condition: dict[str, Any] = field(default_factory=dict)
    true_branch: str = ""
    false_branch: str = ""


@dataclass
class LoopNode(WorkflowNode):
    node_type: NodeType = NodeType.LOOP
    loop_variable: str = ""
    max_iterations: int = 10
    body_nodes: list[str] = field(default_factory=list)
    convergence_condition: dict[str, Any] | None = None


@dataclass
class ParallelNode(WorkflowNode):
    node_type: NodeType = NodeType.PARALLEL
    branch_node_ids: list[list[str]] = field(default_factory=list)
    wait_for_all: bool = True


@dataclass
class MergeNode(WorkflowNode):
    node_type: NodeType = NodeType.MERGE
    merge_strategy: str = "all"


@dataclass
class WaitNode(WorkflowNode):
    node_type: NodeType = NodeType.WAIT
    wait_for_event: str = ""
    timeout_seconds: float | None = None


@dataclass
class DelayNode(WorkflowNode):
    node_type: NodeType = NodeType.DELAY
    delay_seconds: float = 0.0


@dataclass
class EventNode(WorkflowNode):
    node_type: NodeType = NodeType.EVENT
    event_type: str = ""
    event_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class HumanApprovalNode(WorkflowNode):
    node_type: NodeType = NodeType.HUMAN_APPROVAL
    approvers: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class SubworkflowNode(WorkflowNode):
    node_type: NodeType = NodeType.SUBWORKFLOW
    subworkflow_id: str = ""
    subworkflow_input: dict[str, Any] = field(default_factory=dict)
