"""Comprehensive tests for SemanticMemory v2 — Strategy Pattern, multi-source
indexing, configurable threshold, auto-index, and provider interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.memory.embeddings import OllamaEmbeddingProvider
from app.memory.providers import EmbeddingProvider, VectorEntry, VectorStoreProvider
from app.memory.semantic import SemanticMemory, SemanticMemoryConfig
from app.memory.vector_store import ChromaDBVectorStore


# ---------------------------------------------------------------------------
# Fakes for testing
# ---------------------------------------------------------------------------

class FakeEmbedder(EmbeddingProvider):
    """Deterministic embedder for unit tests."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return [float(ord(c)) for c in text[:4]] + [0.0] * 4

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


@dataclass
class _FakeEntry:
    id: str
    document: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    distance: float = 0.0


class FakeVectorStore(VectorStoreProvider):
    """In-memory vector store for unit tests."""

    def __init__(self) -> None:
        self._collections: dict[str, list[_FakeEntry]] = {}

    async def get_or_create_collection(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> str:
        if name not in self._collections:
            self._collections[name] = []
        return name

    async def add(self, collection: str, entries: list[VectorEntry]) -> None:
        for e in entries:
            self._collections[collection].append(
                _FakeEntry(
                    id=e.id,
                    document=e.document,
                    metadata=e.metadata,
                    embedding=e.embedding,
                )
            )

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 5,
        threshold: float | None = None,
    ) -> list[VectorEntry]:
        entries = self._collections.get(collection, [])
        # In a real vector store this would be a real similarity search.
        # For tests we just return the first top_k entries.
        results: list[VectorEntry] = []
        for i, e in enumerate(entries[:top_k]):
            dist = 0.25 * (i + 1)
            if threshold is not None and dist > threshold:
                continue
            results.append(
                VectorEntry(
                    id=e.id,
                    document=e.document,
                    metadata=dict(e.metadata),
                    distance=dist,
                )
            )
        return results

    async def delete(self, collection: str, ids: list[str]) -> None:
        self._collections[collection] = [
            e for e in self._collections.get(collection, []) if e.id not in ids
        ]

    async def count(self, collection: str) -> int:
        return len(self._collections.get(collection, []))

    async def get_all_ids(self, collection: str) -> list[str]:
        return [e.id for e in self._collections.get(collection, [])]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def fake_vector_store() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture
def sm(
    fake_embedder: FakeEmbedder,
    fake_vector_store: FakeVectorStore,
) -> SemanticMemory:
    return SemanticMemory(
        embedder=fake_embedder,
        vector_store=fake_vector_store,
        config=SemanticMemoryConfig(top_k=5, relevance_threshold=None),
    )


# ---------------------------------------------------------------------------
# Provider interface tests
# ---------------------------------------------------------------------------

class TestEmbeddingProviderInterface:
    """Verify that FakeEmbedder conforms to EmbeddingProvider."""

    @pytest.mark.asyncio
    async def test_embed_returns_vector(self, fake_embedder: FakeEmbedder):
        result = await fake_embedder.embed("hello")
        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    @pytest.mark.asyncio
    async def test_embed_batch(self, fake_embedder: FakeEmbedder):
        results = await fake_embedder.embed_batch(["a", "b", "c"])
        assert len(results) == 3
        assert all(isinstance(v, list) for v in results)


class TestVectorStoreProviderInterface:
    """Verify that FakeVectorStore conforms to VectorStoreProvider."""

    @pytest.mark.asyncio
    async def test_get_or_create_collection(
        self, fake_vector_store: FakeVectorStore
    ):
        col = await fake_vector_store.get_or_create_collection("test")
        assert col == "test"

    @pytest.mark.asyncio
    async def test_add_and_count(self, fake_vector_store: FakeVectorStore):
        col = await fake_vector_store.get_or_create_collection("test")
        await fake_vector_store.add(
            col,
            [VectorEntry(id="1", document="doc1", embedding=[0.1, 0.2])],
        )
        assert await fake_vector_store.count(col) == 1

    @pytest.mark.asyncio
    async def test_search(self, fake_vector_store: FakeVectorStore):
        col = await fake_vector_store.get_or_create_collection("test")
        await fake_vector_store.add(
            col,
            [
                VectorEntry(id="1", document="doc1", embedding=[0.1, 0.2]),
                VectorEntry(id="2", document="doc2", embedding=[0.3, 0.4]),
            ],
        )
        results = await fake_vector_store.search(
            col, query_embedding=[0.1, 0.2], top_k=2
        )
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_with_threshold(
        self, fake_vector_store: FakeVectorStore
    ):
        col = await fake_vector_store.get_or_create_collection("test")
        await fake_vector_store.add(
            col,
            [
                VectorEntry(id="1", document="doc1", embedding=[0.1, 0.2]),
                VectorEntry(id="2", document="doc2", embedding=[0.3, 0.4]),
            ],
        )
        results = await fake_vector_store.search(
            col, query_embedding=[0.1, 0.2], top_k=5, threshold=0.3
        )
        # Only entry with distance <= 0.3
        for r in results:
            assert r.distance <= 0.3

    @pytest.mark.asyncio
    async def test_delete(self, fake_vector_store: FakeVectorStore):
        col = await fake_vector_store.get_or_create_collection("test")
        await fake_vector_store.add(
            col,
            [VectorEntry(id="1", document="doc1", embedding=[0.1, 0.2])],
        )
        assert await fake_vector_store.count(col) == 1
        await fake_vector_store.delete(col, ["1"])
        assert await fake_vector_store.count(col) == 0


# ---------------------------------------------------------------------------
# SemanticMemory v2 — backward-compat API
# ---------------------------------------------------------------------------

class TestSemanticMemoryBackwardCompat:
    """Verify that the v1 (chroma_client, ollama, top_k) constructor still works."""

    @pytest.mark.asyncio
    async def test_legacy_constructor(self):
        sm = SemanticMemory(
            chroma_client="fake", ollama="fake",
            top_k=3,
        )
        # It should fall through to the backward-compat branch
        assert sm._embedder is not None
        assert sm._vector_store is not None

    @pytest.mark.asyncio
    async def test_legacy_constructor_raises_without_args(self):
        with pytest.raises(TypeError, match="requires either"):
            SemanticMemory()  # type: ignore[call-arg]

    @pytest.mark.asyncio
    async def test_store_and_search(self, sm: SemanticMemory, fake_embedder: FakeEmbedder):
        await sm.store("session-1", "I love Python")
        await sm.store("session-1", "TypeScript is great too")

        results = await sm.search("programming languages")
        assert len(results) >= 1
        assert all("content" in r for r in results)
        assert all("distance" in r for r in results)
        assert all("session_id" in r for r in results)
        assert all("source" in r for r in results)

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_no_match(
        self, sm: SemanticMemory, fake_embedder: FakeEmbedder
    ):
        results = await sm.search("nothing")
        assert results == []


# ---------------------------------------------------------------------------
# SemanticMemory v2 — multi-source indexing
# ---------------------------------------------------------------------------

class TestMultiSourceIndexing:
    """Verify auto_index, index_profile_facts, index_goals, index_tasks."""

    @pytest.mark.asyncio
    async def test_index_profile_facts(self, sm: SemanticMemory):
        profile = {
            "name": "Alice",
            "facts": ["Loves hiking", "Works at Acme Corp"],
            "preferences": {"language": "Python", "editor": "VS Code"},
        }
        await sm.index_profile_facts(profile)

        results = await sm.search("Alice")
        # The profile facts should have been embedded and stored
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_index_profile_facts_empty(self, sm: SemanticMemory):
        await sm.index_profile_facts(None)
        assert await sm.count() == 0

        await sm.index_profile_facts({})
        assert await sm.count() == 0

    @pytest.mark.asyncio
    async def test_index_goals(self, sm: SemanticMemory):
        goals = [
            {"id": "g1", "title": "Learn Rust", "description": "Master ownership model", "status": "active"},
            {"id": "g2", "title": "Build a chatbot", "status": "active"},
        ]
        await sm.index_goals(goals)

        results = await sm.search("learn")
        assert len(results) >= 1
        assert results[0]["source"] == "goal"

    @pytest.mark.asyncio
    async def test_index_goals_empty(self, sm: SemanticMemory):
        await sm.index_goals(None)
        assert await sm.count() == 0

        await sm.index_goals([])
        assert await sm.count() == 0

    @pytest.mark.asyncio
    async def test_index_tasks(self, sm: SemanticMemory):
        tasks = [
            {"id": "t1", "goal": "Implement login page", "status": "COMPLETED"},
            {"id": "t2", "goal": "Write unit tests", "status": "PENDING"},
            {"id": "t3", "goal": "Deploy to staging", "status": "DONE"},
        ]
        await sm.index_tasks(tasks)

        results = await sm.search("login")
        assert len(results) >= 1
        assert all(r["source"] == "completed_task" for r in results)

    @pytest.mark.asyncio
    async def test_index_tasks_empty(self, sm: SemanticMemory):
        await sm.index_tasks(None)
        assert await sm.count() == 0

        await sm.index_tasks([])
        assert await sm.count() == 0

    @pytest.mark.asyncio
    async def test_auto_index_respects_flag(self, sm: SemanticMemory):
        sm.config.auto_index = False
        await sm.auto_index(
            profile={"name": "Bob", "facts": ["Test"]},
            goals=[{"id": "g1", "title": "Test goal"}],
            tasks=[{"id": "t1", "goal": "Test task", "status": "COMPLETED"}],
        )
        assert await sm.count() == 0

    @pytest.mark.asyncio
    async def test_auto_index_full(self, sm: SemanticMemory):
        await sm.auto_index(
            profile={"name": "Charlie", "facts": ["Loves testing"]},
            goals=[{"id": "g1", "title": "Ship v2"}],
            tasks=[{"id": "t1", "goal": "Test coverage", "status": "COMPLETED"}],
        )
        count = await sm.count()
        assert count >= 3  # profile facts + goal + completed task


# ---------------------------------------------------------------------------
# SemanticMemory v2 — relevance threshold
# ---------------------------------------------------------------------------

class TestRelevanceThreshold:
    """Verify threshold filtering on search."""

    @pytest.mark.asyncio
    async def test_threshold_filters_results(
        self, fake_embedder: FakeEmbedder, fake_vector_store: FakeVectorStore
    ):
        sm = SemanticMemory(
            embedder=fake_embedder,
            vector_store=fake_vector_store,
            config=SemanticMemoryConfig(top_k=10, relevance_threshold=0.3),
        )
        await sm.store("s1", "Entry A")
        await sm.store("s2", "Entry B")
        await sm.store("s3", "Entry C")

        # With threshold=0.3, only entries with distance <= 0.3 are returned.
        results = await sm.search("test")
        for r in results:
            assert r["distance"] <= 0.3

    @pytest.mark.asyncio
    async def test_search_overrides_config_threshold(
        self, fake_embedder: FakeEmbedder, fake_vector_store: FakeVectorStore
    ):
        sm = SemanticMemory(
            embedder=fake_embedder,
            vector_store=fake_vector_store,
            config=SemanticMemoryConfig(top_k=10, relevance_threshold=0.3),
        )
        await sm.store("s1", "Entry A")
        await sm.store("s2", "Entry B")

        # Override threshold to None (no filtering)
        results = await sm.search("test", threshold=None)
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_threshold_none_returns_all(
        self, fake_embedder: FakeEmbedder, fake_vector_store: FakeVectorStore
    ):
        sm = SemanticMemory(
            embedder=fake_embedder,
            vector_store=fake_vector_store,
            config=SemanticMemoryConfig(top_k=10, relevance_threshold=None),
        )
        await sm.store("s1", "Entry A")
        await sm.store("s2", "Entry B")
        await sm.store("s3", "Entry C")

        results = await sm.search("test")
        assert len(results) == 3


# ---------------------------------------------------------------------------
# SemanticMemory v2 — config
# ---------------------------------------------------------------------------

class TestSemanticMemoryConfig:
    """Verify config get/set."""

    def test_default_config(self):
        cfg = SemanticMemoryConfig()
        assert cfg.top_k == 3
        assert cfg.relevance_threshold == 0.85
        assert cfg.auto_index is True

    def test_custom_config(self):
        cfg = SemanticMemoryConfig(top_k=10, relevance_threshold=0.5, auto_index=False)
        assert cfg.top_k == 10
        assert cfg.relevance_threshold == 0.5
        assert cfg.auto_index is False

    @pytest.mark.asyncio
    async def test_config_setter(self, sm: SemanticMemory):
        sm.config = SemanticMemoryConfig(top_k=1, relevance_threshold=0.9)
        assert sm.config.top_k == 1
        assert sm.config.relevance_threshold == 0.9


# ---------------------------------------------------------------------------
# SemanticMemory v2 — clear / count
# ---------------------------------------------------------------------------

class TestAdminOperations:

    @pytest.mark.asyncio
    async def test_clear(self, sm: SemanticMemory):
        await sm.store("s1", "Hello")
        await sm.store("s2", "World")
        assert await sm.count() == 2
        await sm.clear()
        assert await sm.count() == 0

    @pytest.mark.asyncio
    async def test_count_empty(self, sm: SemanticMemory):
        assert await sm.count() == 0

    @pytest.mark.asyncio
    async def test_count_after_store(self, sm: SemanticMemory):
        await sm.store("s1", "Document")
        assert await sm.count() == 1
        await sm.store("s2", "Another")
        assert await sm.count() == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    @pytest.mark.asyncio
    async def test_empty_query(self, sm: SemanticMemory):
        await sm.store("s1", "Something")
        results = await sm.search("")
        # Empty query should not crash; results depend on embedder behavior
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_store_empty_content(self, sm: SemanticMemory):
        await sm.store("s1", "")
        assert await sm.count() == 0

    @pytest.mark.asyncio
    async def test_special_characters(self, sm: SemanticMemory):
        content = "Hello! @#$% ^&*() 123"
        await sm.store("s1", content)
        results = await sm.search("special")
        assert len(results) >= 1
        assert results[0]["content"] == content

    @pytest.mark.asyncio
    async def test_very_long_content(self, sm: SemanticMemory):
        long_text = "word " * 10_000
        await sm.store("s1", long_text)
        assert await sm.count() == 1

    @pytest.mark.asyncio
    async def test_repeated_stores_same_session(self, sm: SemanticMemory):
        for i in range(5):
            await sm.store("s1", f"Message {i}")
        assert await sm.count() == 5

    @pytest.mark.asyncio
    async def test_index_tasks_skips_non_completed(
        self, sm: SemanticMemory
    ):
        tasks = [
            {"id": "t1", "goal": "Do X", "status": "CREATED"},
            {"id": "t2", "goal": "Do Y", "status": "RUNNING"},
            {"id": "t3", "goal": "Do Z", "status": "COMPLETED"},
        ]
        await sm.index_tasks(tasks)
        results = await sm.search("task")
        assert len(results) == 1
        assert results[0]["source"] == "completed_task"
        assert "Do Z" in results[0]["content"]

    @pytest.mark.asyncio
    async def test_profile_without_facts(self, sm: SemanticMemory):
        await sm.index_profile_facts({"name": "Dave"})
        results = await sm.search("Dave")
        assert len(results) >= 1
