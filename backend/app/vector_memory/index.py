"""Vector index management — incremental and bulk indexing."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from app.vector_memory.base import EmbeddingProvider, VectorRepository
from app.vector_memory.metrics import VectorMetrics, get_vector_metrics
from app.vector_memory.schemas import MemoryCategory, VectorMemoryDocument, VectorRecord

logger = logging.getLogger(__name__)


class VectorIndex:
    """Manages vector indexing — incremental, bulk, reindex, and optimization."""

    def __init__(
        self,
        repository: VectorRepository,
        embedder: EmbeddingProvider,
        metrics: Optional[VectorMetrics] = None,
    ) -> None:
        self._repository = repository
        self._embedder = embedder
        self._metrics = metrics or get_vector_metrics()

    async def index_document(
        self,
        document: VectorMemoryDocument,
        embedding: Optional[list[float]] = None,
    ) -> VectorRecord:
        start = time.monotonic()
        if embedding is None:
            emb_start = time.monotonic()
            embedding = await self._embedder.embed(document.content)
            emb_elapsed = (time.monotonic() - emb_start) * 1000
            self._metrics.record_embedding_latency(emb_elapsed)
            self._metrics.increment_vectors_indexed()

        import uuid
        record = VectorRecord(
            vector_id=str(uuid.uuid4()),
            source_id=document.source_id,
            document_id=document.document_id,
            memory_type=document.memory_type,
            content=document.content,
            user_id=document.user_id,
            session_id=document.session_id,
            tags=document.tags,
            confidence=document.confidence,
            importance=document.importance,
            embedding=embedding,
            embedding_provider=self._embedder.provider_id,
            metadata=document.metadata,
        )

        await self._repository.add([record])
        elapsed = (time.monotonic() - start) * 1000
        self._metrics.record_indexing_latency(elapsed)
        self._metrics.increment_vectors_stored()
        logger.debug(
            "Indexed document %s (category=%s, latency=%.1fms)",
            record.vector_id, document.memory_type.value, elapsed,
        )
        return record

    async def index_documents(
        self,
        documents: list[VectorMemoryDocument],
    ) -> list[VectorRecord]:
        records: list[VectorRecord] = []
        for doc in documents:
            record = await self.index_document(doc)
            records.append(record)
        return records

    async def index_batch(
        self,
        documents: list[VectorMemoryDocument],
    ) -> list[VectorRecord]:
        start = time.monotonic()
        texts = [d.content for d in documents]
        emb_start = time.monotonic()
        embeddings = await self._embedder.embed_batch(texts)
        emb_elapsed = (time.monotonic() - emb_start) * 1000
        self._metrics.record_embedding_latency(emb_elapsed)

        records: list[VectorRecord] = []
        import uuid
        for doc, emb in zip(documents, embeddings):
            record = VectorRecord(
                vector_id=str(uuid.uuid4()),
                source_id=doc.source_id,
                document_id=doc.document_id,
                memory_type=doc.memory_type,
                content=doc.content,
                user_id=doc.user_id,
                session_id=doc.session_id,
                tags=doc.tags,
                confidence=doc.confidence,
                importance=doc.importance,
                embedding=emb,
                embedding_provider=self._embedder.provider_id,
                metadata=doc.metadata,
            )
            records.append(record)

        await self._repository.add(records)
        elapsed = (time.monotonic() - start) * 1000
        self._metrics.record_indexing_latency(elapsed)
        self._metrics.increment_vectors_stored(len(records))
        self._metrics.increment_vectors_indexed(len(records))
        logger.debug("Batch indexed %d documents (latency=%.1fms)", len(records), elapsed)
        return records

    async def reindex(
        self,
        vector_ids: Optional[list[str]] = None,
        reindex_all: bool = False,
    ) -> list[VectorRecord]:
        if reindex_all:
            vector_ids = await self._repository.get_all_ids()
        if not vector_ids:
            return []

        records = []
        for vid in vector_ids:
            record = await self._repository.get(vid)
            if record and record.content:
                embedding = await self._embedder.embed(record.content)
                record.embedding = embedding
                record.embedding_provider = self._embedder.provider_id
                records.append(record)

        if records:
            await self._repository.update(records)
            self._metrics.increment_vectors_indexed(len(records))

        logger.debug("Reindexed %d vectors", len(records))
        return records

    async def delete_index(self, vector_ids: list[str]) -> int:
        count = await self._repository.delete(vector_ids)
        logger.debug("Deleted %d vectors from index", count)
        return count

    async def optimize_index(self) -> dict[str, Any]:
        total = await self._repository.count()
        by_category = await self._repository.count_by_category()
        return {
            "total_vectors": total,
            "vectors_by_category": by_category,
            "optimized": True,
        }

    async def get_document_count(self) -> int:
        return await self._repository.count()

    async def get_statistics(self) -> dict[str, Any]:
        total = await self._repository.count()
        by_category = await self._repository.count_by_category()
        return {
            "total_vectors": total,
            "vectors_by_category": by_category,
        }
