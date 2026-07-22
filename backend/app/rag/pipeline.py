"""RAG pipeline — orchestrate the full retrieval pipeline."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from app.rag.base import (
    CitationProvider,
    ContextBuilder,
    EmbeddingProvider,
    QueryRewriter,
    Reranker,
    Retriever,
    VectorRepository,
)
from app.rag.citations import DefaultCitationProvider
from app.rag.context_builder import DefaultContextBuilder
from app.rag.filters import merge_filters
from app.rag.metrics import RAGMetrics, RequestMetric, get_rag_metrics
from app.rag.query_rewriter import PassthroughRewriter
from app.rag.reranker import SimilarityReranker
from app.rag.retriever import VectorRetriever
from app.rag.schemas import (
    ContextPackage,
    FilterCondition,
    RetrievedChunk,
    RetrievalMethod,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStatus,
)
from app.rag.tracing import RAGTracer, RAGTrace, get_rag_tracer

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Full RAG pipeline: rewrite -> embed -> retrieve -> rerank -> cite -> build context."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        repository: VectorRepository,
        retriever: Optional[Retriever] = None,
        reranker: Optional[Reranker] = None,
        query_rewriter: Optional[QueryRewriter] = None,
        context_builder: Optional[ContextBuilder] = None,
        citation_provider: Optional[CitationProvider] = None,
        metrics: Optional[RAGMetrics] = None,
        tracer: Optional[RAGTracer] = None,
        collection: str = "documents",
    ) -> None:
        self._embedder = embedder
        self._repository = repository
        self._retriever = retriever or VectorRetriever(repository, embedder, collection)
        self._reranker = reranker or SimilarityReranker()
        self._query_rewriter = query_rewriter or PassthroughRewriter()
        self._context_builder = context_builder or DefaultContextBuilder()
        self._citation_provider = citation_provider or DefaultCitationProvider()
        self._metrics = metrics or get_rag_metrics()
        self._tracer = tracer or get_rag_tracer()
        self._collection = collection

    @property
    def embedder(self) -> EmbeddingProvider:
        return self._embedder

    @property
    def repository(self) -> VectorRepository:
        return self._repository

    @property
    def metrics(self) -> RAGMetrics:
        return self._metrics

    @property
    def tracer(self) -> RAGTracer:
        return self._tracer

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.0,
        filters: Optional[list[FilterCondition]] = None,
        retrieval_method: RetrievalMethod = RetrievalMethod.VECTOR,
        **kwargs: Any,
    ) -> RetrievalResult:
        start_time = time.time()
        trace = self._tracer.start_trace(query)
        try:
            embed_span = self._tracer.start_span("embed_query", trace)
            embedding = await self._embedder.embed(query)
            self._tracer.finish_span(embed_span, "completed")
            trace.embedding_provider = self._embedder.provider_id

            retrieve_span = self._tracer.start_span("retrieve", trace)
            t0 = time.time()
            chunks = await self._retriever.retrieve(
                query, embedding, top_k, threshold, filters
            )
            retrieval_latency = (time.time() - t0) * 1000
            self._tracer.finish_span(retrieve_span, "completed")
            trace.chunks_retrieved = len(chunks)

            rerank_span = self._tracer.start_span("rerank", trace)
            t1 = time.time()
            reranked = await self._reranker.rerank(query, chunks, top_k)
            rerank_latency = (time.time() - t1) * 1000
            self._tracer.finish_span(rerank_span, "completed")
            trace.chunks_reranked = len(reranked)

            cite_span = self._tracer.start_span("citations", trace)
            citations = await self._citation_provider.generate_citations(
                query, reranked, retrieval_method
            )
            self._tracer.finish_span(cite_span, "completed")

            latency_ms = (time.time() - start_time) * 1000
            self._tracer.finish_trace(trace, "completed")

            metric = RequestMetric(
                request_id=str(trace.trace_id),
                query=query,
                start_time=start_time,
                chunks_retrieved=len(chunks),
                chunks_reranked=len(reranked),
                retrieval_latency_ms=retrieval_latency,
                rerank_latency_ms=rerank_latency,
            )
            metric.complete()
            self._metrics.record_request(metric)

            return RetrievalResult(
                query=query,
                chunks=reranked,
                citations=citations,
                total_chunks=len(reranked),
                status=RetrievalStatus.SUCCESS if reranked else RetrievalStatus.NO_RESULTS,
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._tracer.finish_trace(trace, "error", str(e))
            metric = RequestMetric(
                request_id=str(trace.trace_id),
                query=query,
                start_time=start_time,
                success=False,
                error=str(e),
            )
            metric.complete(False, str(e))
            self._metrics.record_request(metric)
            return RetrievalResult(
                query=query,
                status=RetrievalStatus.ERROR,
                latency_ms=latency_ms,
                metadata={"error": str(e)},
            )

    async def query(
        self,
        request: RetrievalQuery,
        user_context: Optional[dict[str, Any]] = None,
        conversation_history: Optional[list[dict[str, str]]] = None,
        goal_context: Optional[list[dict[str, Any]]] = None,
        task_context: Optional[list[dict[str, Any]]] = None,
        knowledge_context: Optional[list[dict[str, Any]]] = None,
        execution_context: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ContextPackage:
        rewritten = await self._query_rewriter.rewrite(request.query, kwargs.get("rewrite_context"))
        effective_query = rewritten.rewritten_query or request.query
        filters = merge_filters(request.filters)
        result = await self.retrieve(
            effective_query,
            request.top_k,
            request.threshold,
            filters,
            request.retrieval_method,
        )
        context = await self._context_builder.build(
            query=request.query,
            retrieved_chunks=result.chunks,
            user_context=user_context,
            conversation_history=conversation_history,
            goal_context=goal_context,
            task_context=task_context,
            knowledge_context=knowledge_context,
            execution_context=execution_context,
        )
        context.rewritten_query = rewritten.rewritten_query
        context.citations = result.citations
        return context
