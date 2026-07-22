"""RAG rerankers — re-score retrieved chunks for improved relevance."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from app.rag.base import Reranker
from app.rag.schemas import RetrievedChunk


class SimilarityReranker(Reranker):
    """Reranks by raw similarity score (pass-through)."""

    @property
    def reranker_id(self) -> str:
        return "similarity"

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = 10,
        **kwargs: Any,
    ) -> list[RetrievedChunk]:
        sorted_chunks = sorted(chunks, key=lambda c: c.score, reverse=True)
        for c in sorted_chunks[:top_k]:
            c.rerank_score = c.score
        return sorted_chunks[:top_k]

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "reranker": self.reranker_id}


class CrossEncoderReranker(Reranker):
    """Simulated cross-encoder reranker using term overlap scoring."""

    def __init__(self, boost_factor: float = 1.2) -> None:
        self._boost = boost_factor

    @property
    def reranker_id(self) -> str:
        return "cross_encoder"

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = 10,
        **kwargs: Any,
    ) -> list[RetrievedChunk]:
        query_terms = set(query.lower().split())
        for rc in chunks:
            chunk_terms = set(rc.chunk.content.lower().split())
            overlap = len(query_terms & chunk_terms)
            term_score = overlap / max(len(query_terms), 1)
            combined = (rc.score * 0.6) + (term_score * 0.4 * self._boost)
            rc.rerank_score = min(combined, 1.0)
        sorted_chunks = sorted(chunks, key=lambda c: c.rerank_score or 0.0, reverse=True)
        return sorted_chunks[:top_k]

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "reranker": self.reranker_id}


class HybridScoreReranker(Reranker):
    """Combines similarity score with BM25-style keyword matching."""

    def __init__(self, similarity_weight: float = 0.7, keyword_weight: float = 0.3) -> None:
        self._sim_w = similarity_weight
        self._kw_w = keyword_weight

    @property
    def reranker_id(self) -> str:
        return "hybrid_score"

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = 10,
        **kwargs: Any,
    ) -> list[RetrievedChunk]:
        query_terms = set(query.lower().split())
        avg_dl = max(1, sum(len(c.chunk.content.split()) for c in chunks) / max(len(chunks), 1))
        for rc in chunks:
            chunk_terms = set(rc.chunk.content.lower().split())
            tf = len(query_terms & chunk_terms)
            dl = len(rc.chunk.content.split())
            bm25 = (tf / (tf + 1.0 + 0.5 * (dl / avg_dl))) if tf > 0 else 0.0
            hybrid = (rc.score * self._sim_w) + (bm25 * self._kw_w)
            rc.rerank_score = min(hybrid, 1.0)
        sorted_chunks = sorted(chunks, key=lambda c: c.rerank_score or 0.0, reverse=True)
        return sorted_chunks[:top_k]

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "reranker": self.reranker_id}


class RecencyAwareReranker(Reranker):
    """Boosts recently created chunks."""

    def __init__(self, recency_weight: float = 0.3, half_life_days: float = 30.0) -> None:
        self._recency_w = recency_weight
        self._half_life = half_life_days

    @property
    def reranker_id(self) -> str:
        return "recency"

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = 10,
        **kwargs: Any,
    ) -> list[RetrievedChunk]:
        now = datetime.now(timezone.utc)
        for rc in chunks:
            created = rc.chunk.metadata.created_at
            if created and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created:
                age_days = max((now - created).total_seconds() / 86400, 0)
                recency = math.exp(-0.693 * age_days / self._half_life)
            else:
                recency = 0.5
            combined = (rc.score * (1.0 - self._recency_w)) + (recency * self._recency_w)
            rc.rerank_score = min(combined, 1.0)
        sorted_chunks = sorted(chunks, key=lambda c: c.rerank_score or 0.0, reverse=True)
        return sorted_chunks[:top_k]

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "reranker": self.reranker_id}


class ImportanceAwareReranker(Reranker):
    """Boosts chunks with higher confidence/importance scores."""

    def __init__(self, importance_weight: float = 0.3) -> None:
        self._importance_w = importance_weight

    @property
    def reranker_id(self) -> str:
        return "importance"

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = 10,
        **kwargs: Any,
    ) -> list[RetrievedChunk]:
        for rc in chunks:
            confidence = rc.chunk.metadata.confidence
            combined = (rc.score * (1.0 - self._importance_w)) + (confidence * self._importance_w)
            rc.rerank_score = min(combined, 1.0)
        sorted_chunks = sorted(chunks, key=lambda c: c.rerank_score or 0.0, reverse=True)
        return sorted_chunks[:top_k]

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "reranker": self.reranker_id}


def get_reranker(strategy: str = "similarity", **kwargs: Any) -> Reranker:
    mapping: dict[str, type[Reranker]] = {
        "similarity": SimilarityReranker,
        "cross_encoder": CrossEncoderReranker,
        "hybrid_score": HybridScoreReranker,
        "recency": RecencyAwareReranker,
        "importance": ImportanceAwareReranker,
    }
    cls = mapping.get(strategy, SimilarityReranker)
    return cls(**kwargs) if kwargs else cls()
