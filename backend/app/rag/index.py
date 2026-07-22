"""RAG index management — handle document ingestion and index operations."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from app.rag.base import Chunker, EmbeddingProvider, VectorRepository
from app.rag.chunker import get_chunker
from app.rag.metrics import RAGMetrics
from app.rag.schemas import (
    Chunk,
    ChunkMetadata,
    ChunkStrategy,
    DocumentStatus,
    FilterCondition,
    IndexDocument,
    IndexResult,
)

logger = logging.getLogger(__name__)


class RAGIndex:
    """Manages document indexing into the vector repository."""

    def __init__(
        self,
        repository: VectorRepository,
        embedder: EmbeddingProvider,
        chunker: Optional[Chunker] = None,
        metrics: Optional[RAGMetrics] = None,
        collection: str = "documents",
    ) -> None:
        self._repository = repository
        self._embedder = embedder
        self._chunker = chunker or get_chunker(ChunkStrategy.RECURSIVE)
        self._metrics = metrics
        self._collection = collection
        self._document_registry: dict[str, dict[str, Any]] = {}

    @property
    def repository(self) -> VectorRepository:
        return self._repository

    @property
    def embedder(self) -> EmbeddingProvider:
        return self._embedder

    @property
    def collection(self) -> str:
        return self._collection

    async def index_document(self, doc: IndexDocument) -> IndexResult:
        start_time = time.time()
        try:
            metadata = ChunkMetadata(
                document_id=doc.document_id,
                source_id=doc.source,
                title=doc.title,
                strategy=doc.chunk_strategy,
                tags=doc.tags,
                source=doc.source,
                author=doc.author,
                category=doc.category,
                language=doc.language,
                confidence=1.0,
                metadata=doc.metadata,
            )
            chunks = await self._chunker.chunk(
                doc.content,
                metadata,
                doc.chunk_size,
                doc.chunk_overlap,
            )
            if not chunks:
                return IndexResult(
                    document_id=doc.document_id,
                    chunks_created=0,
                    chunks_indexed=0,
                    status=DocumentStatus.INDEXED,
                    latency_ms=(time.time() - start_time) * 1000,
                )
            texts = [c.content for c in chunks]
            embeddings = await self._embedder.embed_batch(texts)
            indexed = await self._repository.add(self._collection, chunks, embeddings)
            self._document_registry[doc.document_id] = {
                "title": doc.title,
                "source": doc.source,
                "chunk_count": len(chunks),
                "indexed_at": time.time(),
            }
            if self._metrics:
                self._metrics.record_document_indexed(len(chunks))
            latency_ms = (time.time() - start_time) * 1000
            return IndexResult(
                document_id=doc.document_id,
                chunks_created=len(chunks),
                chunks_indexed=indexed,
                status=DocumentStatus.INDEXED,
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("Failed to index document %s: %s", doc.document_id, e)
            return IndexResult(
                document_id=doc.document_id,
                chunks_created=0,
                chunks_indexed=0,
                status=DocumentStatus.FAILED,
                latency_ms=latency_ms,
                error=str(e),
            )

    async def index_documents(self, docs: list[IndexDocument]) -> list[IndexResult]:
        results: list[IndexResult] = []
        for doc in docs:
            result = await self.index_document(doc)
            results.append(result)
        return results

    async def remove_document(self, document_id: str) -> int:
        all_ids = await self._repository.get_all_ids(self._collection)
        doc_info = self._document_registry.get(document_id, {})
        chunk_count = doc_info.get("chunk_count", 0)
        removed = await self._repository.delete(self._collection, all_ids[:chunk_count] if chunk_count else all_ids)
        self._document_registry.pop(document_id, None)
        if self._metrics:
            self._metrics.record_document_removed(removed)
        return removed

    async def reindex_document(self, document_id: str, doc: IndexDocument) -> IndexResult:
        await self.remove_document(document_id)
        return await self.index_document(doc)

    async def count(self) -> int:
        return await self._repository.count(self._collection)

    async def get_document_count(self) -> int:
        return len(self._document_registry)

    async def get_statistics(self) -> dict[str, Any]:
        chunk_count = await self.count()
        doc_count = await self.get_document_count()
        source_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        for info in self._document_registry.values():
            src = info.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1
        return {
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "source_counts": source_counts,
            "category_counts": category_counts,
            "average_chunk_size": 0.0,
            "index_size_bytes": 0,
        }

    async def health(self) -> dict[str, Any]:
        return await self._repository.health()
