"""Tests for PreferenceManager — CRUD, filters, soft/permanent delete, search, conflict resolution."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.long_term_memory.base import MemoryStore, MemoryRetriever
from app.long_term_memory.manager import LongTermMemoryManager
from app.long_term_memory.models import (
    LongTermMemory,
    MemoryStatus,
    MemoryType,
    RetrievalResult,
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


class FakeMemoryRetriever(MemoryRetriever):
    """In-memory retriever for testing semantic search."""

    def __init__(self, store: FakeMemoryStore) -> None:
        self._store = store

    async def search(
        self,
        query: str,
        memory_type: str | None = None,
        user_id: str | None = None,
        limit: int = 10,
    ) -> RetrievalResult:
        results = list(self._store._memories.values())
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        if user_id:
            results = [m for m in results if m.user_id == user_id]
        # Simple keyword matching for testing
        query_lower = query.lower()
        matched = [m for m in results if query_lower in m.content.lower()]
        return RetrievalResult(
            results=matched[:limit],
            total=len(matched),
            query=query,
        )

    async def search_similar(
        self,
        content: str,
        memory_type: str | None = None,
        limit: int = 10,
        threshold: float = 0.75,
    ) -> RetrievalResult:
        return await self.search(content, memory_type=memory_type, limit=limit)


# ======================================================================
# PreferenceManager Tests
# ======================================================================


class TestCreatePreference:
    """Tests for create_preference method."""

    @pytest.fixture
    def store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def retriever(self, store: FakeMemoryStore) -> FakeMemoryRetriever:
        return FakeMemoryRetriever(store)

    @pytest.fixture
    def manager(
        self, store: FakeMemoryStore, retriever: FakeMemoryRetriever
    ) -> LongTermMemoryManager:
        return LongTermMemoryManager(store=store, retriever=retriever)

    @pytest.mark.asyncio
    async def test_create_preference_basic(self, manager: LongTermMemoryManager):
        """Test creating a basic preference."""
        pref = await manager.create_preference(
            user_id="user1",
            content="response style: concise",
        )
        assert pref.id
        assert pref.memory_type == MemoryType.PREFERENCE.value
        assert pref.user_id == "user1"
        assert pref.content == "response style: concise"
        assert pref.status == MemoryStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_create_preference_with_tags(self, manager: LongTermMemoryManager):
        """Test creating preference with tags."""
        pref = await manager.create_preference(
            user_id="user1",
            content="response style: concise",
            tags=["response_style", "communication"],
        )
        assert "response_style" in pref.tags
        assert "communication" in pref.tags

    @pytest.mark.asyncio
    async def test_create_preference_with_categories(
        self, manager: LongTermMemoryManager
    ):
        """Test creating preference with categories."""
        pref = await manager.create_preference(
            user_id="user1",
            content="verbosity: low",
            categories=["communication"],
        )
        assert "communication" in pref.categories

    @pytest.mark.asyncio
    async def test_create_preference_with_metadata(
        self, manager: LongTermMemoryManager
    ):
        """Test creating preference with metadata."""
        pref = await manager.create_preference(
            user_id="user1",
            content="response style: concise",
            metadata={"domain": "communication", "confidence": 0.9, "source": "observed"},
        )
        assert pref.metadata["domain"] == "communication"
        assert pref.metadata["confidence"] == 0.9
        assert pref.metadata["source"] == "observed"

    @pytest.mark.asyncio
    async def test_create_preference_sets_timestamps(
        self, manager: LongTermMemoryManager
    ):
        """Test that created_at and updated_at are set."""
        pref = await manager.create_preference(
            user_id="user1",
            content="test preference",
        )
        assert pref.created_at
        assert pref.updated_at
        assert pref.created_at == pref.updated_at


class TestGetPreferencesByUser:
    """Tests for get_preferences_by_user method."""

    @pytest.fixture
    def store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def retriever(self, store: FakeMemoryStore) -> FakeMemoryRetriever:
        return FakeMemoryRetriever(store)

    @pytest.fixture
    def manager(
        self, store: FakeMemoryStore, retriever: FakeMemoryRetriever
    ) -> LongTermMemoryManager:
        return LongTermMemoryManager(store=store, retriever=retriever)

    @pytest.mark.asyncio
    async def test_get_all_preferences_for_user(self, manager: LongTermMemoryManager):
        """Test retrieving all preferences for a user."""
        await manager.create_preference(
            user_id="user1",
            content="preference 1",
            tags=["tag1"],
        )
        await manager.create_preference(
            user_id="user1",
            content="preference 2",
            tags=["tag2"],
        )
        await manager.create_preference(
            user_id="user2",
            content="other user preference",
            tags=["tag1"],
        )
        prefs = await manager.get_preferences_by_user("user1")
        assert len(prefs) == 2
        assert all(p.user_id == "user1" for p in prefs)

    @pytest.mark.asyncio
    async def test_get_preferences_by_tag(self, manager: LongTermMemoryManager):
        """Test filtering preferences by tag."""
        await manager.create_preference(
            user_id="user1",
            content="response style",
            tags=["response_style"],
        )
        await manager.create_preference(
            user_id="user1",
            content="verbosity",
            tags=["verbosity"],
        )
        prefs = await manager.get_preferences_by_user("user1", tag="response_style")
        assert len(prefs) == 1
        assert "response_style" in prefs[0].tags

    @pytest.mark.asyncio
    async def test_get_preferences_by_category(self, manager: LongTermMemoryManager):
        """Test filtering preferences by category."""
        await manager.create_preference(
            user_id="user1",
            content="response style",
            categories=["communication"],
        )
        await manager.create_preference(
            user_id="user1",
            content="code style",
            categories=["coding"],
        )
        prefs = await manager.get_preferences_by_user(
            "user1", category="communication"
        )
        assert len(prefs) == 1
        assert "communication" in prefs[0].categories

    @pytest.mark.asyncio
    async def test_get_preferences_excludes_deleted(self, manager: LongTermMemoryManager):
        """Test that deleted preferences are not returned."""
        pref = await manager.create_preference(
            user_id="user1",
            content="to be deleted",
        )
        await manager.delete_preference(pref.id)
        prefs = await manager.get_preferences_by_user("user1")
        assert len(prefs) == 0

    @pytest.mark.asyncio
    async def test_get_preferences_empty_user(self, manager: LongTermMemoryManager):
        """Test retrieving preferences for user with none."""
        prefs = await manager.get_preferences_by_user("nonexistent")
        assert len(prefs) == 0


class TestUpdatePreference:
    """Tests for update_preference and update_preference_metadata methods."""

    @pytest.fixture
    def store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def retriever(self, store: FakeMemoryStore) -> FakeMemoryRetriever:
        return FakeMemoryRetriever(store)

    @pytest.fixture
    def manager(
        self, store: FakeMemoryStore, retriever: FakeMemoryRetriever
    ) -> LongTermMemoryManager:
        return LongTermMemoryManager(store=store, retriever=retriever)

    @pytest.mark.asyncio
    async def test_update_preference_content(self, manager: LongTermMemoryManager):
        """Test updating preference content."""
        pref = await manager.create_preference(
            user_id="user1",
            content="old content",
        )
        updated = await manager.update_preference(pref.id, "new content")
        assert updated is not None
        assert updated.content == "new content"
        assert updated.updated_at != pref.created_at

    @pytest.mark.asyncio
    async def test_update_preference_not_found(self, manager: LongTermMemoryManager):
        """Test updating non-existent preference returns None."""
        result = await manager.update_preference("nonexistent", "content")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_preference_metadata(self, manager: LongTermMemoryManager):
        """Test updating preference metadata merges with existing."""
        pref = await manager.create_preference(
            user_id="user1",
            content="test",
            metadata={"domain": "communication"},
        )
        updated = await manager.update_preference_metadata(
            pref.id, {"confidence": 0.8}
        )
        assert updated is not None
        assert updated.metadata["domain"] == "communication"
        assert updated.metadata["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_update_preference_metadata_overwrites(
        self, manager: LongTermMemoryManager
    ):
        """Test that metadata update overwrites existing keys."""
        pref = await manager.create_preference(
            user_id="user1",
            content="test",
            metadata={"domain": "old"},
        )
        updated = await manager.update_preference_metadata(
            pref.id, {"domain": "new"}
        )
        assert updated is not None
        assert updated.metadata["domain"] == "new"


class TestDeletePreference:
    """Tests for delete_preference (soft) and permanent_delete_preference."""

    @pytest.fixture
    def store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def retriever(self, store: FakeMemoryStore) -> FakeMemoryRetriever:
        return FakeMemoryRetriever(store)

    @pytest.fixture
    def manager(
        self, store: FakeMemoryStore, retriever: FakeMemoryRetriever
    ) -> LongTermMemoryManager:
        return LongTermMemoryManager(store=store, retriever=retriever)

    @pytest.mark.asyncio
    async def test_soft_delete_preference(self, manager: LongTermMemoryManager, store: FakeMemoryStore):
        """Test soft delete sets status to DELETED."""
        pref = await manager.create_preference(
            user_id="user1",
            content="to delete",
        )
        result = await manager.delete_preference(pref.id)
        assert result is True
        # Verify it's still in store but marked deleted
        fetched = await store.get(pref.id)
        assert fetched is not None
        assert fetched.status == MemoryStatus.DELETED.value

    @pytest.mark.asyncio
    async def test_soft_delete_not_found(self, manager: LongTermMemoryManager):
        """Test soft delete on non-existent preference returns False."""
        result = await manager.delete_preference("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_permanent_delete_preference(self, manager: LongTermMemoryManager, store: FakeMemoryStore):
        """Test permanent delete removes from store."""
        pref = await manager.create_preference(
            user_id="user1",
            content="to permanently delete",
        )
        result = await manager.permanent_delete_preference(pref.id)
        assert result is True
        # Verify it's gone from store
        fetched = await store.get(pref.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_permanent_delete_not_found(self, manager: LongTermMemoryManager):
        """Test permanent delete on non-existent preference returns False."""
        result = await manager.permanent_delete_preference("nonexistent")
        assert result is False


class TestSearchPreferences:
    """Tests for search_preferences method."""

    @pytest.fixture
    def store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def retriever(self, store: FakeMemoryStore) -> FakeMemoryRetriever:
        return FakeMemoryRetriever(store)

    @pytest.fixture
    def manager(
        self, store: FakeMemoryStore, retriever: FakeMemoryRetriever
    ) -> LongTermMemoryManager:
        return LongTermMemoryManager(store=store, retriever=retriever)

    @pytest.mark.asyncio
    async def test_search_preferences_by_query(self, manager: LongTermMemoryManager):
        """Test searching preferences by query."""
        await manager.create_preference(
            user_id="user1",
            content="response style: concise",
            tags=["response_style"],
        )
        await manager.create_preference(
            user_id="user1",
            content="verbosity: low",
            tags=["verbosity"],
        )
        results = await manager.search_preferences("user1", "response")
        assert len(results) == 1
        assert "response" in results[0].content.lower()

    @pytest.mark.asyncio
    async def test_search_preferences_with_limit(self, manager: LongTermMemoryManager):
        """Test searching preferences with limit."""
        for i in range(10):
            await manager.create_preference(
                user_id="user1",
                content=f"preference {i}",
            )
        results = await manager.search_preferences("user1", "preference", limit=5)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_preferences_no_results(self, manager: LongTermMemoryManager):
        """Test search with no matches returns empty list."""
        await manager.create_preference(
            user_id="user1",
            content="something unrelated",
        )
        results = await manager.search_preferences("user1", "nonexistent")
        assert len(results) == 0


class TestResolvePreferenceConflict:
    """Tests for resolve_preference_conflict method."""

    @pytest.fixture
    def store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def retriever(self, store: FakeMemoryStore) -> FakeMemoryRetriever:
        return FakeMemoryRetriever(store)

    @pytest.fixture
    def manager(
        self, store: FakeMemoryStore, retriever: FakeMemoryRetriever
    ) -> LongTermMemoryManager:
        return LongTermMemoryManager(store=store, retriever=retriever)

    @pytest.mark.asyncio
    async def test_resolve_conflict_supersede(self, manager: LongTermMemoryManager, store: FakeMemoryStore):
        """Test resolving conflict by superseding existing preference."""
        old_pref = await manager.create_preference(
            user_id="user1",
            content="response style: verbose",
        )
        new_pref = await manager.create_preference(
            user_id="user1",
            content="response style: concise",
        )
        result = await manager.resolve_preference_conflict(
            old_pref.id, new_pref.id, resolution="supersede"
        )
        assert result is True
        # Old should be CONSOLIDATED
        old_fetched = await store.get(old_pref.id)
        assert old_fetched.status == MemoryStatus.CONSOLIDATED.value
        # New should remain ACTIVE
        new_fetched = await store.get(new_pref.id)
        assert new_fetched.status == MemoryStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_resolve_conflict_not_found(self, manager: LongTermMemoryManager):
        """Test resolving conflict with non-existent preference."""
        result = await manager.resolve_preference_conflict(
            "nonexistent", "also_nonexistent", resolution="supersede"
        )
        assert result is False
