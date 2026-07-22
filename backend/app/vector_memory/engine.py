"""Vector Memory Engine — top-level orchestrator for dense vector operations."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from app.vector_memory.base import (
    ConsolidationReport,
    ConsolidationStrategy,
    EmbeddingProvider,
    SimilarityEngine,
    VectorMemoryProvider,
    VectorRepository,
)
from app.vector_memory.index import VectorIndex
from app.vector_memory.lifecycle import VectorMemoryLifecycle, VectorMemoryState
from app.vector_memory.metrics import VectorMetrics, get_vector_metrics
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
from app.vector_memory.search import VectorSearchEngine
from app.vector_memory.tracing import VectorTracer, get_vector_tracer

logger = logging.getLogger(__name__)


class VectorMemoryEngine(VectorMemoryProvider):
    """Top-level orchestrator for vector memory operations.

    Integrates with:
    - Memory System: stores and retrieves conversation/user memories as vectors
    - Learning Engine: persists learned knowledge as vectors
    - Knowledge Engine: indexes entities and relationships
    - RAG & Retrieval: cross-retrieval augmentation
    - Cognitive Engine: memory-aware context loading
    - Tool System: exposed as a retrieval tool
    - Model Gateway: embedding generation via configured model
    - Event System: emits vector lifecycle events
    """

    def __init__(
        self,
        embedder: EmbeddingProvider,
        repository: VectorRepository,
        similarity: SimilarityEngine | None = None,
        consolidation_strategy: ConsolidationStrategy | None = None,
        metrics: VectorMetrics | None = None,
        tracer: VectorTracer | None = None,
        config: VectorMemoryConfig | None = None,
    ) -> None:
        self._embedder = embedder
        self._repository = repository
        self._config = config or VectorMemoryConfig()
        self._lifecycle = VectorMemoryLifecycle("vector_memory")
        self._metrics = metrics or get_vector_metrics()
        self._tracer = tracer or get_vector_tracer()

        from app.vector_memory.similarity import CosineSimilarity
        self._similarity = similarity or CosineSimilarity()

        from app.vector_memory.consolidation import DefaultConsolidationStrategy
        self._consolidation_strategy = consolidation_strategy or DefaultConsolidationStrategy()

        self._index = VectorIndex(
            repository=repository,
            embedder=embedder,
            metrics=self._metrics,
        )
        self._search = VectorSearchEngine(
            storage=repository.storage,
            embedder=embedder,
            similarity=self._similarity,
            metrics=self._metrics,
            tracer=self._tracer,
        )
        self._event_bus: Any = None
        self._knowledge_engine: Any = None
        self._learning_engine: Any = None
        self._rag_engine: Any = None
        self._cognitive_engine: Any = None
        self._model_gateway: Any = None
        self._tools: Any = None

    @property
    def lifecycle(self) -> VectorMemoryLifecycle:
        return self._lifecycle

    @property
    def config(self) -> VectorMemoryConfig:
        return self._config

    @property
    def embedder(self) -> EmbeddingProvider:
        return self._embedder

    @property
    def repository(self) -> VectorRepository:
        return self._repository

    @property
    def metrics(self) -> VectorMetrics:
        return self._metrics

    @property
    def tracer(self) -> VectorTracer:
        return self._tracer

    @property
    def index(self) -> VectorIndex:
        return self._index

    @property
    def search_engine(self) -> VectorSearchEngine:
        return self._search

    # ------------------------------------------------------------------
    # Integration setters
    # ------------------------------------------------------------------

    def set_event_bus(self, event_bus: Any) -> None:
        self._event_bus = event_bus

    def set_knowledge_engine(self, engine: Any) -> None:
        self._knowledge_engine = engine

    def set_learning_engine(self, engine: Any) -> None:
        self._learning_engine = engine

    def set_rag_engine(self, engine: Any) -> None:
        self._rag_engine = engine

    def set_cognitive_engine(self, engine: Any) -> None:
        self._cognitive_engine = engine

    def set_model_gateway(self, gateway: Any) -> None:
        self._model_gateway = gateway

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        if self._lifecycle.state != VectorMemoryState.REGISTERED:
            if self._lifecycle.state == VectorMemoryState.SHUTDOWN:
                self._lifecycle.recover()
            else:
                return
        self._lifecycle.initialized()
        self._lifecycle.ready()
        logger.info(
            "VectorMemoryEngine initialized (embedder=%s, repository=%s)",
            self._embedder.provider_id,
            await self._repository.health(),
        )

    async def shutdown(self) -> None:
        self._lifecycle.shutdown()
        logger.info("VectorMemoryEngine shutdown")

    async def health(self) -> dict[str, Any]:
        repo_health = await self._repository.health()
        embed_health = await self._embedder.health()
        return {
            "status": "healthy" if self._lifecycle.is_ready else self._lifecycle.state.value,
            "lifecycle_state": self._lifecycle.state.value,
            "repository": repo_health,
            "embedder": embed_health,
            "total_vectors": await self._repository.count(),
        }

    # ------------------------------------------------------------------
    # Core API — store / update / delete / retrieve
    # ------------------------------------------------------------------

    async def store(self, record: VectorRecord) -> VectorMemoryResult:
        span = self._tracer.start_span("store", vector_id=record.vector_id)

        try:
            if not record.embedding:
                emb_start = time.monotonic()
                record.embedding = await self._embedder.embed(record.content)
                emb_elapsed = (time.monotonic() - emb_start) * 1000
                self._metrics.record_embedding_latency(emb_elapsed)

            record.embedding_provider = self._embedder.provider_id
            if not record.vector_id:
                import uuid
                record.vector_id = str(uuid.uuid4())

            count = await self._repository.add([record])
            self._metrics.increment_vectors_stored()

            self._tracer.end_span(span, vector_id=record.vector_id)
            self._emit_event("vector.stored", record)

            return VectorMemoryResult(
                success=count > 0,
                vector_id=record.vector_id,
                message="Vector stored successfully",
                record=record,
            )
        except Exception as e:
            self._tracer.end_span(span, error=True, error_message=str(e))
            logger.exception("Failed to store vector")
            return VectorMemoryResult(
                success=False,
                message=f"Failed to store vector: {e}",
            )

    async def update(self, record: VectorRecord) -> VectorMemoryResult:
        span = self._tracer.start_span("update", vector_id=record.vector_id)

        try:
            if record.content and not record.embedding:
                emb_start = time.monotonic()
                record.embedding = await self._embedder.embed(record.content)
                emb_elapsed = (time.monotonic() - emb_start) * 1000
                self._metrics.record_embedding_latency(emb_elapsed)

            record.embedding_provider = self._embedder.provider_id
            count = await self._repository.update([record])

            self._tracer.end_span(span)
            self._emit_event("vector.updated", record)

            return VectorMemoryResult(
                success=count > 0,
                vector_id=record.vector_id,
                message="Vector updated successfully" if count > 0 else "Vector not found",
                record=record,
            )
        except Exception as e:
            self._tracer.end_span(span, error=True, error_message=str(e))
            logger.exception("Failed to update vector")
            return VectorMemoryResult(
                success=False,
                message=f"Failed to update vector: {e}",
            )

    async def delete(self, vector_id: str) -> bool:
        span = self._tracer.start_span("delete", vector_id=vector_id)

        try:
            count = await self._repository.delete([vector_id])
            self._tracer.end_span(span)
            self._emit_event("vector.deleted", vector_id)
            return count > 0
        except Exception as e:
            self._tracer.end_span(span, error=True, error_message=str(e))
            logger.exception("Failed to delete vector %s", vector_id)
            return False

    async def retrieve(self, vector_id: str) -> Optional[VectorRecord]:
        span = self._tracer.start_span("retrieve", vector_id=vector_id)

        try:
            record = await self._repository.get(vector_id)
            self._tracer.end_span(span)
            return record
        except Exception as e:
            self._tracer.end_span(span, error=True, error_message=str(e))
            logger.exception("Failed to retrieve vector %s", vector_id)
            return None

    # ------------------------------------------------------------------
    # Search API
    # ------------------------------------------------------------------

    async def search(self, query: VectorMemoryQuery) -> VectorMemorySearchResult:
        self._lifecycle.searching()
        try:
            result = await self._search.search(query)
            self._lifecycle.ready()
            return result
        except Exception:
            self._lifecycle.failed("search failed")
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
        self._lifecycle.searching()
        try:
            result = await self._search.similarity_search(
                embedding=embedding,
                top_k=top_k,
                threshold=threshold,
                memory_category=memory_category,
                user_id=user_id,
                session_id=session_id,
                tags=tags,
            )
            self._lifecycle.ready()
            return result
        except Exception:
            self._lifecycle.failed("similarity_search failed")
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
        self._lifecycle.searching()
        try:
            result = await self._search.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                top_k=top_k,
                threshold=threshold,
                memory_category=memory_category,
                user_id=user_id,
                session_id=session_id,
                tags=tags,
                semantic_weight=semantic_weight,
            )
            self._lifecycle.ready()
            return result
        except Exception:
            self._lifecycle.failed("hybrid_search failed")
            raise

    # ------------------------------------------------------------------
    # Consolidation and Index Management
    # ------------------------------------------------------------------

    async def consolidate(self, **kwargs: Any) -> dict[str, Any]:
        span = self._tracer.start_span("consolidate")
        self._lifecycle.consolidating()

        try:
            all_records = await self._repository.list_all(limit=10000)
            report = await self._consolidation_strategy.consolidate(all_records, **kwargs)

            if report.duplicates_removed > 0 or report.stale_removed > 0:
                self._metrics.record_consolidation()

            self._lifecycle.ready()
            self._tracer.end_span(
                span,
                duplicates_removed=report.duplicates_removed,
                stale_removed=report.stale_removed,
            )

            return {
                "success": True,
                "duplicates_removed": report.duplicates_removed,
                "items_merged": report.items_merged,
                "stale_removed": report.stale_removed,
                "details": report.details,
            }
        except Exception as e:
            self._lifecycle.failed(str(e))
            self._tracer.end_span(span, error=True, error_message=str(e))
            logger.exception("consolidate failed")
            return {"success": False, "error": str(e)}

    async def reindex(
        self,
        vector_ids: Optional[list[str]] = None,
        reindex_all: bool = False,
    ) -> dict[str, Any]:
        span = self._tracer.start_span("reindex")
        self._lifecycle.indexing()

        try:
            records = await self._index.reindex(vector_ids=vector_ids, reindex_all=reindex_all)
            count = len(records)
            self._lifecycle.ready()
            self._tracer.end_span(span, count=count)
            return {"success": True, "reindexed_count": count}
        except Exception as e:
            self._lifecycle.failed(str(e))
            self._tracer.end_span(span, error=True, error_message=str(e))
            return {"success": False, "error": str(e)}

    async def index_document(self, document: VectorMemoryDocument) -> VectorMemoryResult:
        record = await self._index.index_document(document)
        self._emit_event("vector.document_indexed", record)
        return VectorMemoryResult(
            success=True,
            vector_id=record.vector_id,
            message="Document indexed",
            record=record,
        )

    async def index_documents(self, documents: list[VectorMemoryDocument]) -> list[VectorMemoryResult]:
        results: list[VectorMemoryResult] = []
        for doc in documents:
            result = await self.index_document(doc)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Metrics and Statistics
    # ------------------------------------------------------------------

    async def get_statistics(self) -> VectorMemoryStatistics:
        total = await self._repository.count()
        by_category = await self._repository.count_by_category()
        m = self._metrics.get_summary()

        return VectorMemoryStatistics(
            total_vectors=total,
            vectors_by_category=by_category,
            total_searches=m["total_searches"],
            avg_retrieval_latency_ms=m["avg_retrieval_latency_ms"],
            avg_indexing_latency_ms=m["avg_indexing_latency_ms"],
            avg_embedding_latency_ms=m["avg_embedding_latency_ms"],
            storage_usage_bytes=m["storage_usage_bytes"],
            cache_hits=m["cache_hits"],
            cache_misses=m["cache_misses"],
            vectors_indexed=m["vectors_indexed"],
            consolidations_run=m["consolidations_run"],
        )

    def get_metrics_summary(self) -> dict[str, Any]:
        return self._metrics.get_summary()

    def get_traces(self, limit: int = 100) -> list[dict[str, Any]]:
        return [t.details for t in self._tracer.get_traces(limit)]

    # ------------------------------------------------------------------
    # Event emission
    # ------------------------------------------------------------------

    def _emit_event(self, event_type: str, payload: Any) -> None:
        if self._event_bus:
            try:
                self._event_bus.emit(event_type, payload)
            except Exception:
                logger.debug("Failed to emit event %s", event_type)

    def subscribe(self, event_type: str, handler: Any) -> None:
        if self._event_bus and hasattr(self._event_bus, "on"):
            self._event_bus.on(event_type, handler)
