"""Domain dataclasses for the Workflow Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    RETRYING = "RETRYING"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"


class StepType(str, Enum):
    TASK = "TASK"
    CONDITION = "CONDITION"
    PARALLEL = "PARALLEL"
    LOOP = "LOOP"
    SUB_WORKFLOW = "SUB_WORKFLOW"
    WAIT = "WAIT"
    DECISION = "DECISION"


class WorkflowEventType(str, Enum):
    CREATED = "CREATED"
    STARTED = "STARTED"
    STEP_STARTED = "STEP_STARTED"
    STEP_COMPLETED = "STEP_COMPLETED"
    STEP_FAILED = "STEP_FAILED"
    PAUSED = "PAUSED"
    RESUMED = "RESUMED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    RETRYING = "RETRYING"
    PROGRESS = "PROGRESS"
    WAITING = "WAITING"
    DECISION_REQUIRED = "DECISION_REQUIRED"


@dataclass
class RetryPolicy:
    max_retries: int = 3
    delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 60.0
    retryable_errors: list[str] = field(default_factory=list)


@dataclass
class TimeoutPolicy:
    step_timeout_seconds: float = 300.0
    workflow_timeout_seconds: float = 86400.0
    hard_timeout_seconds: float | None = None


@dataclass
class Condition:
    field: str = ""
    operator: str = "eq"
    value: Any = None


@dataclass
class WorkflowStep:
    id: str = ""
    name: str = ""
    step_type: StepType = StepType.TASK
    handler: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    retry_policy: RetryPolicy | None = None
    timeout_policy: TimeoutPolicy | None = None
    input_mapping: dict[str, str] = field(default_factory=dict)
    output_mapping: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "step_type": self.step_type.value,
            "handler": self.handler,
            "depends_on": self.depends_on,
            "config": self.config,
            "input_mapping": self.input_mapping,
            "output_mapping": self.output_mapping,
            "metadata": self.metadata,
        }


@dataclass
class ConditionStep(WorkflowStep):
    conditions: list[Condition] = field(default_factory=list)
    if_branch: list[WorkflowStep] = field(default_factory=list)
    else_branch: list[WorkflowStep] = field(default_factory=list)


@dataclass
class ParallelBranch:
    id: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    wait_for_all: bool = True


@dataclass
class ParallelStep(WorkflowStep):
    branches: list[ParallelBranch] = field(default_factory=list)


@dataclass
class LoopStep(WorkflowStep):
    loop_over: str = ""
    max_iterations: int = 10
    convergence_condition: Condition | None = None
    body: list[WorkflowStep] = field(default_factory=list)


@dataclass
class WorkflowDefinition:
    id: str = ""
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    steps: list[WorkflowStep] = field(default_factory=list)
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    timeout_policy: TimeoutPolicy | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [s.to_dict() for s in self.steps],
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowStepExecution:
    step_id: str = ""
    step_name: str = ""
    step_type: StepType = StepType.TASK
    status: StepStatus = StepStatus.PENDING
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    retry_count: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "step_type": self.step_type.value,
            "status": self.status.value,
            "error": self.error,
            "retry_count": self.retry_count,
            "duration_ms": self.duration_ms,
        }


@dataclass
class WorkflowExecution:
    id: str = ""
    workflow_id: str = ""
    workflow_name: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    current_step_id: str | None = None
    step_executions: list[WorkflowStepExecution] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: float = 0.0
    user_id: str | None = None
    session_id: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "error": self.error,
            "current_step_id": self.current_step_id,
            "input": self.input,
            "output": self.output,
            "step_count": len(self.step_executions),
            "steps": [s.to_dict() for s in self.step_executions],
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "user_id": self.user_id,
            "tags": self.tags,
        }


@dataclass
class WorkflowEvent:
    id: str = ""
    execution_id: str = ""
    event_type: WorkflowEventType = WorkflowEventType.CREATED
    step_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "event_type": self.event_type.value,
            "step_id": self.step_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }
