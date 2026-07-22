"""Vector Memory API routes."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.vector_memory.schemas import (
    MemoryCategory,
    VectorMemoryConfig,
    VectorMemoryDocument,
    VectorMemoryQuery,
    VectorMemoryResult,
    VectorMemorySearchResult,
    VectorMemoryStatistics,
    VectorRecord,
)

router = APIRouter(prefix="/vector-memory", tags=["vector-memory"])


async def _get_engine() -> Any:
    from app.main import app_state
    engine = app_state.get("vector_memory_engine")
    if engine is None:
        raise HTTPException(status_code=503, detail="VectorMemoryEngine not initialized")
    return engine


@router.post("/store", response_model=VectorMemoryResult)
async def store_vector(
    record: VectorRecord,
    engine: Any = Depends(_get_engine),
) -> VectorMemoryResult:
    return await engine.store(record)


@router.post("/search", response_model=VectorMemorySearchResult)
async def search_vectors(
    query: VectorMemoryQuery,
    engine: Any = Depends(_get_engine),
) -> VectorMemorySearchResult:
    return await engine.search(query)


@router.post("/similarity", response_model=VectorMemorySearchResult)
async def similarity_search(
    embedding: list[float],
    top_k: int = 10,
    threshold: Optional[float] = None,
    memory_category: Optional[MemoryCategory] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tags: Optional[list[str]] = None,
    engine: Any = Depends(_get_engine),
) -> VectorMemorySearchResult:
    return await engine.similarity_search(
        embedding=embedding,
        top_k=top_k,
        threshold=threshold,
        memory_category=memory_category,
        user_id=user_id,
        session_id=session_id,
        tags=tags,
    )


@router.post("/consolidate")
async def consolidate_vectors(
    engine: Any = Depends(_get_engine),
) -> dict[str, Any]:
    return await engine.consolidate()


@router.post("/reindex")
async def reindex_vectors(
    vector_ids: Optional[list[str]] = None,
    reindex_all: bool = False,
    engine: Any = Depends(_get_engine),
) -> dict[str, Any]:
    return await engine.reindex(vector_ids=vector_ids, reindex_all=reindex_all)


@router.delete("/{vector_id}")
async def delete_vector(
    vector_id: str,
    engine: Any = Depends(_get_engine),
) -> dict[str, Any]:
    deleted = await engine.delete(vector_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Vector {vector_id} not found")
    return {"success": True, "vector_id": vector_id}


@router.get("/statistics", response_model=VectorMemoryStatistics)
async def get_statistics(
    engine: Any = Depends(_get_engine),
) -> VectorMemoryStatistics:
    return await engine.get_statistics()


@router.get("/health")
async def health_check(
    engine: Any = Depends(_get_engine),
) -> dict[str, Any]:
    return await engine.health()


@router.get("/metrics")
async def get_metrics(
    engine: Any = Depends(_get_engine),
) -> dict[str, Any]:
    return engine.get_metrics_summary()


@router.get("/traces")
async def get_traces(
    limit: int = 100,
    engine: Any = Depends(_get_engine),
) -> list[dict[str, Any]]:
    return engine.get_traces(limit=limit)
