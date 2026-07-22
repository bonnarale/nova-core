"""Tests for Long-Term Memory v1 — models, base, importance, summarizer,
consolidator, lifecycle, retriever, manager, schemas, and integration
with CognitiveEngine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.long_term_memory.base import (
    ConsolidationStrategy,
    DeduplicationEngine,
    ImportanceScorer,
    LifecyclePolicy,
    MemoryRetriever,
    MemoryStore,
    MemorySummarizer,
)
from app.long_term_memory.consolidator import (
    ContentHashDeduplicator,
    DefaultConsolidationStrategy,
)
from app.long_term_memory.importance import (
    FixedImportanceScorer,
    MultiFactorImportanceScorer,
)
from app.long_term_memory.lifecycle import DefaultLifecyclePolicy
from app.long_term_memory.manager import LongTermMemoryManager
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
from app.long_term_memory.schemas import (
    ConsolidateRequest,
    ConsolidateResponse,
    LifecycleResponse,
    MemoryCreate,
    MemoryResponse,
    MemorySearchResult,
    MemoryUpdate,
    StatsResponse,
)
from app.long_term_memory.summarizer import (
    ExtractiveMemorySummarizer,
    TruncationSummarizer,
)


# ======================================================================
# Fake in-memory store for tests
# ======================================================================


class FakeMemoryStore(MemoryStore):
    """In-memory implementation of MemoryStore for testing."""

    def __init__(self) -> None:
        self._memories: dict[str, LongTermMemory] = {}

    async def create(self, memory: LongTermMemory) -> LongTermMemory:
        self._memories[memory.id] = memory
        return memory

    async def get(self, memory_id: str) -> LongTermMemory | None:
        return self._memories.get(memory_id)

    async def update(self, memory: LongTermMemory) -> LongTermMemory | None:
        if memory.id not in self._memories:
            return None
        self._memories[memory.id] = memory
        return memory

    async def delete(self, memory_id: str) -> bool:
        return self._memories.pop(memory_id, None) is not None

    async def list_by_user(
        self,
        user_id: str,
        memory_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LongTermMemory]:
        results = [
            m for m in self._memories.values()
            if m.user_id == user_id
        ]
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        if status:
            results = [m for m in results if m.status == status]
        return results[offset:offset + limit]

    async def list_by_type(
        self,
        memory_type: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[LongTermMemory]:
        results = [
            m for m in self._memories.values()
            if m.memory_type == memory_type
        ]
        if status:
            results = [m for m in results if m.status == status]
        return results[:limit]

    async def search_by_tags(
        self,
        tags: list[str],
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[LongTermMemory]:
        tag_set = set(tags)
        results = [
            m for m in self._memories.values()
            if tag_set & set(m.tags)
        ]
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        return results[:limit]

    async def search_by_entity(
        self, entity: str, limit: int = 50
    ) -> list[LongTermMemory]:
        return [
            m for m in self._memories.values()
            if entity in m.entities
        ][:limit]

    async def get_related(
        self, memory_id: str, limit: int = 20
    ) -> list[LongTermMemory]:
        memory = self._memories.get(memory_id)
        if not memory:
            return []
        linked = memory.linked_memory_ids or []
        return [
            m for m in self._memories.values()
            if m.id in linked
        ][:limit]

    async def list_aging(
        self, age_days: int = 30, limit: int = 100
    ) -> list[LongTermMemory]:
        return [
            m for m in self._memories.values()
            if m.status == MemoryStatus.ACTIVE.value
        ][:limit]

    async def list_archivable(
        self, min_age_days: int = 90, importance_below: int = 30, limit: int = 100
    ) -> list[LongTermMemory]:
        return [
            m for m in self._memories.values()
            if m.status == MemoryStatus.ACTIVE.value
            and m.importance_score < importance_below
        ][:limit]

    async def count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for m in self._memories.values():
            counts[m.status] = counts.get(m.status, 0) + 1
        return counts


# ======================================================================
# Models tests
# ======================================================================


class TestLongTermMemoryModel:
    def test_default_creation(self):
        mem = LongTermMemory(
            id="m1", memory_type="user", content="test content", source="test"
        )
        assert mem.id == "m1"
        assert mem.memory_type == "user"
        assert mem.status == MemoryStatus.ACTIVE.value
        assert mem.importance_score == 0.0
        assert mem.tags == []
        assert mem.linked_memory_ids == []

    def test_new_id_generates_uuid(self):
        id1 = LongTermMemory.new_id()
        id2 = LongTermMemory.new_id()
        assert id1 != id2
        UUID(id1)  # should not raise

    def test_to_dict(self):
        mem = LongTermMemory(
            id="m1",
            memory_type="knowledge",
            content="important knowledge",
            source="system",
            importance_score=85.0,
            tags=["tag1"],
        )
        d = mem.to_dict()
        assert d["id"] == "m1"
        assert d["memory_type"] == "knowledge"
        assert d["importance_score"] == 85.0
        assert d["tags"] == ["tag1"]

    def test_from_dict(self):
        data = {
            "id": "m1",
            "memory_type": "user",
            "content": "user fact",
            "source": "profile",
            "importance_score": 50.0,
            "tags": ["fact"],
        }
        mem = LongTermMemory.from_dict(data)
        assert mem.id == "m1"
        assert mem.content == "user fact"
        assert mem.importance_score == 50.0

    def test_from_dict_ignores_extra_keys(self):
        data = {"id": "m1", "memory_type": "user", "content": "x", "source": "s", "invalid": True}
        mem = LongTermMemory.from_dict(data)
        assert not hasattr(mem, "invalid")


class TestMemoryTypeEnum:
    def test_values(self):
        assert MemoryType.USER.value == "user"
        assert MemoryType.PROJECT.value == "project"
        assert MemoryType.AGENT.value == "agent"
        assert MemoryType.KNOWLEDGE.value == "knowledge"
        assert MemoryType.SYSTEM.value == "system"
        assert MemoryType.PREFERENCE.value == "preference"
        assert MemoryType.ERROR_PATTERN.value == "error_pattern"

    def test_all_members(self):
        assert len(MemoryType) == 7


class TestMemoryStatusEnum:
    def test_values(self):
        assert MemoryStatus.ACTIVE.value == "active"
        assert MemoryStatus.CONSOLIDATED.value == "consolidated"
        assert MemoryStatus.ARCHIVED.value == "archived"
        assert MemoryStatus.DELETED.value == "deleted"

    def test_all_members(self):
        assert len(MemoryStatus) == 4


class TestConsolidationResult:
    def test_defaults(self):
        r = ConsolidationResult()
        assert r.created == []
        assert r.duplicates_skipped == 0
        assert r.links_created == 0


class TestLifecycleResult:
    def test_defaults(self):
        r = LifecycleResult()
        assert r.aged == 0
        assert r.archived == 0
        assert r.purged == 0


# ======================================================================
# Base ABC tests
# ======================================================================


class TestBaseABCs:
    def test_memory_store_is_abstract(self):
        with pytest.raises(TypeError):
            MemoryStore()  # type: ignore

    def test_memory_retriever_is_abstract(self):
        with pytest.raises(TypeError):
            MemoryRetriever()  # type: ignore

    def test_consolidation_strategy_is_abstract(self):
        with pytest.raises(TypeError):
            ConsolidationStrategy()  # type: ignore

    def test_importance_scorer_is_abstract(self):
        with pytest.raises(TypeError):
            ImportanceScorer()  # type: ignore

    def test_memory_summarizer_is_abstract(self):
        with pytest.raises(TypeError):
            MemorySummarizer()  # type: ignore

    def test_lifecycle_policy_is_abstract(self):
        with pytest.raises(TypeError):
            LifecyclePolicy()  # type: ignore

    def test_deduplication_engine_is_abstract(self):
        with pytest.raises(TypeError):
            DeduplicationEngine()  # type: ignore


# ======================================================================
# Importance scorer tests
# ======================================================================


class TestMultiFactorImportanceScorer:
    @pytest.fixture
    def scorer(self) -> MultiFactorImportanceScorer:
        return MultiFactorImportanceScorer()

    @pytest.mark.asyncio
    async def test_score_recency_recent(self, scorer: MultiFactorImportanceScorer):
        score = await scorer.score(
            content="Recent important content",
            source="conversation",
            recency_hours=0.5,
        )
        assert 0 <= score <= 100
        assert score > 40

    @pytest.mark.asyncio
    async def test_score_recency_old(self, scorer: MultiFactorImportanceScorer):
        score = await scorer.score(
            content="Old content",
            source="conversation",
            recency_hours=5000,
        )
        assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_score_with_entities(self, scorer: MultiFactorImportanceScorer):
        score = await scorer.score(
            content="Content with many entities",
            source="goal",
            entities=["entity1", "entity2", "entity3", "entity4"],
        )
        assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_score_profile_higher_than_conversation(self, scorer: MultiFactorImportanceScorer):
        profile_score = await scorer.score(
            content="Profile info", source="profile"
        )
        conv_score = await scorer.score(
            content="Chat message", source="conversation"
        )
        assert profile_score >= conv_score

    @pytest.mark.asyncio
    async def test_score_with_access_count(self, scorer: MultiFactorImportanceScorer):
        low = await scorer.score(content="test", source="system", access_count=0)
        high = await scorer.score(content="test", source="system", access_count=50)
        assert high >= low

    @pytest.mark.asyncio
    async def test_score_no_recency(self, scorer: MultiFactorImportanceScorer):
        score = await scorer.score(content="test", source="system")
        assert 0 <= score <= 100


class TestFixedImportanceScorer:
    @pytest.mark.asyncio
    async def test_fixed_score(self):
        scorer = FixedImportanceScorer(fixed_score=42.0)
        score = await scorer.score(content="anything", source="any")
        assert score == 42.0

    @pytest.mark.asyncio
    async def test_default_score(self):
        scorer = FixedImportanceScorer()
        score = await scorer.score(content="x", source="y")
        assert score == 50.0


# ======================================================================
# Summarizer tests
# ======================================================================


class TestExtractiveMemorySummarizer:
    @pytest.fixture
    def summarizer(self) -> ExtractiveMemorySummarizer:
        return ExtractiveMemorySummarizer()

    @pytest.mark.asyncio
    async def test_summarize_short_content(self, summarizer: ExtractiveMemorySummarizer):
        result = await summarizer.summarize("Hello world")
        assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_summarize_empty(self, summarizer: ExtractiveMemorySummarizer):
        result = await summarizer.summarize("")
        assert result == ""

    @pytest.mark.asyncio
    async def test_summarize_long_content(self, summarizer: ExtractiveMemorySummarizer):
        content = ". ".join([f"This is sentence number {i}" for i in range(100)])
        result = await summarizer.summarize(content, max_length=100)
        assert len(result) <= 150  # some slack for punctuation
        assert result
        assert "sentence" in result

    @pytest.mark.asyncio
    async def test_summarize_with_max_length(self, summarizer: ExtractiveMemorySummarizer):
        content = "A long " + "word " * 200
        result = await summarizer.summarize(content, max_length=50)
        assert len(result) <= 100
        assert result


class TestTruncationSummarizer:
    @pytest.fixture
    def summarizer(self) -> TruncationSummarizer:
        return TruncationSummarizer()

    @pytest.mark.asyncio
    async def test_truncate_long(self, summarizer: TruncationSummarizer):
        content = "Hello " * 100
        result = await summarizer.summarize(content, max_length=20)
        assert len(result) < len(content)
        assert result.endswith("...")

    @pytest.mark.asyncio
    async def test_truncate_short(self, summarizer: TruncationSummarizer):
        result = await summarizer.summarize("Short text", max_length=200)
        assert result == "Short text"


# ======================================================================
# Deduplicator tests
# ======================================================================


class TestContentHashDeduplicator:
    @pytest.mark.asyncio
    async def test_find_duplicates_exact_match(self):
        store = FakeMemoryStore()
        await store.create(LongTermMemory(
            id="existing", memory_type="knowledge", content="Hello world",
            source="test", status="active",
        ))
        dedup = ContentHashDeduplicator(store)
        duplicates = await dedup.find_duplicates("Hello world", memory_type="knowledge")
        assert len(duplicates) == 1
        assert duplicates[0].id == "existing"

    @pytest.mark.asyncio
    async def test_find_duplicates_no_match(self):
        store = FakeMemoryStore()
        dedup = ContentHashDeduplicator(store)
        duplicates = await dedup.find_duplicates("Unique content", memory_type="knowledge")
        assert duplicates == []

    @pytest.mark.asyncio
    async def test_find_duplicates_empty_content(self):
        store = FakeMemoryStore()
        dedup = ContentHashDeduplicator(store)
        duplicates = await dedup.find_duplicates("")
        assert duplicates == []

    def test_jaccard_similarity(self):
        sim = ContentHashDeduplicator._jaccard_similarity("a b c", "a b d")
        assert sim == 0.5

    def test_jaccard_identical(self):
        sim = ContentHashDeduplicator._jaccard_similarity("a b c", "a b c")
        assert sim == 1.0

    def test_jaccard_empty(self):
        sim = ContentHashDeduplicator._jaccard_similarity("", "")
        assert sim == 0.0


# ======================================================================
# Consolidator tests
# ======================================================================


class TestDefaultConsolidationStrategy:
    @pytest.fixture
    def store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def strategy(self, store: FakeMemoryStore) -> DefaultConsolidationStrategy:
        return DefaultConsolidationStrategy(
            store=store,
            importance_scorer=FixedImportanceScorer(50.0),
        )

    @pytest.mark.asyncio
    async def test_consolidate_conversations(
        self, strategy: DefaultConsolidationStrategy
    ):
        source = ConsolidationSource(
            conversations=[
                {"role": "user", "content": "My name is Alice and I like Python"},
                {"role": "assistant", "content": "That's interesting Alice"},
            ],
            user_id="user-1",
        )
        result = await strategy.consolidate(source)
        assert len(result) == 2
        assert result[0].memory_type == "user"
        assert result[1].memory_type == "knowledge"
        assert result[0].user_id == "user-1"

    @pytest.mark.asyncio
    async def test_consolidate_skips_short_messages(
        self, strategy: DefaultConsolidationStrategy
    ):
        source = ConsolidationSource(
            conversations=[
                {"role": "user", "content": "Hi"},
            ],
        )
        result = await strategy.consolidate(source)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_consolidate_profile(
        self, strategy: DefaultConsolidationStrategy
    ):
        source = ConsolidationSource(
            profile={
                "name": "Bob",
                "facts": ["Loves hiking", "Works at Acme"],
                "bio": "Software engineer from SF",
            },
            user_id="user-2",
        )
        result = await strategy.consolidate(source)
        assert len(result) >= 3
        assert all(m.memory_type == "user" for m in result)

    @pytest.mark.asyncio
    async def test_consolidate_goals(
        self, strategy: DefaultConsolidationStrategy
    ):
        source = ConsolidationSource(
            goals=[
                {"id": "g1", "title": "Learn Rust", "status": "active"},
                {"id": "g2", "title": "Build an app", "description": "A web app with React"},
            ],
        )
        result = await strategy.consolidate(source)
        assert len(result) >= 2
        assert all(m.memory_type == "knowledge" for m in result)
        assert all(m.source == "goal" for m in result)

    @pytest.mark.asyncio
    async def test_consolidate_tasks(
        self, strategy: DefaultConsolidationStrategy
    ):
        source = ConsolidationSource(
            completed_tasks=[
                {"id": "t1", "goal": "Deploy the API", "status": "completed"},
            ],
        )
        result = await strategy.consolidate(source)
        assert len(result) >= 1
        assert "Deploy the API" in result[0].content

    @pytest.mark.asyncio
    async def test_consolidate_semantic(
        self, strategy: DefaultConsolidationStrategy
    ):
        source = ConsolidationSource(
            semantic_memories=[
                {"content": "Alice prefers functional programming", "source": "extracted"},
            ],
        )
        result = await strategy.consolidate(source)
        assert len(result) >= 1
        assert result[0].memory_type == "knowledge"

    @pytest.mark.asyncio
    async def test_consolidate_empty_source(
        self, strategy: DefaultConsolidationStrategy
    ):
        source = ConsolidationSource()
        result = await strategy.consolidate(source)
        assert result == []


# ======================================================================
# Lifecycle tests
# ======================================================================


class TestDefaultLifecyclePolicy:
    @pytest.fixture
    def store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def policy(self, store: FakeMemoryStore) -> DefaultLifecyclePolicy:
        return DefaultLifecyclePolicy(store=store, batch_size=10)

    @pytest.mark.asyncio
    async def test_age_memories_decreases_importance(
        self, store: FakeMemoryStore, policy: DefaultLifecyclePolicy
    ):
        mem = LongTermMemory(
            id="m1", memory_type="user", content="test", source="test",
            status="active", importance_score=100.0,
        )
        await store.create(mem)
        aged = await policy.age_memories()
        assert aged >= 1
        updated = await store.get("m1")
        assert updated is not None
        assert updated.importance_score < 100.0

    @pytest.mark.asyncio
    async def test_archive_memories(
        self, store: FakeMemoryStore, policy: DefaultLifecyclePolicy
    ):
        mem = LongTermMemory(
            id="m2", memory_type="user", content="old", source="test",
            status="active", importance_score=5.0,
        )
        await store.create(mem)
        archived = await policy.archive_memories()
        assert archived >= 1
        updated = await store.get("m2")
        assert updated is not None
        assert updated.status == MemoryStatus.ARCHIVED.value

    @pytest.mark.asyncio
    async def test_purge_deleted(
        self, store: FakeMemoryStore, policy: DefaultLifecyclePolicy
    ):
        mem = LongTermMemory(
            id="m3", memory_type="user", content="to-purge", source="test",
            status="deleted",
            updated_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        await store.create(mem)
        purged = await policy.purge_deleted()
        assert purged == 0  # just created, not past purge threshold

    @pytest.mark.asyncio
    async def test_lifecycle_empty(self, policy: DefaultLifecyclePolicy):
        aged = await policy.age_memories()
        archived = await policy.archive_memories()
        purged = await policy.purge_deleted()
        assert aged == 0
        assert archived == 0
        assert purged == 0


# ======================================================================
# Retriever tests
# ======================================================================


class TestSemanticMemoryRetriever:
    @pytest.fixture
    def store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def embedder(self):
        emb = AsyncMock()
        emb.embed.return_value = [0.1, 0.2, 0.3]
        return emb

    @pytest.fixture
    def retriever(
        self, store: FakeMemoryStore, embedder
    ) -> SemanticMemoryRetriever:
        return SemanticMemoryRetriever(store, embedder=embedder)

    @pytest.mark.asyncio
    async def test_search_fallback_when_no_embedding(
        self, store: FakeMemoryStore
    ):
        retriever = SemanticMemoryRetriever(store, embedder=None)
        mem = LongTermMemory(
            id="m1", memory_type="knowledge", content="Python programming",
            source="test", status="active", tags=["python"],
        )
        await store.create(mem)
        result = await retriever.search("python", memory_type="knowledge")
        assert result.total >= 1

    @pytest.mark.asyncio
    async def test_search_similar(
        self, store: FakeMemoryStore, retriever: SemanticMemoryRetriever
    ):
        mem = LongTermMemory(
            id="m1", memory_type="knowledge", content="Some content",
            source="test", embedding=[0.1, 0.2, 0.3],
        )
        await store.create(mem)
        result = await retriever.search_similar(
            "some content", memory_type="knowledge"
        )
        assert result.total >= 1


class TestStoreRetriever:
    @pytest.fixture
    def store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def retriever(self, store: FakeMemoryStore) -> StoreRetriever:
        return StoreRetriever(store)

    @pytest.mark.asyncio
    async def test_search_by_user(
        self, store: FakeMemoryStore, retriever: StoreRetriever
    ):
        mem = LongTermMemory(
            id="m1", memory_type="user", content="Prefers dark mode",
            source="profile", user_id="u1",
        )
        await store.create(mem)
        result = await retriever.search("preferences", user_id="u1")
        assert result.total >= 1

    @pytest.mark.asyncio
    async def test_search_by_type(
        self, store: FakeMemoryStore, retriever: StoreRetriever
    ):
        mem = LongTermMemory(
            id="m2", memory_type="knowledge", content="API docs",
            source="system",
        )
        await store.create(mem)
        result = await retriever.search("api", memory_type="knowledge")
        assert result.total >= 1

    @pytest.mark.asyncio
    async def test_search_empty(
        self, retriever: StoreRetriever
    ):
        result = await retriever.search("nothing", memory_type="knowledge")
        assert result.total == 0
        assert result.results == []


# ======================================================================
# Manager tests
# ======================================================================


class TestLongTermMemoryManager:
    @pytest.fixture
    def store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def manager(self, store: FakeMemoryStore) -> LongTermMemoryManager:
        return LongTermMemoryManager(
            store=store,
            importance_scorer=FixedImportanceScorer(75.0),
        )

    @pytest.mark.asyncio
    async def test_create_memory(
        self, manager: LongTermMemoryManager
    ):
        mem = await manager.create_memory(
            content="Test memory content",
            memory_type="knowledge",
            source="test",
            tags=["test"],
        )
        assert mem.id
        assert mem.content == "Test memory content"
        assert mem.memory_type == "knowledge"
        assert mem.importance_score == 75.0

    @pytest.mark.asyncio
    async def test_get_memory(
        self, manager: LongTermMemoryManager
    ):
        created = await manager.create_memory(
            content="Get me", memory_type="user", source="test"
        )
        fetched = await manager.get_memory(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.access_count >= 1

    @pytest.mark.asyncio
    async def test_get_memory_not_found(
        self, manager: LongTermMemoryManager
    ):
        result = await manager.get_memory("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_memory(
        self, manager: LongTermMemoryManager
    ):
        created = await manager.create_memory(
            content="Original", memory_type="knowledge", source="test"
        )
        created.content = "Updated"
        updated = await manager.update_memory(created)
        assert updated is not None
        assert updated.content == "Updated"

    @pytest.mark.asyncio
    async def test_delete_memory_soft(
        self, manager: LongTermMemoryManager
    ):
        created = await manager.create_memory(
            content="To delete", memory_type="user", source="test"
        )
        deleted = await manager.delete_memory(created.id)
        assert deleted is True
        fetched = await manager.get_memory(created.id)
        assert fetched is not None
        assert fetched.status == MemoryStatus.DELETED.value

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(
        self, manager: LongTermMemoryManager
    ):
        result = await manager.delete_memory("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_permanent_delete(
        self, manager: LongTermMemoryManager
    ):
        created = await manager.create_memory(
            content="Remove", memory_type="system", source="test"
        )
        result = await manager.permanent_delete(created.id)
        assert result is True
        fetched = await manager.get_memory(created.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_search(
        self, manager: LongTermMemoryManager, store: FakeMemoryStore
    ):
        await manager.create_memory(
            content="Alice loves functional programming",
            memory_type="user",
            source="conversation",
            user_id="u1",
            tags=["functional", "programming"],
        )
        result = await manager.search("functional programming", user_id="u1")
        assert result.total >= 1
        assert "functional" in result.results[0].content

    @pytest.mark.asyncio
    async def test_get_by_tags(
        self, manager: LongTermMemoryManager, store: FakeMemoryStore
    ):
        await manager.create_memory(
            content="Tagged memory", memory_type="knowledge",
            source="test", tags=["important", "critical"],
        )
        results = await manager.get_by_tags(["important"])
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_get_by_entity(
        self, manager: LongTermMemoryManager, store: FakeMemoryStore
    ):
        await manager.create_memory(
            content="Entity memory", memory_type="knowledge",
            source="test", entities=["person:alice"],
        )
        results = await manager.get_by_entity("person:alice")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_get_by_user(
        self, manager: LongTermMemoryManager
    ):
        await manager.create_memory(
            content="User-specific", memory_type="user",
            source="profile", user_id="specific-user",
        )
        results = await manager.get_by_user("specific-user")
        assert len(results) >= 1
        assert results[0].user_id == "specific-user"

    @pytest.mark.asyncio
    async def test_get_related(
        self, manager: LongTermMemoryManager, store: FakeMemoryStore
    ):
        m1 = await manager.create_memory(
            content="First", memory_type="knowledge", source="test"
        )
        m2 = await manager.create_memory(
            content="Second", memory_type="knowledge", source="test"
        )
        m1.linked_memory_ids = [m2.id]
        await manager.update_memory(m1)
        related = await manager.get_related(m1.id)
        assert len(related) >= 1
        assert related[0].id == m2.id

    @pytest.mark.asyncio
    async def test_consolidate(
        self, manager: LongTermMemoryManager
    ):
        source = ConsolidationSource(
            conversations=[
                {"role": "user", "content": "I enjoy hiking in the mountains"},
            ],
            user_id="u1",
        )
        result = await manager.consolidate(source)
        assert len(result.created) >= 1
        # Verify the memory was stored
        mem_id = result.created[0]
        stored = await manager.get_memory(mem_id)
        assert stored is not None
        assert stored.source == "conversation"

    @pytest.mark.asyncio
    async def test_run_lifecycle(
        self, manager: LongTermMemoryManager, store: FakeMemoryStore
    ):
        await manager.create_memory(
            content="Expiring memory", memory_type="user",
            source="test", importance_score=5.0,
        )
        result = await manager.run_lifecycle()
        assert result.archived >= 1

    @pytest.mark.asyncio
    async def test_get_summary(
        self, manager: LongTermMemoryManager
    ):
        created = await manager.create_memory(
            content="This is a test memory that should get summarized properly",
            memory_type="knowledge", source="test",
        )
        summary = await manager.get_summary(created.id)
        assert summary is not None
        assert len(summary) > 0

    @pytest.mark.asyncio
    async def test_get_summary_not_found(
        self, manager: LongTermMemoryManager
    ):
        result = await manager.get_summary("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_count_by_status(
        self, manager: LongTermMemoryManager
    ):
        await manager.create_memory(content="A", memory_type="user", source="test")
        await manager.create_memory(content="B", memory_type="user", source="test")
        counts = await manager.count_by_status()
        assert counts.get("active", 0) >= 2

    @pytest.mark.asyncio
    async def test_store_property(
        self, manager: LongTermMemoryManager, store: FakeMemoryStore
    ):
        assert manager.store is store

    @pytest.mark.asyncio
    async def test_retriever_property(
        self, manager: LongTermMemoryManager
    ):
        assert manager.retriever is not None

    @pytest.mark.asyncio
    async def test_consolidator_property(
        self, manager: LongTermMemoryManager
    ):
        assert manager.consolidator is not None

    @pytest.mark.asyncio
    async def test_lifecycle_property(
        self, manager: LongTermMemoryManager
    ):
        assert manager.lifecycle is not None


# ======================================================================
# Schema tests
# ======================================================================


class TestSchemas:
    def test_memory_create(self):
        data = MemoryCreate(
            content="Test memory",
            memory_type="user",
            tags=["tag1"],
        )
        assert data.content == "Test memory"
        assert data.memory_type == "user"
        assert data.tags == ["tag1"]

    def test_memory_update(self):
        data = MemoryUpdate(
            content="Updated",
            importance_score=80.0,
        )
        assert data.content == "Updated"
        assert data.importance_score == 80.0

    def test_memory_response(self):
        data = MemoryResponse(
            id="m1",
            memory_type="user",
            content="test",
            summary=None,
            tags=[],
            categories=[],
            entities=[],
            importance_score=50.0,
            status="active",
            linked_memory_ids=[],
            source="test",
            source_id=None,
            user_id=None,
            project_id=None,
            agent_id=None,
            access_count=0,
            metadata={},
            created_at="now",
            accessed_at="now",
            updated_at="now",
            archived_at=None,
        )
        assert data.id == "m1"

    def test_search_result(self):
        result = MemorySearchResult(results=[], total=0, query="test")
        assert result.query == "test"

    def test_consolidate_request(self):
        req = ConsolidateRequest(user_id="u1")
        assert req.user_id == "u1"

    def test_consolidate_response(self):
        resp = ConsolidateResponse(created=["m1"], duplicates_skipped=0, links_created=1)
        assert resp.created == ["m1"]

    def test_lifecycle_response(self):
        resp = LifecycleResponse(aged=5, archived=2, purged=1)
        assert resp.aged == 5

    def test_stats_response(self):
        resp = StatsResponse(counts_by_status={"active": 10})
        assert resp.counts_by_status["active"] == 10


# ======================================================================
# Edge case tests
# ======================================================================


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_create_memory_empty_content(self):
        store = FakeMemoryStore()
        manager = LongTermMemoryManager(store=store)
        mem = await manager.create_memory(
            content="", memory_type="knowledge", source="test"
        )
        assert mem.content == ""
        assert mem.summary == ""

    @pytest.mark.asyncio
    async def test_create_memory_very_long_content(self):
        store = FakeMemoryStore()
        manager = LongTermMemoryManager(store=store)
        long_content = "A" * 10000
        mem = await manager.create_memory(
            content=long_content, memory_type="knowledge", source="test"
        )
        assert len(mem.content) == 10000

    @pytest.mark.asyncio
    async def test_concurrent_memories(self):
        store = FakeMemoryStore()
        manager = LongTermMemoryManager(store=store)
        m1 = await manager.create_memory(content="First", memory_type="user", source="test")
        m2 = await manager.create_memory(content="Second", memory_type="user", source="test")
        assert m1.id != m2.id
        assert await manager.get_memory(m1.id) is not None
        assert await manager.get_memory(m2.id) is not None

    @pytest.mark.asyncio
    async def test_link_memories_manually(self):
        store = FakeMemoryStore()
        manager = LongTermMemoryManager(store=store)
        m1 = await manager.create_memory(content="A", memory_type="knowledge", source="test")
        m2 = await manager.create_memory(content="B", memory_type="knowledge", source="test")
        m1.linked_memory_ids = [m2.id]
        await manager.update_memory(m1)
        related = await manager.get_related(m1.id)
        assert len(related) == 1
        assert related[0].id == m2.id


# ======================================================================
# Integration: Cognitive Engine + LTM
# ======================================================================


class TestCognitiveIntegration:
    @pytest.mark.asyncio
    async def test_engine_accepts_ltm_optional(self):
        from app.cognitive.engine import CognitiveEngine

        engine = CognitiveEngine(
            goal_manager=MagicMock(),
            task_manager=MagicMock(),
            agent_manager=MagicMock(),
            profile_memory=MagicMock(),
            conversation_memory=MagicMock(),
        )
        assert engine._long_term_memory is None

    @pytest.mark.asyncio
    async def test_engine_process_with_ltm(self):
        from app.cognitive.engine import CognitiveEngine

        store = FakeMemoryStore()
        ltm = LongTermMemoryManager(store=store)
        agent_manager = MagicMock()
        agent_manager.list_runtime_agents.return_value = []

        engine = CognitiveEngine(
            goal_manager=MagicMock(),
            task_manager=MagicMock(),
            agent_manager=agent_manager,
            profile_memory=MagicMock(),
            conversation_memory=MagicMock(),
            long_term_memory=ltm,
        )

        # No memories yet — key should not be in extra
        state = await engine.process(raw_input="hello", user_id=str(uuid4()))
        assert state.context is not None
        assert "long_term_memories" not in state.context.extra

        # Add a memory and search for it
        await ltm.create_memory(
            content="User likes Python programming",
            memory_type="user",
            source="conversation",
            user_id=state.context.user_id,
            tags=["python", "programming"],
        )
        state2 = await engine.process(raw_input="python", user_id=state.context.user_id)
        assert "long_term_memories" in state2.context.extra
        assert len(state2.context.extra["long_term_memories"]) >= 1
