"""Unit tests for the Learning Engine module — models, extractor, ranker, consolidator, retriever, repository."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.learning.base import (
    KnowledgeConsolidator,
    KnowledgeExtractor,
    LearningRetriever,
    LearningStore,
    MemoryRanker,
)
from app.learning.consolidator import DefaultConsolidator
from app.learning.extractor import DefaultKnowledgeExtractor
from app.learning.models import (
    ArtifactType,
    ConsolidationResult,
    ExtractedKnowledge,
    KnowledgeArtifact,
    LearningEvent,
    LearningEventType,
    LearningSession,
    MemoryRankSource,
    RankedMemory,
    RetrievalResult,
)
from app.learning.ranker import MultiFactorRanker
from app.learning.repository import LearningRepository
from app.learning.retriever import SemanticRetriever


# ======================================================================
# Models
# ======================================================================

class TestKnowledgeArtifact:
    def test_new_id_is_uuid(self):
        aid = KnowledgeArtifact.new_id()
        assert isinstance(aid, str)
        assert len(aid) == 36

    def test_to_dict(self):
        art = KnowledgeArtifact(
            id="abc-123",
            artifact_type=ArtifactType.FACT.value,
            content="test content",
            summary="summary",
            tags=["a", "b"],
            confidence=0.8,
            importance_score=0.6,
        )
        d = art.to_dict()
        assert d["id"] == "abc-123"
        assert d["artifact_type"] == "fact"
        assert d["tags"] == ["a", "b"]
        assert d["confidence"] == 0.8

    def test_from_dict(self):
        data = {
            "id": "x",
            "artifact_type": "procedure",
            "content": "do X",
            "summary": "X",
            "tags": ["x"],
            "confidence": 0.5,
        }
        art = KnowledgeArtifact.from_dict(data)
        assert art.id == "x"
        assert art.artifact_type == "procedure"

    def test_defaults(self):
        art = KnowledgeArtifact(id="1", artifact_type="fact", content="hi")
        assert art.summary == ""
        assert art.tags == []
        assert art.source_execution_id is None
        assert art.access_count == 0
        assert art.metadata == {}


class TestArtifactType:
    def test_all_values(self):
        values = {e.value for e in ArtifactType}
        assert "procedure" in values
        assert "pattern" in values
        assert "fact" in values
        assert "strategy" in values
        assert "error_handling" in values
        assert "optimization" in values

    def test_count(self):
        assert len(ArtifactType) == 6


class TestLearningEventType:
    def test_event_types(self):
        assert LearningEventType.KNOWLEDGE_EXTRACTED.value == "learning.knowledge_extracted"
        assert LearningEventType.ARTIFACT_STORED.value == "learning.artifact_stored"
        assert LearningEventType.ARTIFACT_CONSOLIDATED.value == "learning.artifact_consolidated"
        assert LearningEventType.MEMORY_RANKED.value == "learning.memory_ranked"
        assert LearningEventType.RETRIEVAL_PERFORMED.value == "learning.retrieval_performed"
        assert LearningEventType.EXECUTION_LEARNED.value == "learning.execution_learned"


class TestLearningEvent:
    def test_to_dict(self):
        event = LearningEvent(
            event_type="test.event",
            payload={"key": "value"},
        )
        d = event.to_dict()
        assert d["event_type"] == "test.event"
        assert d["payload"]["key"] == "value"


class TestExtractedKnowledge:
    def test_to_dict(self):
        ek = ExtractedKnowledge(
            artifacts=[
                KnowledgeArtifact(id="a1", artifact_type="fact", content="c1"),
                KnowledgeArtifact(id="a2", artifact_type="pattern", content="c2"),
            ],
            execution_id="e1",
            task_id="t1",
            extraction_method="test",
            confidence=0.7,
        )
        d = ek.to_dict()
        assert d["artifact_count"] == 2
        assert d["execution_id"] == "e1"

    def test_defaults(self):
        ek = ExtractedKnowledge()
        assert ek.artifacts == []
        assert ek.execution_id == ""


class TestRankedMemory:
    def test_to_dict(self):
        art = KnowledgeArtifact(id="r1", artifact_type="fact", content="content")
        rm = RankedMemory(artifact=art, score=0.9, rank_factors={"recency": 1.0})
        d = rm.to_dict()
        assert d["score"] == 0.9
        assert d["rank_factors"]["recency"] == 1.0
        assert d["id"] == "r1"


class TestConsolidationResult:
    def test_to_dict(self):
        cr = ConsolidationResult(
            merged_count=2,
            duplicates_removed=3,
            artifacts_affected=["a", "b", "c"],
        )
        d = cr.to_dict()
        assert d["merged_count"] == 2
        assert d["duplicates_removed"] == 3


class TestRetrievalResult:
    def test_to_dict(self):
        rr = RetrievalResult(
            results=[
                RankedMemory(
                    artifact=KnowledgeArtifact(id="r1", artifact_type="fact", content="c"),
                    score=0.8,
                )
            ],
            total=1,
            query="test",
        )
        d = rr.to_dict()
        assert d["total"] == 1
        assert d["query"] == "test"
        assert len(d["results"]) == 1


class TestLearningSession:
    def test_to_dict(self):
        session = LearningSession(
            session_id="s1",
            execution_id="e1",
            artifacts_extracted=5,
            status="completed",
        )
        d = session.to_dict()
        assert d["session_id"] == "s1"
        assert d["status"] == "completed"


class TestMemoryRankSource:
    def test_sources(self):
        assert MemoryRankSource.RECENCY.value == "recency"
        assert MemoryRankSource.IMPORTANCE.value == "importance"
        assert MemoryRankSource.RELEVANCE.value == "relevance"
        assert MemoryRankSource.FREQUENCY.value == "frequency"


# ======================================================================
# Repository
# ======================================================================

class TestLearningRepository:
    @pytest.fixture
    def repo(self):
        return LearningRepository()

    @pytest.mark.asyncio
    async def test_create_and_get(self, repo):
        art = KnowledgeArtifact(id="a1", artifact_type="fact", content="test")
        created = await repo.create(art)
        assert created.id == "a1"
        fetched = await repo.get("a1")
        assert fetched is not None
        assert fetched.content == "test"

    @pytest.mark.asyncio
    async def test_get_not_found(self, repo):
        assert await repo.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_update(self, repo):
        art = KnowledgeArtifact(id="a1", artifact_type="fact", content="v1")
        await repo.create(art)
        art.content = "v2"
        updated = await repo.update(art)
        assert updated.content == "v2"

    @pytest.mark.asyncio
    async def test_update_not_found(self, repo):
        art = KnowledgeArtifact(id="missing", artifact_type="fact", content="v1")
        result = await repo.update(art)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, repo):
        art = KnowledgeArtifact(id="a1", artifact_type="fact", content="x")
        await repo.create(art)
        assert await repo.delete("a1") is True
        assert await repo.get("a1") is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo):
        assert await repo.delete("missing") is False

    @pytest.mark.asyncio
    async def test_list_by_user(self, repo):
        await repo.create(KnowledgeArtifact(id="a1", artifact_type="fact", content="x", user_id="u1"))
        await repo.create(KnowledgeArtifact(id="a2", artifact_type="fact", content="y", user_id="u2"))
        result = await repo.list_by_user("u1")
        assert len(result) == 1
        assert result[0].user_id == "u1"

    @pytest.mark.asyncio
    async def test_list_by_type(self, repo):
        await repo.create(KnowledgeArtifact(id="a1", artifact_type="fact", content="x"))
        await repo.create(KnowledgeArtifact(id="a2", artifact_type="pattern", content="y"))
        result = await repo.list_by_type("fact")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_by_tags(self, repo):
        await repo.create(KnowledgeArtifact(id="a1", artifact_type="fact", content="x", tags=["python", "fastapi"]))
        await repo.create(KnowledgeArtifact(id="a2", artifact_type="fact", content="y", tags=["rust"]))
        result = await repo.search_by_tags(["python"])
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_count(self, repo):
        await repo.create(KnowledgeArtifact(id="a1", artifact_type="fact", content="x"))
        assert await repo.count() == 1

    @pytest.mark.asyncio
    async def test_count_by_type(self, repo):
        await repo.create(KnowledgeArtifact(id="a1", artifact_type="fact", content="x"))
        await repo.create(KnowledgeArtifact(id="a2", artifact_type="pattern", content="y"))
        await repo.create(KnowledgeArtifact(id="a3", artifact_type="fact", content="z"))
        counts = await repo.count_by_type()
        assert counts["fact"] == 2
        assert counts["pattern"] == 1


# ======================================================================
# Extractor
# ======================================================================

class TestDefaultKnowledgeExtractor:
    @pytest.fixture
    def extractor(self):
        return DefaultKnowledgeExtractor()

    @pytest.mark.asyncio
    async def test_extract_from_completed_task(self, extractor):
        execution_data = {"id": "e1", "user_id": "u1", "agent_id": "coder"}
        task_data = {
            "id": "t1",
            "goal": "Implement a REST API",
            "status": "COMPLETED",
            "artifacts": {"step_1": {"output": "done"}},
            "events": [],
        }
        result = await extractor.extract(execution_data, task_data)
        assert isinstance(result, ExtractedKnowledge)
        assert len(result.artifacts) > 0
        assert result.execution_id == "e1"
        assert result.task_id == "t1"
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_extract_error_events(self, extractor):
        execution_data = {"id": "e1"}
        task_data = {
            "id": "t1",
            "goal": "Run deployment",
            "status": "FAILED",
            "artifacts": {},
            "events": [
                {"type": "task.failed", "message": "connection refused"},
                {"type": "task.error", "message": "timeout"},
            ],
        }
        result = await extractor.extract(execution_data, task_data)
        error_arts = [a for a in result.artifacts if a.artifact_type == ArtifactType.ERROR_HANDLING.value]
        assert len(error_arts) > 0

    @pytest.mark.asyncio
    async def test_extract_optimization(self, extractor):
        execution_data = {"id": "e1"}
        task_data = {
            "id": "t1",
            "goal": "Optimize database query performance",
            "status": "COMPLETED",
            "artifacts": {},
            "events": [],
        }
        result = await extractor.extract(execution_data, task_data)
        opt_arts = [a for a in result.artifacts if a.artifact_type == ArtifactType.OPTIMIZATION.value]
        assert len(opt_arts) > 0

    @pytest.mark.asyncio
    async def test_extract_strategy(self, extractor):
        execution_data = {"id": "e1"}
        task_data = {
            "id": "t1",
            "goal": "Apply best practice strategy for caching",
            "status": "COMPLETED",
            "artifacts": {},
            "events": [],
        }
        result = await extractor.extract(execution_data, task_data)
        strat_arts = [a for a in result.artifacts if a.artifact_type == ArtifactType.STRATEGY.value]
        assert len(strat_arts) > 0

    @pytest.mark.asyncio
    async def test_extract_empty(self, extractor):
        result = await extractor.extract({"id": "e1"}, {"id": "t1", "goal": "", "status": "COMPLETED"})
        assert result.execution_id == "e1"

    @pytest.mark.asyncio
    async def test_extract_tags(self, extractor):
        tags = DefaultKnowledgeExtractor._extract_tags("Build a Python web application")
        assert "python" in tags
        assert "web" in tags

    @pytest.mark.asyncio
    async def test_score_importance_completed(self):
        score = DefaultKnowledgeExtractor._score_importance(
            "Implement REST API", "COMPLETED", ArtifactType.PROCEDURE
        )
        assert 0.5 < score <= 1.0

    @pytest.mark.asyncio
    async def test_compute_confidence_empty(self):
        assert DefaultKnowledgeExtractor._compute_confidence([], "COMPLETED") == 0.0


# ======================================================================
# Ranker
# ======================================================================

class TestMultiFactorRanker:
    @pytest.fixture
    def ranker(self):
        return MultiFactorRanker()

    @pytest.mark.asyncio
    async def test_rank_empty(self, ranker):
        result = await ranker.rank([], query="test")
        assert result == []

    @pytest.mark.asyncio
    async def test_rank_single_artifact(self, ranker):
        art = KnowledgeArtifact(
            id="a1", artifact_type="fact", content="Python is great",
            summary="Python", tags=["python"], importance_score=0.8,
            access_count=5,
        )
        result = await ranker.rank([art], query="python")
        assert len(result) == 1
        assert result[0].score > 0
        assert "recency" in result[0].rank_factors

    @pytest.mark.asyncio
    async def test_rank_relevance(self, ranker):
        art_relevant = KnowledgeArtifact(
            id="a1", artifact_type="fact", content="Python web framework",
            tags=["python", "web"], importance_score=0.5,
        )
        art_irrelevant = KnowledgeArtifact(
            id="a2", artifact_type="fact", content="Rust systems programming",
            tags=["rust", "systems"], importance_score=0.5,
        )
        result = await ranker.rank([art_irrelevant, art_relevant], query="python web")
        assert result[0].artifact.id == "a1"

    @pytest.mark.asyncio
    async def test_rank_importance_weight(self, ranker):
        art_high = KnowledgeArtifact(
            id="a1", artifact_type="fact", content="x", importance_score=1.0,
        )
        art_low = KnowledgeArtifact(
            id="a2", artifact_type="fact", content="x", importance_score=0.0,
        )
        result = await ranker.rank([art_low, art_high], query="x")
        assert result[0].artifact.id == "a1"


# ======================================================================
# Consolidator
# ======================================================================

class TestDefaultConsolidator:
    @pytest.fixture
    def consolidator(self):
        return DefaultConsolidator(threshold=0.7)

    @pytest.mark.asyncio
    async def test_consolidate_empty(self, consolidator):
        result = await consolidator.consolidate([])
        assert result.merged_count == 0

    @pytest.mark.asyncio
    async def test_consolidate_single(self, consolidator):
        art = KnowledgeArtifact(id="a1", artifact_type="fact", content="Python is a language")
        result = await consolidator.consolidate([art])
        assert result.merged_count == 0

    @pytest.mark.asyncio
    async def test_consolidate_duplicates(self, consolidator):
        art1 = KnowledgeArtifact(
            id="a1", artifact_type="fact",
            content="Python is a programming language used for web development",
            tags=["python"], importance_score=0.8,
        )
        art2 = KnowledgeArtifact(
            id="a2", artifact_type="fact",
            content="Python is a programming language used for web development and scripting",
            tags=["python", "scripting"], importance_score=0.6,
        )
        result = await consolidator.consolidate([art1, art2])
        assert result.merged_count >= 1
        assert result.duplicates_removed >= 1
        assert "a2" in result.artifacts_affected

    @pytest.mark.asyncio
    async def test_consolidate_different_content(self, consolidator):
        art1 = KnowledgeArtifact(id="a1", artifact_type="fact", content="Completely different topic A")
        art2 = KnowledgeArtifact(id="a2", artifact_type="fact", content="Another totally unrelated subject B")
        result = await consolidator.consolidate([art1, art2])
        assert result.merged_count == 0
        assert result.duplicates_removed == 0


# ======================================================================
# Retriever
# ======================================================================

class TestSemanticRetriever:
    @pytest.fixture
    def store(self):
        return LearningRepository()

    @pytest.fixture
    def retriever(self, store):
        return SemanticRetriever(store=store)

    @pytest.mark.asyncio
    async def test_keyword_search(self, retriever, store):
        await store.create(KnowledgeArtifact(
            id="a1", artifact_type="fact", content="Python is great for data science",
            tags=["python", "data-science"],
        ))
        await store.create(KnowledgeArtifact(
            id="a2", artifact_type="fact", content="Rust is fast",
            tags=["rust", "performance"],
        ))
        result = await retriever.retrieve("python data science")
        assert result.total > 0
        assert result.results[0].artifact.id == "a1"

    @pytest.mark.asyncio
    async def test_keyword_search_with_user_filter(self, retriever, store):
        await store.create(KnowledgeArtifact(
            id="a1", artifact_type="fact", content="Python tip", user_id="u1",
        ))
        await store.create(KnowledgeArtifact(
            id="a2", artifact_type="fact", content="Python trick", user_id="u2",
        ))
        result = await retriever.retrieve("python", user_id="u1")
        assert result.total == 1
        assert result.results[0].artifact.user_id == "u1"

    @pytest.mark.asyncio
    async def test_keyword_search_with_type_filter(self, retriever, store):
        await store.create(KnowledgeArtifact(id="a1", artifact_type="fact", content="Python tip"))
        await store.create(KnowledgeArtifact(id="a2", artifact_type="pattern", content="Python pattern"))
        result = await retriever.retrieve("python", artifact_type="pattern")
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_empty_retrieval(self, retriever):
        result = await retriever.retrieve("nonexistent query xyz")
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_no_store_returns_empty(self):
        retriever = SemanticRetriever(store=None)
        result = await retriever.retrieve("anything")
        assert result.total == 0


# ======================================================================
# ABCs
# ======================================================================

class TestABCs:
    def test_learning_store_is_abstract(self):
        with pytest.raises(TypeError):
            LearningStore()

    def test_knowledge_extractor_is_abstract(self):
        with pytest.raises(TypeError):
            KnowledgeExtractor()

    def test_memory_ranker_is_abstract(self):
        with pytest.raises(TypeError):
            MemoryRanker()

    def test_knowledge_consolidator_is_abstract(self):
        with pytest.raises(TypeError):
            KnowledgeConsolidator()

    def test_learning_retriever_is_abstract(self):
        with pytest.raises(TypeError):
            LearningRetriever()
