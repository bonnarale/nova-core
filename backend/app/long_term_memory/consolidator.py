"""Consolidation engine — converts ephemeral data into durable Long-Term Memories.

Sources:
- Conversation history → USER / KNOWLEDGE memories
- Profile data → USER memories
- Goals → GOAL memories (via source="goal")
- Completed tasks → KNOWLEDGE memories
- Semantic memories → KNOWLEDGE memories
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.long_term_memory.base import ConsolidationStrategy, DeduplicationEngine, ImportanceScorer, MemorySummarizer
from app.long_term_memory.importance import FixedImportanceScorer, MultiFactorImportanceScorer
from app.long_term_memory.models import ConsolidationResult, ConsolidationSource, LongTermMemory, MemoryType
from app.long_term_memory.summarizer import TruncationSummarizer

logger = logging.getLogger(__name__)


class ContentHashDeduplicator(DeduplicationEngine):
    """Simple dedup using content hash matching."""

    def __init__(self, store: Any) -> None:
        self._store = store

    async def find_duplicates(
        self,
        content: str,
        memory_type: str | None = None,
        threshold: float = 0.9,
    ) -> list[LongTermMemory]:
        content_stripped = content.strip().lower()
        if not content_stripped:
            return []

        candidates = await self._store.list_by_type(
            memory_type or MemoryType.KNOWLEDGE.value,
            status="active",
            limit=200,
        )
        duplicates: list[LongTermMemory] = []
        for mem in candidates:
            mem_content = (mem.content or "").strip().lower()
            if mem_content == content_stripped:
                duplicates.append(mem)
                continue
            similarity = self._jaccard_similarity(content_stripped, mem_content)
            if similarity >= threshold:
                duplicates.append(mem)

        return duplicates

    @staticmethod
    def _jaccard_similarity(a: str, b: str) -> float:
        set_a = set(a.split())
        set_b = set(b.split())
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)


class DefaultConsolidationStrategy(ConsolidationStrategy):
    """Default strategy that consolidates all available sources."""

    def __init__(
        self,
        store: Any,
        importance_scorer: ImportanceScorer | None = None,
        summarizer: MemorySummarizer | None = None,
        deduplicator: DeduplicationEngine | None = None,
    ) -> None:
        self._store = store
        self._importance_scorer = importance_scorer or MultiFactorImportanceScorer()
        self._summarizer = summarizer or TruncationSummarizer()
        self._deduplicator = deduplicator or ContentHashDeduplicator(store)

    async def consolidate(
        self, source: ConsolidationSource
    ) -> list[LongTermMemory]:
        created: list[LongTermMemory] = []

        if source.conversations:
            memories = await self._consolidate_conversations(source)
            created.extend(memories)

        if source.profile:
            memories = await self._consolidate_profile(source)
            created.extend(memories)

        if source.goals:
            memories = await self._consolidate_goals(source)
            created.extend(memories)

        if source.completed_tasks:
            memories = await self._consolidate_tasks(source)
            created.extend(memories)

        if source.semantic_memories:
            memories = await self._consolidate_semantic(source)
            created.extend(memories)

        return created

    async def _consolidate_conversations(
        self, source: ConsolidationSource
    ) -> list[LongTermMemory]:
        memories: list[LongTermMemory] = []
        for msg in source.conversations:
            content = msg.get("content", "").strip()
            if not content or len(content) < 20:
                continue
            role = msg.get("role", "user")
            memory = await self._build_memory(
                content=content,
                memory_type=MemoryType.USER if role == "user" else MemoryType.KNOWLEDGE,
                source="conversation",
                source_id=msg.get("id"),
                user_id=source.user_id,
                project_id=source.project_id,
                tags=["conversation", role],
                entities=[role],
            )
            if memory:
                memories.append(memory)
        return memories

    async def _consolidate_profile(
        self, source: ConsolidationSource
    ) -> list[LongTermMemory]:
        memories: list[LongTermMemory] = []
        profile = source.profile or {}

        name = profile.get("name")
        if name:
            memory = await self._build_memory(
                content=f"User name is {name}",
                memory_type=MemoryType.USER,
                source="profile",
                user_id=source.user_id,
                tags=["profile", "name"],
                entities=["user"],
            )
            if memory:
                memories.append(memory)

        for fact in profile.get("facts") or []:
            if not fact or not fact.strip():
                continue
            memory = await self._build_memory(
                content=fact,
                memory_type=MemoryType.USER,
                source="profile",
                user_id=source.user_id,
                tags=["profile", "fact"],
                entities=["user"],
            )
            if memory:
                memories.append(memory)

        bio = profile.get("bio")
        if bio and bio.strip():
            memory = await self._build_memory(
                content=bio,
                memory_type=MemoryType.USER,
                source="profile",
                user_id=source.user_id,
                tags=["profile", "bio"],
                entities=["user"],
            )
            if memory:
                memories.append(memory)

        return memories

    async def _consolidate_goals(
        self, source: ConsolidationSource
    ) -> list[LongTermMemory]:
        memories: list[LongTermMemory] = []
        for goal in source.goals:
            title = goal.get("title", "").strip()
            if not title:
                continue
            content_parts = [f"Goal: {title}"]
            desc = goal.get("description", "").strip()
            if desc:
                content_parts.append(desc)
            status = goal.get("status", "active")

            memory = await self._build_memory(
                content=". ".join(content_parts),
                memory_type=MemoryType.KNOWLEDGE,
                source="goal",
                source_id=goal.get("id"),
                user_id=source.user_id,
                tags=["goal", status],
                entities=["goal"],
            )
            if memory:
                memories.append(memory)
        return memories

    async def _consolidate_tasks(
        self, source: ConsolidationSource
    ) -> list[LongTermMemory]:
        memories: list[LongTermMemory] = []
        for task in source.completed_tasks:
            goal_text = task.get("goal", "").strip()
            if not goal_text:
                continue
            memory = await self._build_memory(
                content=f"Completed task: {goal_text}",
                memory_type=MemoryType.KNOWLEDGE,
                source="task",
                source_id=task.get("id"),
                user_id=source.user_id,
                tags=["task", "completed"],
                entities=["task"],
            )
            if memory:
                memories.append(memory)
        return memories

    async def _consolidate_semantic(
        self, source: ConsolidationSource
    ) -> list[LongTermMemory]:
        memories: list[LongTermMemory] = []
        for sem in source.semantic_memories:
            content = sem.get("content", "").strip()
            if not content:
                continue
            memory = await self._build_memory(
                content=content,
                memory_type=MemoryType.KNOWLEDGE,
                source="semantic",
                source_id=sem.get("session_id"),
                user_id=source.user_id,
                tags=["semantic", sem.get("source", "unknown")],
                entities=["knowledge"],
            )
            if memory:
                memories.append(memory)
        return memories

    async def _build_memory(
        self,
        content: str,
        memory_type: MemoryType,
        source: str,
        source_id: str | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        tags: list[str] | None = None,
        entities: list[str] | None = None,
    ) -> LongTermMemory | None:
        if self._deduplicator:
            duplicates = await self._deduplicator.find_duplicates(
                content, memory_type=memory_type.value
            )
            if duplicates:
                logger.debug(
                    "Skipping duplicate memory of type %s from source %s",
                    memory_type.value, source,
                )
                return None

        now = datetime.now(tz=timezone.utc).isoformat()
        summary = await self._summarizer.summarize(content)
        importance = await self._importance_scorer.score(
            content=content,
            source=source,
        )

        return LongTermMemory(
            id=LongTermMemory.new_id(),
            memory_type=memory_type.value,
            content=content,
            summary=summary,
            tags=tags or [],
            entities=entities or [],
            importance_score=importance,
            source=source,
            source_id=source_id,
            user_id=user_id,
            project_id=project_id,
            created_at=now,
            accessed_at=now,
            updated_at=now,
        )
