"""Pydantic schemas for the Vector Memory module."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# MemoryCategory
# ---------------------------------------------------------------------------

class MemoryCategory(str, Enum):
    CONVERSATION = "conversation"
    USER_PROFILE = "user_profile"
    KNOWLEDGE = "knowledge"
    LEARNED = "learned"
    GOAL = "goal"
    TASK = "task"
    PLAN = "plan"
    EXECUTION = "execution"
    AGENT = "agent"
    EXTERNAL = "external"


# ---------------------------------------------------------------------------
# VectorRecord
# ---------------------------------------------------------------------------

class VectorRecord(BaseModel):
    vector_id: str = Field(default="", description="Unique vector identifier")
    source_id: str = Field(default="")
    document_id: str = Field(default="")
    memory_type: MemoryCategory = Field(default=MemoryCategory.KNOWLEDGE)
    user_id: str = ""
    session_id: str = ""
    tags: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 1.0
    importance: float = 0.5
    embedding_provider: str = ""
    content: str = ""
    embedding: list[float] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    distance: float = 0.0


# ---------------------------------------------------------------------------
# VectorMemoryQuery
# ---------------------------------------------------------------------------

class VectorMemoryQuery(BaseModel):
    query: str = ""
    embedding: list[float] = Field(default_factory=list)
    top_k: int = 10
    threshold: Optional[float] = None
    memory_category: Optional[MemoryCategory] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    tags: Optional[list[str]] = None
    namespace: str = "default"


# ---------------------------------------------------------------------------
# VectorMemoryResult
# ---------------------------------------------------------------------------

class VectorMemoryResult(BaseModel):
    success: bool = True
    vector_id: str = ""
    message: str = ""
    record: Optional[VectorRecord] = None


# ---------------------------------------------------------------------------
# VectorMemorySearchResult
# ---------------------------------------------------------------------------

class VectorMemorySearchResult(BaseModel):
    results: list[VectorRecord] = Field(default_factory=list)
    total: int = 0
    query: str = ""
    time_taken_ms: float = 0.0


# ---------------------------------------------------------------------------
# VectorMemoryStatistics
# ---------------------------------------------------------------------------

class VectorMemoryStatistics(BaseModel):
    total_vectors: int = 0
    vectors_by_category: dict[str, int] = Field(default_factory=dict)
    total_searches: int = 0
    avg_retrieval_latency_ms: float = 0.0
    avg_indexing_latency_ms: float = 0.0
    avg_embedding_latency_ms: float = 0.0
    storage_usage_bytes: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    vectors_indexed: int = 0
    consolidations_run: int = 0


# ---------------------------------------------------------------------------
# VectorMemoryConfig
# ---------------------------------------------------------------------------

class VectorMemoryConfig(BaseModel):
    top_k: int = 10
    threshold: float = 0.0
    auto_consolidate: bool = True
    consolidation_interval: int = 100
    auto_index: bool = True
    embedding_dimension: int = 384
    namespace: str = "default"
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600


# ---------------------------------------------------------------------------
# VectorMemoryDocument
# ---------------------------------------------------------------------------

class VectorMemoryDocument(BaseModel):
    source_id: str = ""
    document_id: str = ""
    memory_type: MemoryCategory = MemoryCategory.EXTERNAL
    content: str = ""
    user_id: str = ""
    session_id: str = ""
    tags: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    importance: float = 0.5
    metadata: dict[str, Any] = Field(default_factory=dict)
