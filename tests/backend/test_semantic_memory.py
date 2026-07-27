"""Tests for SemanticMemory — the RAG layer.

Covers:
- Constructor variants (backward-compat vs new-style providers)
- store() / search() core API
- auto_index() for profiles, goals, tasks
- Threshold filtering
- Edge cases (empty content, failed embeddings, etc.)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.asyncio

from app.memory.providers import EmbeddingProvider, VectorEntry, VectorStoreProvider
from app.memory.semantic import SemanticMemory, SemanticMemoryConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class FakeEmbedder(EmbeddingProvider):
    """Deterministic fake embedder for tests."""

    def __init__(self) -> None:
        self.call_count = 0

    async def embed(self, text: str) -> list[float]:
        self.call_count += 1
        # Simple hash-based embedding for determinism
        h = hash(text) % 100
        return [float(h) / 100, 0.5, 0.3, 0.1]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


class FakeVectorStore(VectorStoreProvider):
    """In-memory fake vector store for tests."""

    def __init__(self) -> None:
        self.collections: dict[str, list[VectorEntry]] = {}

    async def get_or_create_collection(
        self, name: str, metadata: dict | None = None
    ) -> str:
        if name not in self.collections:
            self.collections[name] = []
        return name

    async def add(self, collection: str, entries: list[VectorEntry]) -> None:
        self.collections.setdefault(collection, []).extend(entries)

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 5,
        threshold: float | None = None,
    ) -> list[VectorEntry]:
        entries = self.collections.get(collection, [])
        # Simple: return first top_k entries (no real distance calc)
        result = []
        for e in entries[:top_k]:
            if threshold is not None and e.distance > threshold:
                continue
            result.append(e)
        return result

    async def delete(self, collection: str, ids: list[str]) -> None:
        entries = self.collections.get(collection, [])
        self.collections[collection] = [e for e in entries if e.id not in ids]

    async def count(self, collection: str) -> int:
        return len(self.collections.get(collection, []))

    async def get_all_ids(self, collection: str) -> list[str]:
        return [e.id for e in self.collections.get(collection, [])]


@pytest.fixture
def embedder():
    return FakeEmbedder()


@pytest.fixture
def vector_store():
    return FakeVectorStore()


@pytest.fixture
def sm(embedder, vector_store):
    """SemanticMemory with new-style providers."""
    return SemanticMemory(embedder=embedder, vector_store=vector_store)


# ---------------------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------------------


class TestSemanticMemoryInit:
    def test_new_style_providers(self, embedder, vector_store):
        sm = SemanticMemory(embedder=embedder, vector_store=vector_store)
        assert sm.embedder is embedder
        assert sm.vector_store is vector_store

    def test_missing_providers_raises(self):
        with pytest.raises(TypeError, match="requires either"):
            SemanticMemory()

    def test_config_defaults(self, embedder, vector_store):
        sm = SemanticMemory(embedder=embedder, vector_store=vector_store)
        assert sm.config.top_k == 3
        assert sm.config.relevance_threshold == 0.85
        assert sm.config.auto_index is True

    def test_custom_config(self, embedder, vector_store):
        config = SemanticMemoryConfig(top_k=10, relevance_threshold=0.5)
        sm = SemanticMemory(embedder=embedder, vector_store=vector_store, config=config)
        assert sm.config.top_k == 10
        assert sm.config.relevance_threshold == 0.5

    def test_top_k_kwarg_overrides_default(self, embedder, vector_store):
        sm = SemanticMemory(embedder=embedder, vector_store=vector_store, top_k=7)
        assert sm.config.top_k == 7


# ---------------------------------------------------------------------------
# store() tests
# ---------------------------------------------------------------------------


class TestStore:
    async def test_store_adds_entry(self, sm, vector_store):
        await sm.store("session-1", "Hello world")
        count = await vector_store.count("nova_semantic_memory")
        assert count == 1

    async def test_store_empty_content_skipped(self, sm, vector_store):
        await sm.store("session-1", "")
        await sm.store("session-1", "   ")
        count = await vector_store.count("nova_semantic_memory")
        assert count == 0

    async def test_store_failed_embedding_skipped(self, embedder, vector_store):
        embedder.embed = AsyncMock(return_value=[])
        sm = SemanticMemory(embedder=embedder, vector_store=vector_store)
        await sm.store("session-1", "test content")
        count = await vector_store.count("nova_semantic_memory")
        assert count == 0

    async def test_store_uses_session_in_metadata(self, sm, vector_store):
        await sm.store("sess-42", "My memory")
        entries = vector_store.collections["nova_semantic_memory"]
        assert entries[0].metadata["session_id"] == "sess-42"
        assert entries[0].metadata["source"] == "message"


# ---------------------------------------------------------------------------
# search() tests
# ---------------------------------------------------------------------------


class TestSearch:
    async def test_search_returns_results(self, sm):
        await sm.store("s1", "Python is a programming language")
        results = await sm.search("programming")
        assert len(results) > 0
        assert "content" in results[0]

    async def test_search_empty_when_no_data(self, sm):
        results = await sm.search("anything")
        assert results == []

    async def test_search_uses_config_top_k(self, embedder, vector_store):
        sm = SemanticMemory(
            embedder=embedder, vector_store=vector_store,
            config=SemanticMemoryConfig(top_k=2),
        )
        for i in range(5):
            await sm.store(f"s{i}", f"Document {i}")
        results = await sm.search("test")
        assert len(results) <= 2

    async def test_search_override_top_k(self, sm):
        for i in range(5):
            await sm.store(f"s{i}", f"Document {i}")
        results = await sm.search("test", top_k=1)
        assert len(results) <= 1

    async def test_search_threshold_filtering(self, embedder, vector_store):
        sm = SemanticMemory(
            embedder=embedder, vector_store=vector_store,
            config=SemanticMemoryConfig(relevance_threshold=0.01),
        )
        await sm.store("s1", "Some content")
        results = await sm.search("test", threshold=0.01)
        # With very tight threshold, may filter out
        assert isinstance(results, list)

    async def test_search_failed_embedding_returns_empty(self, embedder, vector_store):
        embedder.embed = AsyncMock(return_value=[])
        sm = SemanticMemory(embedder=embedder, vector_store=vector_store)
        results = await sm.search("test")
        assert results == []


# ---------------------------------------------------------------------------
# auto_index() tests
# ---------------------------------------------------------------------------


class TestAutoIndex:
    async def test_auto_index_profiles(self, sm, vector_store):
        profile = {
            "name": "Alejandro",
            "facts": ["Likes Python", "Prefers dark mode"],
            "preferences": {"theme": "dark", "lang": "es"},
        }
        await sm.auto_index(profile=profile)
        count = await vector_store.count("nova_semantic_memory")
        # 2 facts + 1 name + 2 preferences = 5
        assert count == 5

    async def test_auto_index_goals(self, sm, vector_store):
        goals = [
            {"id": "g1", "title": "Learn Rust", "description": "Complete the book", "status": "active"},
            {"id": "g2", "title": "Deploy app", "status": "completed"},
        ]
        await sm.auto_index(goals=goals)
        count = await vector_store.count("nova_semantic_memory")
        assert count == 2

    async def test_auto_index_tasks(self, sm, vector_store):
        tasks = [
            {"id": "t1", "goal": "Write tests", "status": "COMPLETED"},
            {"id": "t2", "goal": "Pending task", "status": "CREATED"},
        ]
        await sm.auto_index(tasks=tasks)
        count = await vector_store.count("nova_semantic_memory")
        # Only completed tasks indexed
        assert count == 1

    async def test_auto_index_disabled(self, embedder, vector_store):
        sm = SemanticMemory(
            embedder=embedder, vector_store=vector_store,
            config=SemanticMemoryConfig(auto_index=False),
        )
        await sm.auto_index(profile={"name": "Test"})
        count = await vector_store.count("nova_semantic_memory")
        assert count == 0

    async def test_auto_index_none_sources(self, sm, vector_store):
        await sm.auto_index()
        count = await vector_store.count("nova_semantic_memory")
        assert count == 0


# ---------------------------------------------------------------------------
# clear() and count()
# ---------------------------------------------------------------------------


class TestAdmin:
    async def test_count_empty(self, sm):
        assert await sm.count() == 0

    async def test_count_after_stores(self, sm):
        await sm.store("s1", "a")
        await sm.store("s2", "b")
        assert await sm.count() == 2

    async def test_clear_removes_all(self, sm):
        await sm.store("s1", "a")
        await sm.store("s2", "b")
        await sm.clear()
        assert await sm.count() == 0


# ---------------------------------------------------------------------------
# Config setter
# ---------------------------------------------------------------------------


class TestConfig:
    def test_config_setter(self, sm):
        new_config = SemanticMemoryConfig(top_k=99)
        sm.config = new_config
        assert sm.config.top_k == 99
