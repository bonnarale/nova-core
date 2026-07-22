"""Tests for the Vector Memory module — Chapter 18."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.vector_memory.base import (
    ConsolidationReport,
    ConsolidationStrategy,
    EmbeddingProvider,
    SimilarityEngine,
    VectorMemoryProvider,
    VectorRepository,
)
from app.vector_memory.consolidation import DefaultConsolidationStrategy
from app.vector_memory.embeddings import (
    GoogleEmbeddingProvider,
    InMemoryEmbeddingProvider,
    LocalEmbeddingProvider,
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from app.vector_memory.engine import VectorMemoryEngine
from app.vector_memory.factory import VectorMemoryFactory
from app.vector_memory.index import VectorIndex
from app.vector_memory.lifecycle import VectorMemoryLifecycle, VectorMemoryState
from app.vector_memory.metrics import VectorMetrics, get_vector_metrics
from app.vector_memory.repository import InMemoryVectorRepository
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
from app.vector_memory.similarity import (
    CosineSimilarity,
    DotProductSimilarity,
    EuclideanSimilarity,
)
from app.vector_memory.storage import ChromaVectorStorage, InMemoryVectorStorage
from app.vector_memory.tracing import VectorSpan, VectorTrace, VectorTracer


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def embedder() -> InMemoryEmbeddingProvider:
    return InMemoryEmbeddingProvider(dimension=384)


@pytest.fixture
def repository() -> InMemoryVectorRepository:
    return InMemoryVectorRepository()


@pytest.fixture
def engine(embedder: InMemoryEmbeddingProvider, repository: InMemoryVectorRepository) -> VectorMemoryEngine:
    eng = VectorMemoryEngine(embedder=embedder, repository=repository)
    return eng


@pytest.fixture
def sample_record() -> VectorRecord:
    return VectorRecord(
        vector_id="",
        source_id="test_source",
        document_id="test_doc",
        memory_type=MemoryCategory.KNOWLEDGE,
        content="Test vector content for unit testing",
        user_id="user-1",
        session_id="session-1",
        tags=["test", "knowledge"],
        confidence=0.9,
        importance=0.8,
        embedding=[],
    )


# =========================================================================
# Vector Memory Lifecycle Tests
# =========================================================================


class TestVectorMemoryLifecycle:
    def test_initial_state(self) -> None:
        lc = VectorMemoryLifecycle()
        assert lc.state == VectorMemoryState.REGISTERED
        assert lc.is_registered
        assert not lc.is_ready

    def test_transitions(self) -> None:
        lc = VectorMemoryLifecycle()
        lc.initialized()
        assert lc.state == VectorMemoryState.INITIALIZED
        assert lc.is_initialized
        lc.ready()
        assert lc.state == VectorMemoryState.READY
        assert lc.is_ready
        lc.indexing()
        assert lc.state == VectorMemoryState.INDEXING
        lc.searching()
        assert lc.state == VectorMemoryState.SEARCHING
        lc.consolidating()
        assert lc.state == VectorMemoryState.CONSOLIDATING

    def test_failed_recover(self) -> None:
        lc = VectorMemoryLifecycle()
        lc.ready()
        lc.failed("test error")
        assert lc.is_failed
        lc.recover()
        assert lc.state == VectorMemoryState.REGISTERED

    def test_shutdown(self) -> None:
        lc = VectorMemoryLifecycle()
        lc.ready()
        lc.shutdown()
        assert lc.is_shutdown


# =========================================================================
# Vector Store Tests
# =========================================================================


class TestInMemoryVectorStorage:
    @pytest.fixture
    def storage(self) -> InMemoryVectorStorage:
        return InMemoryVectorStorage()

    @pytest.fixture
    def records(self) -> list[VectorRecord]:
        from datetime import timezone
        return [
            VectorRecord(
                vector_id="v1", content="First vector",
                user_id="u1", session_id="s1",
                memory_type=MemoryCategory.KNOWLEDGE,
                tags=["a"], embedding=[0.1, 0.2],
            ),
            VectorRecord(
                vector_id="v2", content="Second vector",
                user_id="u1", session_id="s1",
                memory_type=MemoryCategory.CONVERSATION,
                tags=["b"], embedding=[0.3, 0.4],
            ),
            VectorRecord(
                vector_id="v3", content="Third vector",
                user_id="u2", session_id="s2",
                memory_type=MemoryCategory.USER_PROFILE,
                tags=["a", "c"], embedding=[0.5, 0.6],
            ),
        ]

    @pytest.mark.asyncio
    async def test_add_and_list_all(self, storage: InMemoryVectorStorage, records: list[VectorRecord]) -> None:
        count = await storage.add(records)
        assert count == 3
        all_records = await storage.list_all(limit=10)
        assert len(all_records) == 3

    @pytest.mark.asyncio
    async def test_get(self, storage: InMemoryVectorStorage, records: list[VectorRecord]) -> None:
        await storage.add(records)
        rec = await storage.get("v1")
        assert rec is not None
        assert rec.content == "First vector"

    @pytest.mark.asyncio
    async def test_update(self, storage: InMemoryVectorStorage, records: list[VectorRecord]) -> None:
        await storage.add(records)
        records[0].content = "Updated content"
        count = await storage.update([records[0]])
        assert count == 1
        rec = await storage.get("v1")
        assert rec is not None
        assert rec.content == "Updated content"

    @pytest.mark.asyncio
    async def test_delete(self, storage: InMemoryVectorStorage, records: list[VectorRecord]) -> None:
        await storage.add(records)
        count = await storage.delete(["v1"])
        assert count == 1
        assert await storage.get("v1") is None
        assert await storage.count() == 2

    @pytest.mark.asyncio
    async def test_list_by_user(self, storage: InMemoryVectorStorage, records: list[VectorRecord]) -> None:
        await storage.add(records)
        u1_records = await storage.list_by_user("u1")
        assert len(u1_records) == 2
        u2_records = await storage.list_by_user("u2")
        assert len(u2_records) == 1

    @pytest.mark.asyncio
    async def test_list_by_category(self, storage: InMemoryVectorStorage, records: list[VectorRecord]) -> None:
        await storage.add(records)
        knowledge = await storage.list_by_category(MemoryCategory.KNOWLEDGE)
        assert len(knowledge) == 1

    @pytest.mark.asyncio
    async def test_count_by_category(self, storage: InMemoryVectorStorage, records: list[VectorRecord]) -> None:
        await storage.add(records)
        counts = await storage.count_by_category()
        assert counts.get("knowledge") == 1
        assert counts.get("conversation") == 1
        assert counts.get("user_profile") == 1

    @pytest.mark.asyncio
    async def test_search_by_tags(self, storage: InMemoryVectorStorage, records: list[VectorRecord]) -> None:
        await storage.add(records)
        tagged = await storage.search_by_tags(["a"])
        assert len(tagged) == 2

    @pytest.mark.asyncio
    async def test_health(self, storage: InMemoryVectorStorage, records: list[VectorRecord]) -> None:
        await storage.add(records)
        health = await storage.health()
        assert health["status"] == "healthy"
        assert health["total_vectors"] == 3

    @pytest.mark.asyncio
    async def test_search_with_filters(self, storage: InMemoryVectorStorage, records: list[VectorRecord]) -> None:
        await storage.add(records)
        query_emb = [0.15, 0.25]
        results = await storage.search_with_filters(query_emb, top_k=5)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_all(self, storage: InMemoryVectorStorage, records: list[VectorRecord]) -> None:
        await storage.add(records)
        query_emb = [0.15, 0.25]
        results = await storage.search_all(query_emb, top_k=5)
        assert len(results) > 0


# =========================================================================
# Similarity Engine Tests
# =========================================================================


class TestCosineSimilarity:
    def test_identical(self) -> None:
        cs = CosineSimilarity()
        a = [1.0, 0.0, 0.0]
        sim = cs.compute(a, a)
        assert abs(sim - 1.0) < 0.001

    def test_orthogonal(self) -> None:
        cs = CosineSimilarity()
        sim = cs.compute([1.0, 0.0], [0.0, 1.0])
        assert abs(sim - 0.0) < 0.001

    def test_opposite(self) -> None:
        cs = CosineSimilarity()
        sim = cs.compute([1.0, 0.0], [-1.0, 0.0])
        assert abs(sim - (-1.0)) < 0.001

    def test_dimension_mismatch(self) -> None:
        cs = CosineSimilarity()
        with pytest.raises(ValueError):
            cs.compute([1.0, 0.0], [1.0])


class TestDotProductSimilarity:
    def test_basic(self) -> None:
        dp = DotProductSimilarity()
        sim = dp.compute([1.0, 2.0], [3.0, 4.0])
        assert abs(sim - 11.0) < 0.001

    def test_zero(self) -> None:
        dp = DotProductSimilarity()
        sim = dp.compute([0.0, 0.0], [3.0, 4.0])
        assert abs(sim) < 0.001

    def test_batch(self) -> None:
        dp = DotProductSimilarity()
        results = dp.batch_compute([1.0, 0.0], [[2.0, 0.0], [0.0, 1.0]])
        assert len(results) == 2


class TestEuclideanSimilarity:
    def test_identical(self) -> None:
        es = EuclideanSimilarity()
        sim = es.compute([1.0, 0.0], [1.0, 0.0])
        assert abs(sim - 1.0) < 0.001

    def test_distant(self) -> None:
        es = EuclideanSimilarity()
        sim = es.compute([0.0, 0.0], [100.0, 100.0])
        assert sim < 0.5

    def test_batch(self) -> None:
        es = EuclideanSimilarity()
        results = es.batch_compute([1.0, 0.0], [[1.0, 0.0], [-1.0, 0.0]])
        assert len(results) == 2


# =========================================================================
# Embedding Provider Tests
# =========================================================================


class TestInMemoryEmbeddingProvider:
    @pytest.mark.asyncio
    async def test_embed(self) -> None:
        ep = InMemoryEmbeddingProvider(dimension=384)
        emb = await ep.embed("test text")
        assert len(emb) == 384
        assert all(isinstance(v, float) for v in emb)

    @pytest.mark.asyncio
    async def test_embed_batch(self) -> None:
        ep = InMemoryEmbeddingProvider(dimension=384)
        embs = await ep.embed_batch(["text1", "text2"])
        assert len(embs) == 2
        assert len(embs[0]) == 384

    @pytest.mark.asyncio
    async def test_health(self) -> None:
        ep = InMemoryEmbeddingProvider(dimension=384)
        health = await ep.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_deterministic(self) -> None:
        ep = InMemoryEmbeddingProvider(dimension=384)
        emb1 = await ep.embed("same text")
        emb2 = await ep.embed("same text")
        assert emb1 == emb2

    @pytest.mark.asyncio
    async def test_provider_id(self) -> None:
        ep = InMemoryEmbeddingProvider()
        assert ep.provider_id == "in_memory"
        assert ep.embedding_dimension == 384


class TestOllamaEmbeddingProvider:
    @pytest.mark.asyncio
    async def test_health_unhealthy(self) -> None:
        ep = OllamaEmbeddingProvider(base_url="http://localhost:99999")
        health = await ep.health()
        assert health["status"] == "unhealthy"

    def test_provider_id(self) -> None:
        ep = OllamaEmbeddingProvider(base_url="http://localhost:99999")
        assert ep.provider_id == "ollama"

    def test_dimension(self) -> None:
        ep = OllamaEmbeddingProvider()
        assert ep.embedding_dimension == 768


class TestOpenAIEmbeddingProvider:
    def test_provider_id(self) -> None:
        ep = OpenAIEmbeddingProvider()
        assert ep.provider_id == "openai"

    @pytest.mark.asyncio
    async def test_health_unconfigured(self) -> None:
        ep = OpenAIEmbeddingProvider()
        health = await ep.health()
        assert health["status"] == "unconfigured"


class TestGoogleEmbeddingProvider:
    def test_provider_id(self) -> None:
        ep = GoogleEmbeddingProvider()
        assert ep.provider_id == "google"

    @pytest.mark.asyncio
    async def test_health_unconfigured(self) -> None:
        ep = GoogleEmbeddingProvider()
        health = await ep.health()
        assert health["status"] == "unconfigured"


class TestLocalEmbeddingProvider:
    @pytest.mark.asyncio
    async def test_health_no_model(self) -> None:
        ep = LocalEmbeddingProvider()
        health = await ep.health()
        assert health["status"] in ("unhealthy", "healthy")


# =========================================================================
# Consolidation Tests
# =========================================================================


class TestDefaultConsolidationStrategy:
    @pytest.fixture
    def strategy(self) -> DefaultConsolidationStrategy:
        return DefaultConsolidationStrategy(
            duplicate_threshold=0.95,
            stale_days=90,
            importance_threshold=0.1,
        )

    @pytest.mark.asyncio
    async def test_find_duplicates_no_embedding(self, strategy: DefaultConsolidationStrategy) -> None:
        records = [
            VectorRecord(vector_id="a", content="hello", embedding=[0.1, 0.2]),
            VectorRecord(vector_id="b", content="hello", embedding=[0.1, 0.2]),
        ]
        groups = await strategy.find_duplicates(records, threshold=0.95)
        assert len(groups) == 1

    @pytest.mark.asyncio
    async def test_find_duplicates_exact_content(self, strategy: DefaultConsolidationStrategy) -> None:
        records = [
            VectorRecord(vector_id="a", content="exact same content", embedding=[0.1, 0.2]),
            VectorRecord(vector_id="b", content="exact same content", embedding=[0.1, 0.2]),
            VectorRecord(vector_id="c", content="different content", embedding=[0.9, 0.8]),
        ]
        groups = await strategy.find_duplicates(records, threshold=0.95)
        assert len(groups) == 1
        assert len(groups[0]) == 2

    @pytest.mark.asyncio
    async def test_consolidate_duplicates(self, strategy: DefaultConsolidationStrategy) -> None:
        records = [
            VectorRecord(vector_id="a", content="duplicate text", embedding=[0.1, 0.2], confidence=0.9, importance=0.5),
            VectorRecord(vector_id="b", content="duplicate text", embedding=[0.1, 0.2], confidence=0.8, importance=0.4),
        ]
        report = await strategy.consolidate(records)
        assert report.duplicates_removed > 0

    @pytest.mark.asyncio
    async def test_consolidate_no_duplicates(self, strategy: DefaultConsolidationStrategy) -> None:
        records = [
            VectorRecord(vector_id="a", content="first", embedding=[0.1, 0.2]),
            VectorRecord(vector_id="b", content="second", embedding=[0.9, 0.8]),
        ]
        report = await strategy.consolidate(records)
        assert report.duplicates_removed == 0


# =========================================================================
# Search Engine Tests
# =========================================================================


class TestVectorSearchEngine:
    @pytest.fixture
    def storage(self) -> InMemoryVectorStorage:
        return InMemoryVectorStorage()

    @pytest.fixture
    def search_engine(self, storage: InMemoryVectorStorage) -> VectorSearchEngine:
        embedder = InMemoryEmbeddingProvider(dimension=384)
        return VectorSearchEngine(storage=storage, embedder=embedder)

    @pytest.mark.asyncio
    async def test_search_empty(self, search_engine: VectorSearchEngine) -> None:
        query = VectorMemoryQuery(query="test query", top_k=5)
        result = await search_engine.search(query)
        assert result.total == 0
        assert len(result.results) == 0

    @pytest.mark.asyncio
    async def test_similarity_search_empty(self, search_engine: VectorSearchEngine) -> None:
        result = await search_engine.similarity_search(embedding=[0.1, 0.2], top_k=5)
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_hybrid_search_empty(self, search_engine: VectorSearchEngine) -> None:
        result = await search_engine.hybrid_search(
            query_text="test",
            query_embedding=[0.1, 0.2],
            top_k=5,
        )
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_search_with_stored_data(
        self,
        storage: InMemoryVectorStorage,
        search_engine: VectorSearchEngine,
    ) -> None:
        emb = [0.15, 0.25, 0.35]
        await storage.add([
            VectorRecord(vector_id="v1", content="test document", embedding=emb),
        ])
        query = VectorMemoryQuery(query="test", embedding=emb, top_k=5)
        result = await search_engine.search(query)
        assert result.total == 1

    def test_compute_keyword_scores(self, search_engine: VectorSearchEngine) -> None:
        records = [VectorRecord(vector_id="v1", content="test document one")]
        scores = search_engine._compute_keyword_scores("test", records)
        assert "v1" in scores
        assert scores["v1"] > 0


# =========================================================================
# Index Tests
# =========================================================================


class TestVectorIndex:
    @pytest.fixture
    def repository(self) -> InMemoryVectorRepository:
        return InMemoryVectorRepository()

    @pytest.fixture
    def embedder(self) -> InMemoryEmbeddingProvider:
        return InMemoryEmbeddingProvider(dimension=384)

    @pytest.fixture
    def index(self, repository: InMemoryVectorRepository, embedder: InMemoryEmbeddingProvider) -> VectorIndex:
        return VectorIndex(repository=repository, embedder=embedder)

    @pytest.mark.asyncio
    async def test_index_document(self, index: VectorIndex) -> None:
        doc = VectorMemoryDocument(
            source_id="src1",
            document_id="doc1",
            content="Test document for indexing",
            user_id="user-1",
            memory_type=MemoryCategory.KNOWLEDGE,
        )
        record = await index.index_document(doc)
        assert record.vector_id
        assert record.content == "Test document for indexing"
        assert len(record.embedding) == 384

    @pytest.mark.asyncio
    async def test_index_documents(self, index: VectorIndex) -> None:
        docs = [
            VectorMemoryDocument(source_id="src1", content="Doc 1"),
            VectorMemoryDocument(source_id="src2", content="Doc 2"),
        ]
        records = await index.index_documents(docs)
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_index_batch(self, index: VectorIndex) -> None:
        docs = [
            VectorMemoryDocument(source_id="src1", content="Batch 1"),
            VectorMemoryDocument(source_id="src2", content="Batch 2"),
            VectorMemoryDocument(source_id="src3", content="Batch 3"),
        ]
        records = await index.index_batch(docs)
        assert len(records) == 3

    @pytest.mark.asyncio
    async def test_optimize_index(self, index: VectorIndex) -> None:
        result = await index.optimize_index()
        assert "total_vectors" in result
        assert "optimized" in result

    @pytest.mark.asyncio
    async def test_get_document_count(self, index: VectorIndex) -> None:
        await index.index_document(VectorMemoryDocument(content="Test"))
        count = await index.get_document_count()
        assert count > 0

    @pytest.mark.asyncio
    async def test_reindex_empty(self, index: VectorIndex) -> None:
        records = await index.reindex()
        assert records == []

    @pytest.mark.asyncio
    async def test_delete_index(self, index: VectorIndex) -> None:
        doc = VectorMemoryDocument(content="Delete me")
        record = await index.index_document(doc)
        count = await index.delete_index([record.vector_id])
        assert count == 1


# =========================================================================
# Vector Memory Engine Tests
# =========================================================================


class TestVectorMemoryEngine:
    @pytest.mark.asyncio
    async def test_initialization(self, engine: VectorMemoryEngine) -> None:
        await engine.initialize()
        assert engine.lifecycle.is_ready
        health = await engine.health()
        assert health["status"] == "healthy"
        assert "lifecycle_state" in health

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, engine: VectorMemoryEngine, sample_record: VectorRecord) -> None:
        await engine.initialize()
        result = await engine.store(sample_record)
        assert result.success
        assert result.vector_id

        retrieved = await engine.retrieve(result.vector_id)
        assert retrieved is not None
        assert retrieved.content == sample_record.content
        assert retrieved.source_id == sample_record.source_id
        assert retrieved.memory_type == sample_record.memory_type

    @pytest.mark.asyncio
    async def test_store_without_embedding(self, engine: VectorMemoryEngine) -> None:
        await engine.initialize()
        record = VectorRecord(content="Generate embedding for me", memory_type=MemoryCategory.KNOWLEDGE)
        result = await engine.store(record)
        assert result.success
        assert len(result.record.embedding) > 0

    @pytest.mark.asyncio
    async def test_update(self, engine: VectorMemoryEngine, sample_record: VectorRecord) -> None:
        await engine.initialize()
        result = await engine.store(sample_record)
        assert result.success

        updated_record = result.record
        updated_record.content = "Updated content"
        update_result = await engine.update(updated_record)
        assert update_result.success

        retrieved = await engine.retrieve(result.vector_id)
        assert retrieved is not None
        assert retrieved.content == "Updated content"

    @pytest.mark.asyncio
    async def test_delete(self, engine: VectorMemoryEngine, sample_record: VectorRecord) -> None:
        await engine.initialize()
        result = await engine.store(sample_record)
        assert result.success

        deleted = await engine.delete(result.vector_id)
        assert deleted

        retrieved = await engine.retrieve(result.vector_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_search(self, engine: VectorMemoryEngine, sample_record: VectorRecord) -> None:
        await engine.initialize()
        await engine.store(sample_record)

        query = VectorMemoryQuery(query=sample_record.content, top_k=5)
        result = await engine.search(query)
        assert result.total >= 1

    @pytest.mark.asyncio
    async def test_similarity_search(self, engine: VectorMemoryEngine, sample_record: VectorRecord) -> None:
        await engine.initialize()
        result = await engine.store(sample_record)
        emb = result.record.embedding

        sim_result = await engine.similarity_search(embedding=emb, top_k=5)
        assert sim_result.total >= 1

    @pytest.mark.asyncio
    async def test_hybrid_search(self, engine: VectorMemoryEngine, sample_record: VectorRecord) -> None:
        await engine.initialize()
        result = await engine.store(sample_record)

        hybrid_result = await engine.hybrid_search(
            query_text=sample_record.content,
            query_embedding=result.record.embedding,
            top_k=5,
        )
        assert hybrid_result.total >= 1

    @pytest.mark.asyncio
    async def test_search_with_metadata_filters(self, engine: VectorMemoryEngine) -> None:
        await engine.initialize()
        record1 = VectorRecord(content="Knowledge item", user_id="u1", memory_type=MemoryCategory.KNOWLEDGE)
        record2 = VectorRecord(content="Conversation item", user_id="u2", memory_type=MemoryCategory.CONVERSATION)
        await engine.store(record1)
        await engine.store(record2)

        query = VectorMemoryQuery(query="item", user_id="u1", top_k=5)
        result = await engine.search(query)
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_consolidate(self, engine: VectorMemoryEngine) -> None:
        await engine.initialize()
        await engine.store(VectorRecord(content="duplicate text", embedding=[0.1, 0.2]))
        await engine.store(VectorRecord(content="duplicate text", embedding=[0.1, 0.2]))
        result = await engine.consolidate()
        assert result["success"]

    @pytest.mark.asyncio
    async def test_reindex(self, engine: VectorMemoryEngine) -> None:
        await engine.initialize()
        result = await engine.reindex()
        assert result["success"]

    @pytest.mark.asyncio
    async def test_index_document(self, engine: VectorMemoryEngine) -> None:
        await engine.initialize()
        doc = VectorMemoryDocument(
            source_id="src1",
            content="Document to index",
            memory_type=MemoryCategory.EXTERNAL,
        )
        result = await engine.index_document(doc)
        assert result.success
        assert result.record.vector_id

    @pytest.mark.asyncio
    async def test_get_statistics(self, engine: VectorMemoryEngine) -> None:
        await engine.initialize()
        await engine.store(VectorRecord(content="Item 1", memory_type=MemoryCategory.KNOWLEDGE))
        await engine.store(VectorRecord(content="Item 2", memory_type=MemoryCategory.CONVERSATION))
        stats = await engine.get_statistics()
        assert stats.total_vectors == 2
        assert "knowledge" in stats.vectors_by_category

    @pytest.mark.asyncio
    async def test_shutdown(self, engine: VectorMemoryEngine) -> None:
        await engine.initialize()
        await engine.shutdown()
        assert engine.lifecycle.is_shutdown

    @pytest.mark.asyncio
    async def test_scoped_search_user_isolation(self, engine: VectorMemoryEngine) -> None:
        await engine.initialize()
        await engine.store(VectorRecord(content="User 1 secret", user_id="u1"))
        await engine.store(VectorRecord(content="User 2 secret", user_id="u2"))

        query = VectorMemoryQuery(query="secret", user_id="u1", top_k=5)
        result = await engine.search(query)
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_scoped_search_category_isolation(self, engine: VectorMemoryEngine) -> None:
        await engine.initialize()
        await engine.store(VectorRecord(content="Goal record", memory_type=MemoryCategory.GOAL))
        await engine.store(VectorRecord(content="Task record", memory_type=MemoryCategory.TASK))

        query = VectorMemoryQuery(query="record", memory_category=MemoryCategory.GOAL, top_k=5)
        result = await engine.search(query)
        assert result.total == 1
        assert result.results[0].memory_type == MemoryCategory.GOAL

    @pytest.mark.asyncio
    async def test_threshold_filtering(self, engine: VectorMemoryEngine) -> None:
        await engine.initialize()
        await engine.store(VectorRecord(content="query", embedding=[1.0, 0.0, 0.0]))
        await engine.store(VectorRecord(content="unrelated", embedding=[0.0, 1.0, 0.0]))

        query = VectorMemoryQuery(query="query", top_k=5, threshold=0.9)
        result = await engine.search(query)
        assert result.total <= 1

    @pytest.mark.asyncio
    async def test_tag_filtering(self, engine: VectorMemoryEngine) -> None:
        await engine.initialize()
        await engine.store(VectorRecord(content="Tagged", tags=["important", "priority"]))
        await engine.store(VectorRecord(content="Untagged"))

        query = VectorMemoryQuery(query="Tagged", tags=["priority"], top_k=5)
        result = await engine.search(query)
        assert result.total >= 1


# =========================================================================
# Metrics Tests
# =========================================================================


class TestVectorMetrics:
    def test_initial_values(self) -> None:
        m = VectorMetrics()
        summary = m.get_summary()
        assert summary["vectors_stored"] == 0
        assert summary["total_searches"] == 0

    def test_increment(self) -> None:
        m = VectorMetrics()
        m.increment_vectors_stored(5)
        m.increment_vectors_indexed(3)
        m.record_search()
        m.record_consolidation()
        summary = m.get_summary()
        assert summary["vectors_stored"] == 5
        assert summary["vectors_indexed"] == 3
        assert summary["total_searches"] == 1
        assert summary["consolidations_run"] == 1

    def test_latency_recording(self) -> None:
        m = VectorMetrics()
        m.record_retrieval_latency(10.5)
        m.record_indexing_latency(20.3)
        m.record_embedding_latency(5.2)
        summary = m.get_summary()
        assert summary["avg_retrieval_latency_ms"] == 10.5
        assert summary["avg_indexing_latency_ms"] == 20.3
        assert summary["avg_embedding_latency_ms"] == 5.2

    def test_cache(self) -> None:
        m = VectorMetrics()
        m.record_cache_hit()
        m.record_cache_miss()
        summary = m.get_summary()
        assert summary["cache_hits"] == 1
        assert summary["cache_misses"] == 1

    def test_storage_usage(self) -> None:
        m = VectorMetrics()
        m.record_storage_usage(1024)
        summary = m.get_summary()
        assert summary["storage_usage_bytes"] == 1024

    def test_reset(self) -> None:
        m = VectorMetrics()
        m.increment_vectors_stored(5)
        m.reset()
        summary = m.get_summary()
        assert summary["vectors_stored"] == 0

    def test_singleton(self) -> None:
        m1 = get_vector_metrics()
        m2 = get_vector_metrics()
        assert m1 is m2


# =========================================================================
# Tracing Tests
# =========================================================================


class TestVectorTracer:
    def test_start_and_end_span(self) -> None:
        tracer = VectorTracer()
        span = tracer.start_span("test_op")
        assert isinstance(span, VectorSpan)
        assert span.operation == "test_op"

        trace = tracer.end_span(span)
        assert isinstance(trace, VectorTrace)
        assert trace.operation == "test_op"
        assert trace.status == "success"

    def test_error_span(self) -> None:
        tracer = VectorTracer()
        span = tracer.start_span("error_op")
        trace = tracer.end_span(span, error=True, error_message="test error")
        assert trace.status == "error"

    def test_get_traces(self) -> None:
        tracer = VectorTracer()
        for i in range(5):
            span = tracer.start_span(f"op_{i}")
            tracer.end_span(span)

        traces = tracer.get_traces(limit=3)
        assert len(traces) == 3

    def test_get_traces_by_operation(self) -> None:
        tracer = VectorTracer()
        for i in range(3):
            span = tracer.start_span("same_op")
            tracer.end_span(span)

        traces = tracer.get_traces_by_operation("same_op")
        assert len(traces) == 3

    def test_error_count(self) -> None:
        tracer = VectorTracer()
        for i in range(3):
            span = tracer.start_span("good")
            tracer.end_span(span)
        for i in range(2):
            span = tracer.start_span("bad")
            tracer.end_span(span, error=True)

        assert tracer.get_error_count() == 2

    def test_reset(self) -> None:
        tracer = VectorTracer()
        for i in range(3):
            span = tracer.start_span("op")
            tracer.end_span(span)

        assert tracer.get_total_count() == 3
        tracer.reset()
        assert tracer.get_total_count() == 0

    def test_singleton(self) -> None:
        from app.vector_memory.tracing import get_vector_tracer as gvt
        t1 = gvt()
        t2 = gvt()
        assert t1 is t2


# =========================================================================
# Factory Tests
# =========================================================================


class TestVectorMemoryFactory:
    def test_create_engine_default(self) -> None:
        factory = VectorMemoryFactory()
        engine = factory.create_engine()
        assert isinstance(engine, VectorMemoryEngine)
        assert engine.embedder.provider_id == "in_memory"

    def test_create_engine_with_storage(self) -> None:
        factory = VectorMemoryFactory()
        engine = factory.create_engine_with_storage(
            storage_type="in_memory",
            embedding_type="in_memory",
        )
        assert isinstance(engine, VectorMemoryEngine)

    def test_create_engine_with_custom_components(self) -> None:
        embedder = InMemoryEmbeddingProvider(dimension=128)
        repository = InMemoryVectorRepository()
        factory = VectorMemoryFactory(embedder=embedder, repository=repository)
        engine = factory.create_engine()
        assert engine.embedder.embedding_dimension == 128

    def test_register_embedding_provider(self) -> None:
        class CustomProvider(InMemoryEmbeddingProvider):
            pass

        VectorMemoryFactory.register_embedding_provider("custom", CustomProvider)
        assert "custom" in VectorMemoryFactory._embedding_providers


# =========================================================================
# Lifecycle State Integration Tests
# =========================================================================


class TestLifecycleStates:
    @pytest.mark.asyncio
    async def test_engine_lifecycle_sequence(self) -> None:
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        assert engine.lifecycle.state == VectorMemoryState.REGISTERED
        await engine.initialize()
        assert engine.lifecycle.state == VectorMemoryState.READY
        q = VectorMemoryQuery(query="test")
        await engine.search(q)
        assert engine.lifecycle.state == VectorMemoryState.READY
        await engine.shutdown()
        assert engine.lifecycle.state == VectorMemoryState.SHUTDOWN


# =========================================================================
# End-to-End Integration Tests
# =========================================================================


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_workflow(self) -> None:
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        await engine.initialize()

        records = [
            VectorRecord(content="Machine learning is a subset of AI", user_id="u1", memory_type=MemoryCategory.KNOWLEDGE, tags=["ai", "ml"]),
            VectorRecord(content="Deep learning uses neural networks", user_id="u1", memory_type=MemoryCategory.KNOWLEDGE, tags=["ai", "deep-learning"]),
            VectorRecord(content="User likes programming in Python", user_id="u1", memory_type=MemoryCategory.USER_PROFILE, tags=["profile"]),
            VectorRecord(content="Help me debug my code", user_id="u1", memory_type=MemoryCategory.CONVERSATION, tags=["conversation"]),
        ]

        for rec in records:
            result = await engine.store(rec)
            assert result.success

        stats = await engine.get_statistics()
        assert stats.total_vectors == 4

        query = VectorMemoryQuery(query="artificial intelligence", user_id="u1", top_k=2)
        result = await engine.search(query)
        assert result.total >= 1

        consolidate_result = await engine.consolidate()
        assert consolidate_result["success"]

        reindex_result = await engine.reindex()
        assert reindex_result["success"]

        await engine.shutdown()
        assert engine.lifecycle.is_shutdown

    @pytest.mark.asyncio
    async def test_memory_categories(self) -> None:
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        await engine.initialize()

        for category in MemoryCategory:
            record = VectorRecord(content=f"Test {category.value}", memory_type=category)
            result = await engine.store(record)
            assert result.success

        stats = await engine.get_statistics()
        assert stats.total_vectors == len(MemoryCategory)


# =========================================================================
# Edge Cases
# =========================================================================


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_content(self) -> None:
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        await engine.initialize()
        record = VectorRecord(content="", memory_type=MemoryCategory.KNOWLEDGE)
        result = await engine.store(record)
        assert result.success

    @pytest.mark.asyncio
    async def test_very_long_content(self) -> None:
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        await engine.initialize()
        long_content = "word " * 10000
        record = VectorRecord(content=long_content, memory_type=MemoryCategory.KNOWLEDGE)
        result = await engine.store(record)
        assert result.success

    @pytest.mark.asyncio
    async def test_special_characters(self) -> None:
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        await engine.initialize()
        special = "😀 日本語 العربية решение! @#$%^&*()"
        record = VectorRecord(content=special, memory_type=MemoryCategory.KNOWLEDGE)
        result = await engine.store(record)
        assert result.success

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent(self) -> None:
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        await engine.initialize()
        retrieved = await engine.retrieve("nonexistent-id")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self) -> None:
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        await engine.initialize()
        deleted = await engine.delete("nonexistent-id")
        assert not deleted

    @pytest.mark.asyncio
    async def test_idempotent_shutdown(self) -> None:
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        await engine.initialize()
        await engine.shutdown()
        await engine.shutdown()
        assert engine.lifecycle.is_shutdown

    @pytest.mark.asyncio
    async def test_idempotent_initialize(self) -> None:
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        await engine.initialize()
        await engine.initialize()
        assert engine.lifecycle.state == VectorMemoryState.READY

    @pytest.mark.asyncio
    async def test_get_statistics_empty(self) -> None:
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        await engine.initialize()
        stats = await engine.get_statistics()
        assert stats.total_vectors == 0

    @pytest.mark.asyncio
    async def test_concurrent_access(self) -> None:
        import asyncio
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        await engine.initialize()

        async def store_record(i: int) -> VectorMemoryResult:
            return await engine.store(
                VectorRecord(content=f"Record {i}", user_id="u1", memory_type=MemoryCategory.KNOWLEDGE)
            )

        results = await asyncio.gather(*[store_record(i) for i in range(20)])
        assert all(r.success for r in results)

        stats = await engine.get_statistics()
        assert stats.total_vectors == 20

    @pytest.mark.asyncio
    async def test_namespace_isolation(self) -> None:
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        await engine.initialize()
        await engine.store(VectorRecord(content="Public data", user_id="u1"))
        await engine.store(VectorRecord(content="Private data", user_id="u2"))

        query = VectorMemoryQuery(query="data", user_id="u1", top_k=5)
        result = await engine.search(query)
        for rec in result.results:
            assert rec.user_id == "u1"

    @pytest.mark.asyncio
    async def test_session_isolation(self) -> None:
        engine = VectorMemoryEngine(
            embedder=InMemoryEmbeddingProvider(),
            repository=InMemoryVectorRepository(),
        )
        await engine.initialize()
        await engine.store(VectorRecord(content="Session A data", session_id="sess-a"))
        await engine.store(VectorRecord(content="Session B data", session_id="sess-b"))

        query = VectorMemoryQuery(query="data", session_id="sess-a", top_k=5)
        result = await engine.search(query)
        for rec in result.results:
            assert rec.session_id == "sess-a"
