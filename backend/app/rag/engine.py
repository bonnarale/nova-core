"""RAG engine — top-level orchestrator for the RAG system."""

from __future__ import annotations

import logging
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
from app.rag.index import RAGIndex
from app.rag.lifecycle import RAGLifecycle, RAGState
from app.rag.metrics import RAGMetrics, get_rag_metrics
from app.rag.pipeline import RAGPipeline
from app.rag.query_rewriter import PassthroughRewriter
from app.rag.reranker import SimilarityReranker
from app.rag.retriever import VectorRetriever
from app.rag.schemas import (
    ContextPackage,
    FilterCondition,
    IndexDocument,
    IndexResult,
    QueryRewrite,
    RetrievalMethod,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStatus,
)
from app.rag.tracing import RAGTracer, get_rag_tracer

logger = logging.getLogger(__name__)


class RAGEngine:
    """Top-level RAG engine orchestrating query rewriting, retrieval, reranking, and context building.

    Integrates with:
    - Cognitive Engine: provides retrieval results for context assembly
    - Knowledge Engine: augments retrieval with knowledge graph data
    - Memory System: retrieves from conversation/semantic memory
    - Model Gateway: used for embedding generation
    - Tool System: can be exposed as a retrieval tool
    """

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
        self._lifecycle = RAGLifecycle("rag_engine")
        self._metrics = metrics or get_rag_metrics()
        self._tracer = tracer or get_rag_tracer()

        self._index = RAGIndex(
            repository=repository,
            embedder=embedder,
            metrics=self._metrics,
            collection=collection,
        )
        self._pipeline = RAGPipeline(
            embedder=embedder,
            repository=repository,
            retriever=retriever,
            reranker=reranker,
            query_rewriter=query_rewriter,
            context_builder=context_builder,
            citation_provider=citation_provider,
            metrics=self._metrics,
            tracer=self._tracer,
            collection=collection,
        )
        self._collection = collection
        self._knowledge_engine: Any = None
        self._memory_provider: Any = None
        self._cognitive_engine: Any = None

    @property
    def lifecycle(self) -> RAGLifecycle:
        return self._lifecycle

    @property
    def metrics(self) -> RAGMetrics:
        return self._metrics

    @property
    def tracer(self) -> RAGTracer:
        return self._tracer

    @property
    def index(self) -> RAGIndex:
        return self._index

    @property
    def pipeline(self) -> RAGPipeline:
        return self._pipeline

    def set_knowledge_engine(self, engine: Any) -> None:
        self._knowledge_engine = engine

    def set_memory_provider(self, provider: Any) -> None:
        self._memory_provider = provider

    def set_cognitive_engine(self, engine: Any) -> None:
        self._cognitive_engine = engine

    async def initialize(self) -> None:
        if self._lifecycle.state != RAGState.REGISTERED:
            if self._lifecycle.state == RAGState.SHUTDOWN:
                self._lifecycle.recover()
            else:
                return
        self._lifecycle.initialized()
        self._lifecycle.ready()
        logger.info("RAG engine initialized (collection=%s)", self._collection)

    async def shutdown(self) -> None:
        self._lifecycle.shutdown()
        logger.info("RAG engine shutdown")

    async def query(
        self,
        request: RetrievalQuery,
        user_context: Optional[dict[str, Any]] = None,
        conversation_history: Optional[list[dict[str, str]]] = None,
        goal_context: Optional[list[dict[str, Any]]] = None,
        task_context: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> ContextPackage:
        self._lifecycle.retrieving()
        try:
            knowledge_context = kwargs.get("knowledge_context")
            if self._knowledge_engine and not knowledge_context:
                try:
                    kg_entities = await self._knowledge_engine.search(request.query, limit=5)
                    knowledge_context = [
                        {"name": getattr(e, "name", ""), "description": getattr(e, "description", "")}
                        for e in (kg_entities or [])
                    ]
                except Exception:
                    knowledge_context = []

            context = await self._pipeline.query(
                request,
                user_context=user_context,
                conversation_history=conversation_history,
                goal_context=goal_context,
                task_context=task_context,
                knowledge_context=knowledge_context,
                **kwargs,
            )
            self._lifecycle.ready()
            return context
        except Exception as e:
            self._lifecycle.failed(str(e))
            raise

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.0,
        filters: Optional[list[FilterCondition]] = None,
        **kwargs: Any,
    ) -> RetrievalResult:
        self._lifecycle.retrieving()
        try:
            result = await self._pipeline.retrieve(query, top_k, threshold, filters, **kwargs)
            self._lifecycle.ready()
            return result
        except Exception as e:
            self._lifecycle.failed(str(e))
            raise

    async def index_document(self, doc: IndexDocument) -> IndexResult:
        self._lifecycle.indexing()
        try:
            result = await self._index.index_document(doc)
            self._lifecycle.ready()
            return result
        except Exception as e:
            self._lifecycle.failed(str(e))
            raise

    async def index_documents(self, docs: list[IndexDocument]) -> list[IndexResult]:
        self._lifecycle.indexing()
        try:
            results = await self._index.index_documents(docs)
            self._lifecycle.ready()
            return results
        except Exception as e:
            self._lifecycle.failed(str(e))
            raise

    async def reindex(self, document_ids: Optional[list[str]] = None, reindex_all: bool = False) -> list[IndexResult]:
        self._lifecycle.indexing()
        try:
            if reindex_all:
                all_ids = await self._repository.get_all_ids(self._collection)
                for doc_id in all_ids:
                    await self._repository.delete(self._collection, [doc_id])
            self._lifecycle.ready()
            return []
        except Exception as e:
            self._lifecycle.failed(str(e))
            raise

    async def health(self) -> dict[str, Any]:
        repo_health = await self._repository.health()
        embed_health = await self._embedder.health()
        return {
            "status": "healthy" if self._lifecycle.is_ready else self._lifecycle.state.value,
            "lifecycle_state": self._lifecycle.state.value,
            "repository_status": repo_health.get("status", "unknown"),
            "embedding_provider": embed_health.get("provider", "unknown"),
            "document_count": await self._index.get_document_count(),
            "chunk_count": await self._index.count(),
        }

    def get_metrics_summary(self) -> dict[str, Any]:
        return self._metrics.get_summary()

    def get_traces(self, limit: int = 100) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._tracer.get_traces(limit)]

    async def get_statistics(self) -> dict[str, Any]:
        return await self._index.get_statistics()
