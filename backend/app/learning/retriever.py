"""Semantic retriever — retrieves learning artifacts by semantic similarity.

Wraps pluggable EmbeddingProvider + VectorStoreProvider to provide
semantic search over learning artifacts, analogous to SemanticMemory
but scoped to the learning domain.
"""

from __future__ import annotations

import logging
from typing import Any

from app.learning.base import LearningRetriever
from app.learning.models import KnowledgeArtifact, RankedMemory, RetrievalResult

logger = logging.getLogger(__name__)

LEARNING_COLLECTION = "nova_learning"


class SemanticRetriever(LearningRetriever):
    """Retrieves learning artifacts using vector-based semantic search.

    Delegates embedding and vector storage to pluggable providers.
    Falls back to keyword search when no vector store is configured.
    """

    def __init__(
        self,
        store: Any = None,
        embedder: Any = None,
        vector_store: Any = None,
        top_k: int = 5,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._vector_store = vector_store
        self._top_k = top_k
        self._collection_ref = None

    async def retrieve(
        self,
        query: str,
        user_id: str | None = None,
        artifact_type: str | None = None,
        limit: int = 10,
    ) -> RetrievalResult:
        if self._vector_store is not None and self._embedder is not None:
            return await self._vector_search(query, user_id, artifact_type, limit)

        return await self._keyword_search(query, user_id, artifact_type, limit)

    async def _vector_search(
        self,
        query: str,
        user_id: str | None,
        artifact_type: str | None,
        limit: int,
    ) -> RetrievalResult:
        try:
            embedding = await self._embedder.embed(query)
            if not embedding:
                return RetrievalResult(query=query)

            col = await self._collection()
            where_filter: dict[str, Any] = {}
            if user_id:
                where_filter["user_id"] = user_id
            if artifact_type:
                where_filter["artifact_type"] = artifact_type

            results_data = await self._vector_store.search(
                col,
                query_embedding=embedding,
                top_k=limit,
                threshold=None,
                where=where_filter if where_filter else None,
            )

            ranked: list[RankedMemory] = []
            for entry in results_data:
                artifact = KnowledgeArtifact(
                    id=entry.metadata.get("artifact_id", entry.id),
                    artifact_type=entry.metadata.get("artifact_type", "fact"),
                    content=entry.document,
                    user_id=entry.metadata.get("user_id"),
                    tags=entry.metadata.get("tags", "").split(",") if entry.metadata.get("tags") else [],
                )
                ranked.append(RankedMemory(
                    artifact=artifact,
                    score=max(1.0 - (entry.distance or 0.0), 0.0),
                ))

            return RetrievalResult(
                results=ranked,
                total=len(ranked),
                query=query,
                filters={"user_id": user_id, "artifact_type": artifact_type},
            )
        except Exception as exc:
            logger.warning("Vector search failed, falling back to keyword: %s", exc)
            return await self._keyword_search(query, user_id, artifact_type, limit)

    async def _keyword_search(
        self,
        query: str,
        user_id: str | None,
        artifact_type: str | None,
        limit: int,
    ) -> RetrievalResult:
        if self._store is None:
            return RetrievalResult(query=query)

        candidates = await self._store.list_all(limit=500)

        query_words = set(query.lower().split())
        scored: list[RankedMemory] = []

        for artifact in candidates:
            if user_id and artifact.user_id != user_id:
                continue
            if artifact_type and artifact.artifact_type != artifact_type:
                continue

            content_words = set(artifact.content.lower().split())
            tag_words = set(t.lower() for t in artifact.tags)
            overlap = len(query_words & (content_words | tag_words))
            if overlap == 0:
                continue

            score = overlap / max(len(query_words), 1)
            scored.append(RankedMemory(artifact=artifact, score=round(score, 4)))

        scored.sort(key=lambda rm: rm.score, reverse=True)
        return RetrievalResult(
            results=scored[:limit],
            total=len(scored),
            query=query,
            filters={"user_id": user_id, "artifact_type": artifact_type},
        )

    async def _collection(self):
        if self._collection_ref is None:
            self._collection_ref = await self._vector_store.get_or_create_collection(
                name=LEARNING_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection_ref
