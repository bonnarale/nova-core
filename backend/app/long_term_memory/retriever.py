"""Memory retrieval strategies for Long-Term Memory.

Supports retrieval by:
- Semantic similarity (via optional embedder)
- Tags
- Categories
- Recency
- Importance
- Entity relationships
- Source type
- User ID
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from app.long_term_memory.base import MemoryRetriever
from app.long_term_memory.models import LongTermMemory, RetrievalResult

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    async def embed(self, text: str) -> list[float]:
        ...


class SemanticMemoryRetriever(MemoryRetriever):
    """Retriever that uses semantic similarity via an embedder.

    Falls back to tag-based and recency-based retrieval if no embedder
    is available or if semantic search returns no results.
    """

    def __init__(
        self,
        store: Any,
        embedder: Embedder | None = None,
        default_limit: int = 10,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._default_limit = default_limit

    async def search(
        self,
        query: str,
        memory_type: str | None = None,
        user_id: str | None = None,
        limit: int | None = None,
    ) -> RetrievalResult:
        k = limit or self._default_limit

        if self._embedder and query.strip():
            semantic_results = await self._semantic_search(query, memory_type, k)
            if semantic_results:
                return RetrievalResult(
                    results=semantic_results,
                    total=len(semantic_results),
                    query=query,
                )

        return await self._fallback_search(query, memory_type, user_id, k)

    async def search_similar(
        self,
        content: str,
        memory_type: str | None = None,
        limit: int = 10,
        threshold: float = 0.75,
    ) -> RetrievalResult:
        if self._embedder and content.strip():
            results = await self._semantic_search(content, memory_type, limit, threshold)
            return RetrievalResult(results=results, total=len(results), query=content[:50])
        candidates = await self._store.list_by_type(
            memory_type or "knowledge", limit=limit
        )
        return RetrievalResult(results=candidates, total=len(candidates), query=content[:50])

    async def _semantic_search(
        self,
        query: str,
        memory_type: str | None = None,
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> list[LongTermMemory]:
        if not self._embedder:
            return []

        try:
            query_vec = await self._embedder.embed(query)
            if not query_vec:
                return []
        except Exception:
            logger.exception("Embedding failed during semantic search")
            return []

        candidates = await self._store.list_by_type(
            memory_type or "knowledge", status="active", limit=200
        )

        scored: list[tuple[LongTermMemory, float]] = []
        for mem in candidates:
            if not mem.embedding:
                continue
            sim = self._cosine_similarity(query_vec, mem.embedding)
            if sim >= threshold:
                scored.append((mem, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [mem for mem, _sim in scored[:top_k]]

    async def _fallback_search(
        self,
        query: str,
        memory_type: str | None = None,
        user_id: str | None = None,
        limit: int = 10,
    ) -> RetrievalResult:
        query_lower = query.lower()
        query_words = set(query_lower.split())

        candidates: list[LongTermMemory] = []
        if user_id:
            candidates = await self._store.list_by_user(
                user_id, memory_type=memory_type, limit=100
            )
        else:
            candidates = await self._store.list_by_type(
                memory_type or "knowledge", limit=100
            )

        scored: list[tuple[LongTermMemory, float]] = []
        for mem in candidates:
            mem_words = set((mem.content or "").lower().split())
            overlap = query_words & mem_words
            score = len(overlap) / max(len(query_words), 1)
            if mem.tags:
                tag_overlap = query_words & set(t.lower() for t in mem.tags)
                score += len(tag_overlap) * 0.5
            if score > 0:
                scored.append((mem, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = [mem for mem, _score in scored[:limit]]

        return RetrievalResult(results=results, total=len(results), query=query)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class StoreRetriever(MemoryRetriever):
    """Simple retriever that delegates directly to the store's query methods."""

    def __init__(self, store: Any, default_limit: int = 10) -> None:
        self._store = store
        self._default_limit = default_limit

    async def search(
        self,
        query: str,
        memory_type: str | None = None,
        user_id: str | None = None,
        limit: int | None = None,
    ) -> RetrievalResult:
        k = limit or self._default_limit
        if user_id:
            results = await self._store.list_by_user(
                user_id, memory_type=memory_type, limit=k
            )
        else:
            results = await self._store.list_by_type(
                memory_type or "knowledge", limit=k
            )
        return RetrievalResult(results=results, total=len(results), query=query)

    async def search_similar(
        self,
        content: str,
        memory_type: str | None = None,
        limit: int = 10,
        threshold: float = 0.75,
    ) -> RetrievalResult:
        results = await self._store.list_by_type(
            memory_type or "knowledge", limit=limit
        )
        return RetrievalResult(results=results, total=len(results), query=content[:50])
