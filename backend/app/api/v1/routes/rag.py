"""RAG API routes — REST endpoints for the RAG system."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/rag", tags=["rag"])


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    filters: list[dict[str, Any]] = Field(default_factory=list)
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class RAGQueryResponse(BaseModel):
    query: str = ""
    context_text: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
    chunks_count: int = 0
    latency_ms: float = 0.0


class RAGRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.0, ge=0.0, le=1.0)


class RAGRetrieveResponse(BaseModel):
    query: str = ""
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    total_chunks: int = 0
    latency_ms: float = 0.0


class RAGIndexDocRequest(BaseModel):
    document_id: Optional[str] = None
    content: str = Field(..., min_length=1)
    title: str = ""
    source: str = ""
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    chunk_size: int = 512
    chunk_overlap: int = 50


class RAGIndexResponse(BaseModel):
    document_id: str = ""
    chunks_created: int = 0
    status: str = "indexed"
    latency_ms: float = 0.0


class RAGReindexRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    reindex_all: bool = False


class RAGHealthResponse(BaseModel):
    status: str = "ok"
    lifecycle_state: str = ""
    document_count: int = 0
    chunk_count: int = 0


class RAGMetricsResponse(BaseModel):
    total_queries: int = 0
    average_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    total_documents: int = 0
    total_chunks: int = 0


class RAGTracesResponse(BaseModel):
    traces: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class RAGStatisticsResponse(BaseModel):
    document_count: int = 0
    chunk_count: int = 0
    source_counts: dict[str, int] = Field(default_factory=dict)


def _get_rag_engine() -> Any:
    from app.main import app_state
    engine = app_state.get("rag_engine")
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not initialized")
    return engine


@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest) -> RAGQueryResponse:
    engine = _get_rag_engine()
    from app.rag.schemas import RetrievalQuery, FilterCondition, FilterOperator
    filters = [FilterCondition(field=f.get("field", ""), operator=FilterOperator(f.get("operator", "eq")), value=f.get("value")) for f in request.filters]
    req = RetrievalQuery(query=request.query, top_k=request.top_k, threshold=request.threshold, filters=filters)
    context = await engine.query(req, user_context={"user_id": request.user_id} if request.user_id else None)
    return RAGQueryResponse(
        query=request.query,
        context_text=context.context_text,
        citations=[c.model_dump() for c in context.citations],
        chunks_count=len(context.retrieved_chunks),
    )


@router.post("/retrieve", response_model=RAGRetrieveResponse)
async def rag_retrieve(request: RAGRetrieveRequest) -> RAGRetrieveResponse:
    engine = _get_rag_engine()
    result = await engine.retrieve(request.query, request.top_k, request.threshold)
    return RAGRetrieveResponse(
        query=request.query,
        chunks=[rc.model_dump() for rc in result.chunks],
        total_chunks=result.total_chunks,
        latency_ms=result.latency_ms,
    )


@router.post("/index", response_model=RAGIndexResponse)
async def rag_index(request: RAGIndexDocRequest) -> RAGIndexResponse:
    engine = _get_rag_engine()
    from app.rag.schemas import IndexDocument, ChunkStrategy
    from uuid import uuid4
    doc = IndexDocument(
        document_id=request.document_id or str(uuid4()),
        content=request.content,
        title=request.title,
        source=request.source,
        category=request.category,
        tags=request.tags,
        chunk_strategy=ChunkStrategy.RECURSIVE,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
    )
    result = await engine.index_document(doc)
    return RAGIndexResponse(
        document_id=result.document_id,
        chunks_created=result.chunks_created,
        status=result.status.value,
        latency_ms=result.latency_ms,
    )


@router.post("/reindex")
async def rag_reindex(request: RAGReindexRequest) -> dict[str, Any]:
    engine = _get_rag_engine()
    results = await engine.reindex(request.document_ids, request.reindex_all)
    return {"reindexed": len(results)}


@router.get("/health", response_model=RAGHealthResponse)
async def rag_health() -> RAGHealthResponse:
    engine = _get_rag_engine()
    health = await engine.health()
    return RAGHealthResponse(
        status=health.get("status", "unknown"),
        lifecycle_state=health.get("lifecycle_state", ""),
        document_count=health.get("document_count", 0),
        chunk_count=health.get("chunk_count", 0),
    )


@router.get("/metrics", response_model=RAGMetricsResponse)
async def rag_metrics() -> RAGMetricsResponse:
    engine = _get_rag_engine()
    summary = engine.get_metrics_summary()
    return RAGMetricsResponse(**summary)


@router.get("/traces", response_model=RAGTracesResponse)
async def rag_traces(limit: int = 100) -> RAGTracesResponse:
    engine = _get_rag_engine()
    traces = engine.get_traces(limit)
    return RAGTracesResponse(traces=traces, total=len(traces))


@router.get("/statistics", response_model=RAGStatisticsResponse)
async def rag_statistics() -> RAGStatisticsResponse:
    engine = _get_rag_engine()
    stats = await engine.get_statistics()
    return RAGStatisticsResponse(**stats)
