"""Pydantic schemas for the Workflow Engine API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConditionSchema(BaseModel):
    field: str = ""
    operator: str = "eq"
    value: Any = None


class RetryPolicySchema(BaseModel):
    max_retries: int = 3
    delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 60.0
    retryable_errors: list[str] = Field(default_factory=list)


class TimeoutPolicySchema(BaseModel):
    step_timeout_seconds: float = 300.0
    workflow_timeout_seconds: float = 86400.0
    hard_timeout_seconds: float | None = None


class WorkflowStepSchema(BaseModel):
    id: str
    name: str = ""
    step_type: str = "TASK"
    handler: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    retry_policy: RetryPolicySchema | None = None
    timeout_policy: TimeoutPolicySchema | None = None
    input_mapping: dict[str, str] = Field(default_factory=dict)
    output_mapping: dict[str, str] = Field(default_factory=dict)


class ParallelBranchSchema(BaseModel):
    id: str = ""
    steps: list[WorkflowStepSchema] = Field(default_factory=list)
    wait_for_all: bool = True


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    version: str = "1.0.0"
    steps: list[WorkflowStepSchema] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    version: str | None = None
    steps: list[WorkflowStepSchema] | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class WorkflowResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    steps: list[WorkflowStepSchema] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowStepExecutionSchema(BaseModel):
    step_id: str = ""
    step_name: str = ""
    step_type: str = "TASK"
    status: str = "PENDING"
    error: str | None = None
    retry_count: int = 0
    duration_ms: float = 0.0


class WorkflowExecutionCreate(BaseModel):
    workflow_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None
    session_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    workflow_name: str = ""
    status: str = "PENDING"
    error: str | None = None
    current_step_id: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    steps: list[WorkflowStepExecutionSchema] = Field(default_factory=list)
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: float = 0.0
    user_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowEventResponse(BaseModel):
    id: str
    execution_id: str
    event_type: str
    step_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str | None = None


class WorkflowExecutionAction(BaseModel):
    action: str  # pause, resume, cancel, retry


class WorkflowImportRequest(BaseModel):
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    steps: list[WorkflowStepSchema] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowCloneRequest(BaseModel):
    name: str | None = None


class WorkflowStatisticsResponse(BaseModel):
    total_definitions: int = 0
    total_executions: int = 0
    metrics: dict[str, Any] = Field(default_factory=dict)


class WorkflowMetricsResponse(BaseModel):
    workflows_created: int = 0
    workflows_executed: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    node_execution_count: int = 0
    average_execution_time_ms: float = 0.0
    retry_count: int = 0
    rollback_count: int = 0


class WorkflowHealthResponse(BaseModel):
    status: str = "ok"
    lifecycle_state: str = ""
    total_definitions: int = 0
    total_executions: int = 0
    uptime_seconds: float = 0.0


class WorkflowTracesResponse(BaseModel):
    traces: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class WorkflowTemplateResponse(BaseModel):
    name: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)


class WorkflowNodeSchema(BaseModel):
    node_id: str = ""
    node_type: str = "action"
    name: str = ""
    description: str = ""
    handler: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float | None = None
    retry_policy: dict[str, Any] | None = None


class WorkflowEdgeSchema(BaseModel):
    edge_id: str = ""
    source_node_id: str = ""
    target_node_id: str = ""
    edge_type: str = "normal"
    condition: dict[str, Any] | None = None
    label: str = ""


class WorkflowGraphRequest(BaseModel):
    nodes: list[WorkflowNodeSchema] = Field(default_factory=list)
    edges: list[WorkflowEdgeSchema] = Field(default_factory=list)
