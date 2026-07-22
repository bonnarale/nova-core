"""Pydantic schemas for Long-Term Memory API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    memory_type: str = Field(default="knowledge")
    source: str = Field(default="system")
    source_id: str | None = None
    user_id: str | None = None
    project_id: str | None = None
    agent_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    importance_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    content: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    categories: list[str] | None = None
    entities: list[str] | None = None
    importance_score: float | None = None
    metadata: dict[str, Any] | None = None


class MemoryResponse(BaseModel):
    id: str
    memory_type: str
    content: str
    summary: str | None
    tags: list[str]
    categories: list[str]
    entities: list[str]
    importance_score: float
    status: str
    linked_memory_ids: list[str]
    source: str
    source_id: str | None
    user_id: str | None
    project_id: str | None
    agent_id: str | None
    access_count: int
    metadata: dict[str, Any]
    created_at: str
    accessed_at: str
    updated_at: str
    archived_at: str | None


class MemorySearchResult(BaseModel):
    results: list[MemoryResponse]
    total: int
    query: str


class ConsolidateRequest(BaseModel):
    user_id: str | None = None
    project_id: str | None = None


class ConsolidateResponse(BaseModel):
    created: list[str]
    duplicates_skipped: int
    links_created: int


class LifecycleResponse(BaseModel):
    aged: int
    archived: int
    purged: int


class StatsResponse(BaseModel):
    counts_by_status: dict[str, int]
