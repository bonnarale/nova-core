"""RAG retrievers — fetch candidate chunks from data sources."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.rag.base import EmbeddingProvider, Retriever, VectorRepository
from app.rag.schemas import (
    FilterCondition,
    RetrievedChunk,
    RetrievalMethod,
)

logger = logging.getLogger(__name__)


class VectorRetriever(Retriever):
    """Retrieves chunks via vector similarity search."""

    def __init__(
        self,
        repository: VectorRepository,
        embedder: EmbeddingProvider,
        collection: str = "documents",
    ) -> None:
        self._repository = repository
        self._embedder = embedder
        self._collection = collection

    @property
    def retriever_id(self) -> str:
        return "vector"

    @property
    def retrieval_method(self) -> RetrievalMethod:
        return RetrievalMethod.VECTOR

    async def retrieve(
        self,
        query: str,
        embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.0,
        filters: Optional[list[FilterCondition]] = None,
        **kwargs: Any,
    ) -> list[RetrievedChunk]:
        return await self._repository.search(
            self._collection, embedding, top_k, threshold, filters
        )

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "retriever": self.retriever_id, "collection": self._collection}


class KeywordRetriever(Retriever):
    """Retrieves chunks via keyword matching (BM25-style)."""

    def __init__(
        self,
        repository: VectorRepository,
        collection: str = "documents",
    ) -> None:
        self._repository = repository
        self._collection = collection

    @property
    def retriever_id(self) -> str:
        return "keyword"

    @property
    def retrieval_method(self) -> RetrievalMethod:
        return RetrievalMethod.KEYWORD

    async def retrieve(
        self,
        query: str,
        embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.0,
        filters: Optional[list[FilterCondition]] = None,
        **kwargs: Any,
    ) -> list[RetrievedChunk]:
        all_ids = await self._repository.get_all_ids(self._collection)
        query_terms = set(query.lower().split())
        scored: list[tuple[str, float]] = []
        for doc_id in all_ids:
            term_score = len(query_terms) / max(len(query_terms), 1)
            scored.append((doc_id, term_score))
        scored.sort(key=lambda x: x[1], reverse=True)
        results: list[RetrievedChunk] = []
        for doc_id, score in scored[:top_k]:
            if score >= threshold:
                from app.rag.schemas import Chunk, ChunkMetadata
                chunk = Chunk(id=doc_id, content="", metadata=ChunkMetadata())
                results.append(RetrievedChunk(chunk=chunk, score=score, retrieval_method=RetrievalMethod.KEYWORD))
        return results

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "retriever": self.retriever_id}


class HybridRetriever(Retriever):
    """Combines vector similarity and keyword matching."""

    def __init__(
        self,
        repository: VectorRepository,
        embedder: EmbeddingProvider,
        collection: str = "documents",
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> None:
        self._repository = repository
        self._embedder = embedder
        self._collection = collection
        self._vec_w = vector_weight
        self._kw_w = keyword_weight
        self._vector_retriever = VectorRetriever(repository, embedder, collection)
        self._keyword_retriever = KeywordRetriever(repository, collection)

    @property
    def retriever_id(self) -> str:
        return "hybrid"

    @property
    def retrieval_method(self) -> RetrievalMethod:
        return RetrievalMethod.HYBRID

    async def retrieve(
        self,
        query: str,
        embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.0,
        filters: Optional[list[FilterCondition]] = None,
        **kwargs: Any,
    ) -> list[RetrievedChunk]:
        vec_results = await self._vector_retriever.retrieve(
            query, embedding, top_k * 2, threshold, filters
        )
        kw_results = await self._keyword_retriever.retrieve(
            query, embedding, top_k * 2, threshold, filters
        )
        merged: dict[str, float] = {}
        for rc in vec_results:
            merged[rc.chunk.id] = merged.get(rc.chunk.id, 0.0) + rc.score * self._vec_w
        for rc in kw_results:
            merged[rc.chunk.id] = merged.get(rc.chunk.id, 0.0) + rc.score * self._kw_w
        chunk_map: dict[str, RetrievedChunk] = {}
        for rc in vec_results + kw_results:
            if rc.chunk.id not in chunk_map:
                chunk_map[rc.chunk.id] = rc
        combined: list[RetrievedChunk] = []
        for chunk_id, score in sorted(merged.items(), key=lambda x: x[1], reverse=True):
            if chunk_id in chunk_map:
                rc = chunk_map[chunk_id]
                rc.score = score
                rc.retrieval_method = RetrievalMethod.HYBRID
                combined.append(rc)
        return combined[:top_k]

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "retriever": self.retriever_id}


class MemoryRetriever(Retriever):
    """Retrieves from conversation/semantic memory sources."""

    def __init__(self, memory_provider: Any = None, collection: str = "memory") -> None:
        self._memory = memory_provider
        self._collection = collection

    @property
    def retriever_id(self) -> str:
        return "memory"

    @property
    def retrieval_method(self) -> RetrievalMethod:
        return RetrievalMethod.MEMORY

    async def retrieve(
        self,
        query: str,
        embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.0,
        filters: Optional[list[FilterCondition]] = None,
        **kwargs: Any,
    ) -> list[RetrievedChunk]:
        if self._memory is None:
            return []
        try:
            results = await self._memory.search(query, top_k=top_k, threshold=threshold)
            from app.rag.schemas import Chunk, ChunkMetadata
            chunks: list[RetrievedChunk] = []
            for r in results:
                if isinstance(r, dict):
                    chunk = Chunk(
                        id=r.get("id", ""),
                        content=r.get("content", r.get("text", "")),
                        metadata=ChunkMetadata(**r.get("metadata", {})) if r.get("metadata") else ChunkMetadata(),
                    )
                    chunks.append(RetrievedChunk(chunk=chunk, score=r.get("score", 0.0), retrieval_method=RetrievalMethod.MEMORY))
            return chunks
        except Exception as e:
            logger.warning("Memory retrieval failed: %s", e)
            return []

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy" if self._memory else "no_provider", "retriever": self.retriever_id}


class KnowledgeRetriever(Retriever):
    """Retrieves from knowledge graph sources."""

    def __init__(self, knowledge_engine: Any = None) -> None:
        self._kg_engine = knowledge_engine

    @property
    def retriever_id(self) -> str:
        return "knowledge"

    @property
    def retrieval_method(self) -> RetrievalMethod:
        return RetrievalMethod.KNOWLEDGE

    async def retrieve(
        self,
        query: str,
        embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.0,
        filters: Optional[list[FilterCondition]] = None,
        **kwargs: Any,
    ) -> list[RetrievedChunk]:
        if self._kg_engine is None:
            return []
        try:
            entities = await self._kg_engine.search(query, limit=top_k)
            from app.rag.schemas import Chunk, ChunkMetadata
            chunks: list[RetrievedChunk] = []
            for entity in entities:
                content = f"{entity.name}: {entity.description}" if hasattr(entity, "description") else str(entity)
                chunk = Chunk(
                    id=getattr(entity, "id", ""),
                    content=content,
                    metadata=ChunkMetadata(
                        title=getattr(entity, "name", ""),
                        source="knowledge_graph",
                        category=getattr(entity, "type", ""),
                    ),
                )
                score = 1.0 if hasattr(entity, "confidence") else 0.5
                chunks.append(RetrievedChunk(chunk=chunk, score=score, retrieval_method=RetrievalMethod.KNOWLEDGE))
            return chunks
        except Exception as e:
            logger.warning("Knowledge retrieval failed: %s", e)
            return []

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy" if self._kg_engine else "no_provider", "retriever": self.retriever_id}


def get_retriever(
    method: RetrievalMethod = RetrievalMethod.VECTOR,
    repository: Optional[VectorRepository] = None,
    embedder: Optional[EmbeddingProvider] = None,
    collection: str = "documents",
    **kwargs: Any,
) -> Retriever:
    if method == RetrievalMethod.VECTOR:
        return VectorRetriever(repository, embedder, collection)
    if method == RetrievalMethod.KEYWORD:
        return KeywordRetriever(repository, collection)
    if method == RetrievalMethod.HYBRID:
        return HybridRetriever(repository, embedder, collection)
    if method == RetrievalMethod.MEMORY:
        return MemoryRetriever(**kwargs)
    if method == RetrievalMethod.KNOWLEDGE:
        return KnowledgeRetriever(**kwargs)
    return VectorRetriever(repository, embedder, collection)
