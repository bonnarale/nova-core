"""RAG factory — create and configure RAG components."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.rag.base import (
    CitationProvider,
    ContextBuilder,
    EmbeddingProvider,
    QueryRewriter,
    Reranker,
    VectorRepository,
)
from app.rag.citations import DefaultCitationProvider
from app.rag.context_builder import DefaultContextBuilder
from app.rag.embeddings import InMemoryEmbeddingProvider
from app.rag.engine import RAGEngine
from app.rag.index import RAGIndex
from app.rag.metrics import RAGMetrics, get_rag_metrics
from app.rag.pipeline import RAGPipeline
from app.rag.query_rewriter import PassthroughRewriter
from app.rag.reranker import SimilarityReranker
from app.rag.repository import InMemoryRepository
from app.rag.tracing import RAGTracer, get_rag_tracer

logger = logging.getLogger(__name__)


class RAGFactory:
    """Factory for creating configured RAG components."""

    def __init__(
        self,
        embedder: Optional[EmbeddingProvider] = None,
        repository: Optional[VectorRepository] = None,
        collection: str = "documents",
    ) -> None:
        self._embedder = embedder or InMemoryEmbeddingProvider()
        self._repository = repository or InMemoryRepository()
        self._collection = collection
        self._metrics = get_rag_metrics()
        self._tracer = get_rag_tracer()

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

    def create_pipeline(
        self,
        retriever: Optional[Any] = None,
        reranker: Optional[Reranker] = None,
        query_rewriter: Optional[QueryRewriter] = None,
        context_builder: Optional[ContextBuilder] = None,
        citation_provider: Optional[CitationProvider] = None,
    ) -> RAGPipeline:
        from app.rag.retriever import VectorRetriever
        return RAGPipeline(
            embedder=self._embedder,
            repository=self._repository,
            retriever=retriever or VectorRetriever(self._repository, self._embedder, self._collection),
            reranker=reranker or SimilarityReranker(),
            query_rewriter=query_rewriter or PassthroughRewriter(),
            context_builder=context_builder or DefaultContextBuilder(),
            citation_provider=citation_provider or DefaultCitationProvider(),
            metrics=self._metrics,
            tracer=self._tracer,
            collection=self._collection,
        )

    def create_index(self) -> RAGIndex:
        return RAGIndex(
            repository=self._repository,
            embedder=self._embedder,
            metrics=self._metrics,
            collection=self._collection,
        )

    def create_engine(self) -> RAGEngine:
        engine = RAGEngine(
            embedder=self._embedder,
            repository=self._repository,
            metrics=self._metrics,
            tracer=self._tracer,
            collection=self._collection,
        )
        logger.info("RAG engine created via factory")
        return engine

    def create_default_engine(self) -> RAGEngine:
        return self.create_engine()


def get_rag_factory(
    embedder: Optional[EmbeddingProvider] = None,
    repository: Optional[VectorRepository] = None,
    collection: str = "documents",
) -> RAGFactory:
    return RAGFactory(embedder=embedder, repository=repository, collection=collection)
