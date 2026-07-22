"""RAG & Retrieval schemas — Pydantic models for API and internal data contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RetrievalMethod(str, Enum):
    VECTOR = "vector"
    HYBRID = "hybrid"
    KEYWORD = "keyword"
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"


class ChunkStrategy(str, Enum):
    FIXED = "fixed"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"
    MARKDOWN = "markdown"
    CODE = "code"


class RerankStrategy(str, Enum):
    SIMILARITY = "similarity"
    CROSS_ENCODER = "cross_encoder"
    HYBRID_SCORE = "hybrid_score"
    RECENCY = "recency"
    IMPORTANCE = "importance"


class FilterOperator(str, Enum):
    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    NIN = "nin"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETED = "deleted"


class RetrievalStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    NO_RESULTS = "no_results"
    ERROR = "error"


# ── Request / Response models ────────────────────────────────────────


class ChunkMetadata(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str = ""
    source_id: str = ""
    title: str = ""
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 0
    token_count: int = 0
    strategy: ChunkStrategy = ChunkStrategy.FIXED
    tags: list[str] = Field(default_factory=list)
    source: str = ""
    author: str = ""
    category: str = ""
    language: str = "en"
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str = ""
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)
    embedding: Optional[list[float]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata.model_dump(),
            "embedding": self.embedding,
        }


class Citation(BaseModel):
    source_id: str = ""
    document_id: str = ""
    title: str = ""
    chunk_id: str = ""
    relevance_score: float = 0.0
    retrieval_method: RetrievalMethod = RetrievalMethod.VECTOR
    snippet: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    chunk: Chunk
    score: float = 0.0
    retrieval_method: RetrievalMethod = RetrievalMethod.VECTOR
    citation: Optional[Citation] = None
    rerank_score: Optional[float] = None


class QueryRewrite(BaseModel):
    original_query: str = ""
    rewritten_query: str = ""
    expansion_terms: list[str] = Field(default_factory=list)
    strategy: str = "none"


class FilterCondition(BaseModel):
    field: str = ""
    operator: FilterOperator = FilterOperator.EQ
    value: Any = None


class RetrievalQuery(BaseModel):
    query: str = ""
    rewritten_query: Optional[str] = None
    top_k: int = 10
    threshold: float = 0.0
    filters: list[FilterCondition] = Field(default_factory=list)
    retrieval_method: RetrievalMethod = RetrievalMethod.HYBRID
    rerank_strategy: RerankStrategy = RerankStrategy.SIMILARITY
    tags: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    include_embeddings: bool = False
    include_metadata: bool = True
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    query: str = ""
    rewritten_query: Optional[str] = None
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    total_chunks: int = 0
    status: RetrievalStatus = RetrievalStatus.SUCCESS
    latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextPackage(BaseModel):
    query: str = ""
    rewritten_query: Optional[str] = None
    context_text: str = ""
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    user_context: dict[str, Any] = Field(default_factory=dict)
    conversation_context: list[dict[str, str]] = Field(default_factory=list)
    goal_context: list[dict[str, Any]] = Field(default_factory=list)
    task_context: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_context: list[dict[str, Any]] = Field(default_factory=list)
    execution_context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndexDocument(BaseModel):
    document_id: str = Field(default_factory=lambda: str(uuid4()))
    content: str = ""
    title: str = ""
    source: str = ""
    author: str = ""
    category: str = ""
    language: str = "en"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_strategy: ChunkStrategy = ChunkStrategy.RECURSIVE
    chunk_size: int = 512
    chunk_overlap: int = 50


class IndexResult(BaseModel):
    document_id: str = ""
    chunks_created: int = 0
    chunks_indexed: int = 0
    status: DocumentStatus = DocumentStatus.INDEXED
    latency_ms: float = 0.0
    error: Optional[str] = None


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    retrieval_method: RetrievalMethod = RetrievalMethod.HYBRID
    rerank_strategy: RerankStrategy = RerankStrategy.SIMILARITY
    filters: list[FilterCondition] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    include_citations: bool = True
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class RAGQueryResponse(BaseModel):
    query: str = ""
    context: ContextPackage = Field(default_factory=ContextPackage)
    citations: list[Citation] = Field(default_factory=list)
    status: RetrievalStatus = RetrievalStatus.SUCCESS
    latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    retrieval_method: RetrievalMethod = RetrievalMethod.HYBRID
    filters: list[FilterCondition] = Field(default_factory=list)


class RAGRetrieveResponse(BaseModel):
    query: str = ""
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    total_chunks: int = 0
    status: RetrievalStatus = RetrievalStatus.SUCCESS
    latency_ms: float = 0.0


class RAGIndexRequest(BaseModel):
    documents: list[IndexDocument] = Field(..., min_length=1)


class RAGIndexResponse(BaseModel):
    results: list[IndexResult] = Field(default_factory=list)
    total_documents: int = 0
    total_chunks: int = 0
    latency_ms: float = 0.0


class RAGReindexRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    reindex_all: bool = False


class RAGHealthResponse(BaseModel):
    status: str = "ok"
    lifecycle_state: str = ""
    repository_status: str = ""
    embedding_provider: str = ""
    document_count: int = 0
    chunk_count: int = 0
    latency_ms: float = 0.0


class RAGMetricsResponse(BaseModel):
    total_queries: int = 0
    average_latency_ms: float = 0.0
    average_retrieval_latency_ms: float = 0.0
    average_rerank_latency_ms: float = 0.0
    average_embedding_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    total_documents: int = 0
    total_chunks: int = 0


class RAGTracesResponse(BaseModel):
    traces: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class RAGStatisticsResponse(BaseModel):
    document_count: int = 0
    chunk_count: int = 0
    source_counts: dict[str, int] = Field(default_factory=dict)
    category_counts: dict[str, int] = Field(default_factory=dict)
    average_chunk_size: float = 0.0
    index_size_bytes: int = 0
