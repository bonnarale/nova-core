"""Long-Term Memory Manager — the main orchestrator facade.

Provides the public API for creating, retrieving, consolidating, and
managing the lifecycle of long-term memories.

Dependencies are injected via constructor (Strategy Pattern).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.long_term_memory.base import (
    ConsolidationStrategy,
    DeduplicationEngine,
    ImportanceScorer,
    LifecyclePolicy,
    MemoryRetriever,
    MemoryStore,
    MemorySummarizer,
)
from app.long_term_memory.consolidator import ContentHashDeduplicator, DefaultConsolidationStrategy
from app.long_term_memory.importance import MultiFactorImportanceScorer
from app.long_term_memory.lifecycle import DefaultLifecyclePolicy
from app.long_term_memory.models import (
    ConsolidationResult,
    ConsolidationSource,
    LifecycleResult,
    LongTermMemory,
    MemoryStatus,
    MemoryType,
    RetrievalResult,
)
from app.long_term_memory.retriever import SemanticMemoryRetriever, StoreRetriever
from app.long_term_memory.summarizer import ExtractiveMemorySummarizer

logger = logging.getLogger(__name__)


class LongTermMemoryManager:
    """Main orchestrator for Long-Term Memory operations.

    Usage::

        manager = LongTermMemoryManager(store=store, ...)
        memory = await manager.create_memory(...)
        results = await manager.search("user preferences")
        result = await manager.consolidate(source)
    """

    def __init__(
        self,
        store: MemoryStore,
        retriever: MemoryRetriever | None = None,
        consolidator: ConsolidationStrategy | None = None,
        importance_scorer: ImportanceScorer | None = None,
        summarizer: MemorySummarizer | None = None,
        deduplicator: DeduplicationEngine | None = None,
        lifecycle: LifecyclePolicy | None = None,
        embedder: Any = None,
    ) -> None:
        self._store = store
        self._importance_scorer = importance_scorer or MultiFactorImportanceScorer()
        self._summarizer = summarizer or ExtractiveMemorySummarizer()
        self._deduplicator = deduplicator or ContentHashDeduplicator(store)
        self._retriever = retriever or SemanticMemoryRetriever(
            store, embedder=embedder
        )
        self._consolidator = consolidator or DefaultConsolidationStrategy(
            store=store,
            importance_scorer=self._importance_scorer,
            summarizer=self._summarizer,
            deduplicator=self._deduplicator,
        )
        self._lifecycle = lifecycle or DefaultLifecyclePolicy(store=store)

    # ------------------------------------------------------------------
    # Properties for pluggable components
    # ------------------------------------------------------------------

    @property
    def store(self) -> MemoryStore:
        return self._store

    @property
    def retriever(self) -> MemoryRetriever:
        return self._retriever

    @property
    def consolidator(self) -> ConsolidationStrategy:
        return self._consolidator

    @property
    def lifecycle(self) -> LifecyclePolicy:
        return self._lifecycle

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    async def create_memory(
        self,
        content: str,
        memory_type: str = MemoryType.KNOWLEDGE.value,
        source: str = "system",
        source_id: str | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        agent_id: str | None = None,
        tags: list[str] | None = None,
        categories: list[str] | None = None,
        entities: list[str] | None = None,
        importance_score: float | None = None,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LongTermMemory:
        if importance_score is None:
            importance_score = await self._importance_scorer.score(
                content=content, source=source
            )

        summary = await self._summarizer.summarize(content)
        now = datetime.now(tz=timezone.utc).isoformat()

        memory = LongTermMemory(
            id=LongTermMemory.new_id(),
            memory_type=memory_type,
            content=content,
            summary=summary,
            tags=tags or [],
            categories=categories or [],
            entities=entities or [],
            importance_score=importance_score,
            source=source,
            source_id=source_id,
            user_id=user_id,
            project_id=project_id,
            agent_id=agent_id,
            embedding=embedding,
            metadata=metadata or {},
            created_at=now,
            accessed_at=now,
            updated_at=now,
        )

        created = await self._store.create(memory)
        logger.debug(
            "Created LTM id=%s type=%s source=%s importance=%.1f",
            created.id, memory_type, source, importance_score,
        )
        return created

    async def get_memory(self, memory_id: str) -> LongTermMemory | None:
        memory = await self._store.get(memory_id)
        if memory:
            memory.access_count += 1
            memory.accessed_at = datetime.now(tz=timezone.utc).isoformat()
            try:
                await self._store.update(memory)
            except Exception:
                logger.debug("Could not update access stats for %s", memory_id)
        return memory

    async def update_memory(
        self, memory: LongTermMemory
    ) -> LongTermMemory | None:
        memory.updated_at = datetime.now(tz=timezone.utc).isoformat()
        return await self._store.update(memory)

    async def delete_memory(self, memory_id: str) -> bool:
        memory = await self._store.get(memory_id)
        if memory is None:
            return False
        memory.status = MemoryStatus.DELETED.value
        memory.updated_at = datetime.now(tz=timezone.utc).isoformat()
        result = await self._store.update(memory)
        return result is not None

    async def permanent_delete(self, memory_id: str) -> bool:
        return await self._store.delete(memory_id)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        memory_type: str | None = None,
        user_id: str | None = None,
        limit: int = 10,
    ) -> RetrievalResult:
        return await self._retriever.search(
            query=query,
            memory_type=memory_type,
            user_id=user_id,
            limit=limit,
        )

    async def get_by_tags(
        self,
        tags: list[str],
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[LongTermMemory]:
        return await self._store.search_by_tags(tags, memory_type, limit)

    async def get_by_entity(
        self, entity: str, limit: int = 50
    ) -> list[LongTermMemory]:
        return await self._store.search_by_entity(entity, limit)

    async def get_by_user(
        self,
        user_id: str,
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[LongTermMemory]:
        return await self._store.list_by_user(user_id, memory_type, limit=limit)

    async def get_related(
        self, memory_id: str, limit: int = 20
    ) -> list[LongTermMemory]:
        return await self._store.get_related(memory_id, limit)

    # ------------------------------------------------------------------
    # Consolidation
    # ------------------------------------------------------------------

    async def consolidate(self, source: ConsolidationSource) -> ConsolidationResult:
        created_memories = await self._consolidator.consolidate(source)

        linked_ids = []
        for mem in created_memories:
            await self._store.create(mem)
            linked_ids.append(mem.id)

        links_created = 0
        if len(linked_ids) > 1:
            for i, mem_id in enumerate(linked_ids):
                others = [lid for lid in linked_ids if lid != mem_id]
                memory = await self._store.get(mem_id)
                if memory:
                    current_links = list(memory.linked_memory_ids or [])
                    for oid in others:
                        if oid not in current_links:
                            current_links.append(oid)
                            links_created += 1
                    memory.linked_memory_ids = current_links
                    memory.updated_at = datetime.now(tz=timezone.utc).isoformat()
                    await self._store.update(memory)

        return ConsolidationResult(
            created=[m.id for m in created_memories],
            links_created=links_created,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def run_lifecycle(self) -> LifecycleResult:
        aged = await self._lifecycle.age_memories()
        archived = await self._lifecycle.archive_memories()
        purged = await self._lifecycle.purge_deleted()
        return LifecycleResult(aged=aged, archived=archived, purged=purged)

    # ------------------------------------------------------------------
    # Summarization
    # ------------------------------------------------------------------

    async def get_summary(
        self, memory_id: str, max_length: int = 200
    ) -> str | None:
        memory = await self._store.get(memory_id)
        if memory is None:
            return None
        if memory.summary:
            return memory.summary
        summary = await self._summarizer.summarize(memory.content, max_length)
        memory.summary = summary
        memory.updated_at = datetime.now(tz=timezone.utc).isoformat()
        await self._store.update(memory)
        return summary

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def count_by_status(self) -> dict[str, int]:
        return await self._store.count_by_status()
