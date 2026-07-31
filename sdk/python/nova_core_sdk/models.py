from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str


class ChatRequestModel(BaseModel):
    model: str
    messages: list[Message]
    provider: str | None = None
    agent_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    use_cache: bool = True
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False


class ChatResponseModel(BaseModel):
    response: dict[str, Any] = Field(default_factory=dict)
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    cache_hit: bool = False
    tokens_input: int = 0
    tokens_output: int = 0


class CreateAgentRequest(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=100)
    description: str = ""
    system_prompt: str = ""
    allowed_tools: list[str] = Field(default_factory=list)
    memory_scope: str = "session"
    permissions: dict[str, Any] = Field(default_factory=dict)
    supported_models: list[str] = Field(default_factory=list)


class UpdateAgentRequest(BaseModel):
    name: str | None = None
    role: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    allowed_tools: list[str] | None = None
    memory_scope: str | None = None
    permissions: dict[str, Any] | None = None
    supported_models: list[str] | None = None
    status: str | None = None


class DispatchRequest(BaseModel):
    task: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    timeout: float | None = None


class CoordinateRequest(BaseModel):
    steps: list[dict[str, Any]]
    pattern: str = "sequential"
    aggregation_agent: str | None = None


class ExecuteRequest(BaseModel):
    task: str
    agent_id: str
    session_id: str | None = None
    user_id: str | None = None


class CreateGoalRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: int = Field(default=3, ge=1, le=5)


class UpdateGoalRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: int | None = None
    progress: int | None = None
    block_reason: str | None = None


class CreateTaskRequest(BaseModel):
    goal: str = Field(min_length=1)
    plan: dict[str, Any] | None = None
    steps: list[Any] | None = None
    dependencies: list[str] | None = None
    assigned_agent: str | None = None


class UpdateTaskRequest(BaseModel):
    status: str | None = None
    current_step: int | None = None
    plan: dict[str, Any] | None = None
    steps: list[Any] | None = None
    artifacts: dict[str, Any] | None = None
    assigned_agent: str | None = None


class AdvanceStepRequest(BaseModel):
    artifacts: dict[str, Any] | None = None


class RAGQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.0, ge=0, le=1)
    filters: list[dict[str, Any]] = Field(default_factory=list)
    user_id: str | None = None
    session_id: str | None = None


class RAGRetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = 10
    threshold: float = 0.0


class RAGIndexDocRequest(BaseModel):
    content: str = Field(min_length=1)
    title: str = ""
    source: str = ""
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    chunk_size: int = 512
    chunk_overlap: int = 50
    document_id: str | None = None


class RAGReindexRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    reindex_all: bool = False


class RegisterToolRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    category: str = "general"
    policy: str = "immediate"
    permission_level: str = "read"
    timeout: float = 30.0
    retries: int = 0


class ExecuteToolRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)
    agent_id: str = ""
    user_id: str = ""
    timeout: float | None = None
    retries: int | None = None


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    version: str = "1.0.0"
    steps: list[dict[str, Any]] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowExecutionCreate(BaseModel):
    workflow_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None
    session_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowExecutionAction(BaseModel):
    action: str = Field(pattern="^(pause|resume|cancel|retry)$")


class CreateJobRequest(BaseModel):
    name: str
    handler: str = ""
    schedule: str = ""
    params: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class PublishEventRequest(BaseModel):
    event_type: str
    source: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    user_id: str | None = None


class EntityCreate(BaseModel):
    type: str
    name: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    source: str = "manual"
    confidence: float = 1.0


class EntityUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    aliases: list[str] | None = None
    tags: list[str] | None = None
    properties: dict[str, Any] | None = None
    confidence: float | None = None


class RelationshipCreate(BaseModel):
    source_id: str
    target_id: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)
    weight: float = 1.0
    source: str = "manual"
    confidence: float = 1.0


class VectorRecord(BaseModel):
    content: str
    embedding: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorMemoryQuery(BaseModel):
    query: str
    top_k: int = 10
    threshold: float = 0.0
    filters: dict[str, Any] = Field(default_factory=dict)


class RegisterPluginRequest(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    plugin_type: str = "extension"
    config: dict[str, Any] = Field(default_factory=dict)


class ExecutePluginRequest(BaseModel):
    operation: str
    params: dict[str, Any] = Field(default_factory=dict)


class ExtractKnowledgeRequest(BaseModel):
    execution_id: str
    session_id: str = ""
    user_id: str = ""


class SearchLearningRequest(BaseModel):
    query: str
    limit: int = 10
    artifact_type: str | None = None


class ConsolidateRequest(BaseModel):
    artifact_ids: list[str]


class CreateAgentRequestModel(BaseModel):
    name: str
    owner_id: str = ""


class CreateWorkspaceRequest(BaseModel):
    name: str
    org_id: str = ""


class CreateTeamRequest(BaseModel):
    name: str
    org_id: str = ""


class CreateRoleRequest(BaseModel):
    name: str
    permissions: list[str] = Field(default_factory=list)


class CreatePolicyRequest(BaseModel):
    name: str
    policy_type: str
    rules: list[dict[str, Any]] = Field(default_factory=list)
