"""Vector Memory factory — creates and wires vector memory components."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.vector_memory.base import ConsolidationStrategy, EmbeddingProvider, VectorRepository
from app.vector_memory.consolidation import DefaultConsolidationStrategy
from app.vector_memory.embeddings import (
    GoogleEmbeddingProvider,
    InMemoryEmbeddingProvider,
    LocalEmbeddingProvider,
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from app.vector_memory.engine import VectorMemoryEngine
from app.vector_memory.index import VectorIndex
from app.vector_memory.lifecycle import VectorMemoryLifecycle
from app.vector_memory.metrics import VectorMetrics, get_vector_metrics
from app.vector_memory.repository import ChromaVectorRepository, InMemoryVectorRepository
from app.vector_memory.search import VectorSearchEngine
from app.vector_memory.similarity import CosineSimilarity, SimilarityEngine
from app.vector_memory.tracing import VectorTracer, get_vector_tracer

logger = logging.getLogger(__name__)


class VectorMemoryFactory:
    """Factory for creating Vector Memory engines with configured components.

    Supports automatic provider registration and dependency injection.
    """

    _embedding_providers: dict[str, type[EmbeddingProvider]] = {
        "in_memory": InMemoryEmbeddingProvider,
        "ollama": OllamaEmbeddingProvider,
        "openai": OpenAIEmbeddingProvider,
        "google": GoogleEmbeddingProvider,
        "local": LocalEmbeddingProvider,
    }

    _repository_providers: dict[str, type[VectorRepository]] = {
        "in_memory": InMemoryVectorRepository,
        "chroma": ChromaVectorRepository,
    }

    _storage_providers: dict[str, type] = {}

    _similarity_engines: dict[str, type[SimilarityEngine]] = {
        "cosine": CosineSimilarity,
    }

    def __init__(
        self,
        embedder: Optional[EmbeddingProvider] = None,
        repository: Optional[VectorRepository] = None,
        similarity: Optional[SimilarityEngine] = None,
        consolidation: Optional[ConsolidationStrategy] = None,
        metrics: Optional[VectorMetrics] = None,
        tracer: Optional[VectorTracer] = None,
    ) -> None:
        self._embedder = embedder
        self._repository = repository
        self._similarity = similarity
        self._consolidation = consolidation
        self._metrics = metrics or get_vector_metrics()
        self._tracer = tracer or get_vector_tracer()

    @classmethod
    def register_embedding_provider(cls, name: str, provider_cls: type[EmbeddingProvider]) -> None:
        cls._embedding_providers[name] = provider_cls
        logger.debug("Registered embedding provider: %s", name)

    @classmethod
    def register_repository_provider(cls, name: str, provider_cls: type[VectorRepository]) -> None:
        cls._repository_providers[name] = provider_cls
        logger.debug("Registered repository provider: %s", name)

    @classmethod
    def register_storage_provider(cls, name: str, storage_cls: type) -> None:
        cls._storage_providers[name] = storage_cls
        logger.debug("Registered storage provider: %s", name)

    @classmethod
    def register_similarity_engine(cls, name: str, engine_cls: type[SimilarityEngine]) -> None:
        cls._similarity_engines[name] = engine_cls
        logger.debug("Registered similarity engine: %s", name)

    def create_engine(
        self,
        **kwargs: Any,
    ) -> VectorMemoryEngine:
        embedder = kwargs.get("embedder") or self._embedder
        if embedder is None:
            embedder = InMemoryEmbeddingProvider(dimension=384)

        repository = kwargs.get("repository") or self._repository
        if repository is None:
            repository = InMemoryVectorRepository()

        similarity = kwargs.get("similarity") or self._similarity or CosineSimilarity()
        consolidation = kwargs.get("consolidation") or self._consolidation or DefaultConsolidationStrategy()
        metrics = kwargs.get("metrics") or self._metrics
        tracer = kwargs.get("tracer") or self._tracer

        return VectorMemoryEngine(
            embedder=embedder,
            repository=repository,
            similarity=similarity,
            consolidation_strategy=consolidation,
            metrics=metrics,
            tracer=tracer,
        )

    def create_engine_with_storage(
        self,
        storage_type: str = "in_memory",
        embedding_type: str = "in_memory",
        similarity_type: str = "cosine",
        **kwargs: Any,
    ) -> VectorMemoryEngine:
        embedder = self._create_embedder(embedding_type, kwargs)
        repository = self._create_repository(storage_type, kwargs)
        similarity = self._create_similarity(similarity_type)
        consolidation = DefaultConsolidationStrategy()

        return VectorMemoryEngine(
            embedder=embedder,
            repository=repository,
            similarity=similarity,
            consolidation_strategy=consolidation,
            metrics=self._metrics,
            tracer=self._tracer,
        )

    def _create_embedder(self, provider_type: str, kwargs: dict[str, Any]) -> EmbeddingProvider:
        cls = self._embedding_providers.get(provider_type)
        if not cls:
            raise ValueError(f"Unknown embedding provider: {provider_type}")
        return cls(**kwargs)

    def _create_repository(self, storage_type: str, kwargs: dict[str, Any]) -> VectorRepository:
        cls = self._repository_providers.get(storage_type)
        if not cls:
            raise ValueError(f"Unknown repository type: {storage_type}")
        if storage_type == "chroma":
            return cls(chroma_client=kwargs.get("chroma_client"))
        return cls()

    @staticmethod
    def _create_similarity(engine_type: str) -> SimilarityEngine:
        engines = {
            "cosine": CosineSimilarity(),
            "dot_product": __import__("app.vector_memory.similarity", fromlist=["DotProductSimilarity"]).DotProductSimilarity(),
            "euclidean": __import__("app.vector_memory.similarity", fromlist=["EuclideanSimilarity"]).EuclideanSimilarity(),
        }
        engine = engines.get(engine_type)
        if not engine:
            raise ValueError(f"Unknown similarity engine: {engine_type}")
        return engine
