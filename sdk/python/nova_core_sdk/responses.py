from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    success: bool = True
    data: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    request_id: str = ""
    timestamp: float = 0.0


class PaginatedResponse(BaseModel):
    success: bool = True
    data: list[Any] = Field(default_factory=list)
    pagination: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class PaginationInfo(BaseModel):
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0
    has_next: bool = False
    has_prev: bool = False
    next_cursor: str | None = None
    prev_cursor: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"


class ChatResponse(BaseModel):
    response: dict[str, Any] = Field(default_factory=dict)
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    cache_hit: bool = False
    tokens_input: int = 0
    tokens_output: int = 0


class AgentResponse(BaseModel):
    id: str = ""
    name: str = ""
    role: str = ""
    description: str = ""
    status: str = "active"
    system_prompt: str = ""
    allowed_tools: list[str] = Field(default_factory=list)
    memory_scope: str = "session"
    permissions: dict[str, Any] = Field(default_factory=dict)
    supported_models: list[str] = Field(default_factory=list)


class GoalResponse(BaseModel):
    id: str = ""
    user_id: str = ""
    title: str = ""
    description: str = ""
    status: str = "active"
    priority: int = 3
    progress: int = 0


class TaskResponse(BaseModel):
    id: str = ""
    goal: str = ""
    status: str = "CREATED"
    current_step: int = 0
    plan: dict[str, Any] = Field(default_factory=dict)
    steps: list[Any] = Field(default_factory=list)
    assigned_agent: str | None = None


class WorkflowResponse(BaseModel):
    id: str = ""
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    steps: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class WorkflowExecutionResponse(BaseModel):
    id: str = ""
    workflow_id: str = ""
    workflow_name: str = ""
    status: str = "PENDING"
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)


class JobResponse(BaseModel):
    id: str = ""
    name: str = ""
    handler: str = ""
    schedule: str = ""
    status: str = "pending"
    enabled: bool = True


class EventResponse(BaseModel):
    id: str = ""
    event_type: str = ""
    source: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class EntityResponse(BaseModel):
    id: str = ""
    type: str = ""
    name: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    status: str = "ACTIVE"
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class RelationshipResponse(BaseModel):
    id: str = ""
    source_id: str = ""
    target_id: str = ""
    type: str = ""
    weight: float = 1.0
    status: str = "ACTIVE"


class ToolResponse(BaseModel):
    id: str = ""
    name: str = ""
    description: str = ""
    category: str = "general"
    status: str = "active"


class PluginResponse(BaseModel):
    id: str = ""
    name: str = ""
    version: str = ""
    status: str = "inactive"
    plugin_type: str = ""


class RAGQueryResponse(BaseModel):
    query: str = ""
    context_text: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
    chunks_count: int = 0
    latency_ms: float = 0.0


class RAGRetrieveResponse(BaseModel):
    query: str = ""
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    total_chunks: int = 0
    latency_ms: float = 0.0


class RAGIndexResponse(BaseModel):
    document_id: str = ""
    chunks_created: int = 0
    status: str = "indexed"
    latency_ms: float = 0.0


class VectorMemorySearchResult(BaseModel):
    results: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class LearningSessionResponse(BaseModel):
    artifacts_created: int = 0
    artifacts_updated: int = 0
    session_id: str = ""


class ArtifactListResponse(BaseModel):
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
