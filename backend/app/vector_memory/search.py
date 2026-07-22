"""Vector search engine — semantic, hybrid, and filtered search."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from app.vector_memory.base import EmbeddingProvider
from app.vector_memory.metrics import VectorMetrics, get_vector_metrics
from app.vector_memory.schemas import MemoryCategory, VectorMemoryQuery, VectorMemorySearchResult, VectorRecord
from app.vector_memory.similarity import CosineSimilarity, SimilarityEngine
from app.vector_memory.tracing import VectorTracer, get_vector_tracer

logger = logging.getLogger(__name__)


class VectorSearchEngine:
    """Search engine for vector memory — semantic, hybrid, and filtered search."""

    def __init__(
        self,
        storage: Any,
        embedder: EmbeddingProvider,
        similarity: SimilarityEngine | None = None,
        metrics: VectorMetrics | None = None,
        tracer: VectorTracer | None = None,
    ) -> None:
        self._storage = storage
        self._embedder = embedder
        self._similarity = similarity or CosineSimilarity()
        self._metrics = metrics or get_vector_metrics()
        self._tracer = tracer or get_vector_tracer()

    async def search(self, query: VectorMemoryQuery) -> VectorMemorySearchResult:
        start = time.monotonic()
        span = self._tracer.start_span("search", query=query.query)

        try:
            if not query.embedding and query.query:
                emb_start = time.monotonic()
                query.embedding = await self._embedder.embed(query.query)
                emb_elapsed = (time.monotonic() - emb_start) * 1000
                self._metrics.record_embedding_latency(emb_elapsed)

            if not query.embedding:
                return VectorMemorySearchResult(results=[], total=0, query=query.query)

            results = await self._storage.search_with_filters(
                query_embedding=query.embedding,
                top_k=query.top_k,
                threshold=query.threshold,
                memory_category=query.memory_category,
                user_id=query.user_id,
                session_id=query.session_id,
                tags=query.tags,
            )

            elapsed = (time.monotonic() - start) * 1000
            self._metrics.record_search()
            self._metrics.record_retrieval_latency(elapsed)
            self._tracer.end_span(span, result_count=len(results), latency_ms=elapsed)

            return VectorMemorySearchResult(
                results=results,
                total=len(results),
                query=query.query,
                time_taken_ms=elapsed,
            )
        except Exception:
            self._tracer.end_span(span, error=True)
            raise

    async def similarity_search(
        self,
        embedding: list[float],
        top_k: int = 10,
        threshold: Optional[float] = None,
        memory_category: Optional[MemoryCategory] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> VectorMemorySearchResult:
        start = time.monotonic()
        span = self._tracer.start_span("similarity_search")

        try:
            results = await self._storage.search_with_filters(
                query_embedding=embedding,
                top_k=top_k,
                threshold=threshold,
                memory_category=memory_category,
                user_id=user_id,
                session_id=session_id,
                tags=tags,
            )

            elapsed = (time.monotonic() - start) * 1000
            self._metrics.record_search()
            self._metrics.record_retrieval_latency(elapsed)
            self._tracer.end_span(span, result_count=len(results), latency_ms=elapsed)

            return VectorMemorySearchResult(
                results=results,
                total=len(results),
                time_taken_ms=elapsed,
            )
        except Exception:
            self._tracer.end_span(span, error=True)
            raise

    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 10,
        threshold: Optional[float] = None,
        memory_category: Optional[MemoryCategory] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        semantic_weight: float = 0.7,
    ) -> VectorMemorySearchResult:
        start = time.monotonic()
        span = self._tracer.start_span("hybrid_search", query=query_text)

        try:
            results = await self._storage.search_with_filters(
                query_embedding=query_embedding,
                top_k=top_k * 2,
                threshold=threshold,
                memory_category=memory_category,
                user_id=user_id,
                session_id=session_id,
                tags=tags,
            )

            keyword_scores = self._compute_keyword_scores(query_text, results)
            for result in results:
                semantic_score = result.score
                kw_score = keyword_scores.get(result.vector_id, 0.0)
                result.score = (semantic_score * semantic_weight) + (kw_score * (1.0 - semantic_weight))

            results.sort(key=lambda r: r.score, reverse=True)
            results = results[:top_k]

            elapsed = (time.monotonic() - start) * 1000
            self._metrics.record_search()
            self._metrics.record_retrieval_latency(elapsed)
            self._tracer.end_span(span, result_count=len(results), latency_ms=elapsed)

            return VectorMemorySearchResult(
                results=results,
                total=len(results),
                query=query_text,
                time_taken_ms=elapsed,
            )
        except Exception:
            self._tracer.end_span(span, error=True)
            raise

    def _compute_keyword_scores(
        self, query: str, results: list[VectorRecord],
    ) -> dict[str, float]:
        query_terms = set(query.lower().split())
        scores: dict[str, float] = {}
        for r in results:
            content_terms = set(r.content.lower().split())
            if not query_terms:
                scores[r.vector_id] = 0.0
                continue
            overlap = len(query_terms.intersection(content_terms))
            scores[r.vector_id] = overlap / len(query_terms)
        return scores
