"""Pydantic schemas for Learning Engine API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractKnowledgeRequest(BaseModel):
    """Request to extract knowledge from a completed execution."""

    execution_id: str = Field(min_length=1)
    task_id: str | None = None
    execution_data: dict = Field(default_factory=dict)
    task_data: dict | None = None
    user_id: str | None = None
    agent_id: str | None = None


class ArtifactResponse(BaseModel):
    """Response schema for a single knowledge artifact."""

    id: str
    artifact_type: str
    content: str
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
    source_execution_id: str | None = None
    source_task_id: str | None = None
    user_id: str | None = None
    agent_id: str | None = None
    confidence: float = 0.0
    importance_score: float = 0.0
    access_count: int = 0
    metadata: dict = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class ArtifactListResponse(BaseModel):
    """Response for a list of artifacts."""

    artifacts: list[ArtifactResponse] = Field(default_factory=list)
    total: int = 0


class SearchLearningRequest(BaseModel):
    """Request to search for learned knowledge."""

    query: str = Field(min_length=1)
    user_id: str | None = None
    artifact_type: str | None = None
    tags: list[str] | None = None
    limit: int = Field(default=10, ge=1, le=100)


class LearningEventResponse(BaseModel):
    """Response for a learning event."""

    event_type: str
    payload: dict = Field(default_factory=dict)


class LearningSessionResponse(BaseModel):
    """Response for a learning session."""

    session_id: str
    execution_id: str | None = None
    task_id: str | None = None
    user_id: str | None = None
    artifacts_extracted: int = 0
    artifacts_stored: int = 0
    consolidations_run: int = 0
    events: list[LearningEventResponse] = Field(default_factory=list)
    status: str = "pending"
    error: str | None = None


class ConsolidateRequest(BaseModel):
    """Request to consolidate knowledge artifacts."""

    user_id: str | None = None
    artifact_type: str | None = None
    tags: list[str] | None = None


class LearningStatsResponse(BaseModel):
    """Response for learning statistics."""

    total_artifacts: int = 0
    artifacts_by_type: dict[str, int] = Field(default_factory=dict)
    total_sessions: int = 0


class ArtifactUpdateRequest(BaseModel):
    """Request to update a knowledge artifact."""

    content: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    importance_score: float | None = None
