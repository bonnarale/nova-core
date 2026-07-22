"""Integration tests for the Learning Engine — full lifecycle and CognitiveEngine integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.learning.consolidator import DefaultConsolidator
from app.learning.engine import LearningEngine
from app.learning.events import (
    artifact_consolidated_event,
    artifact_stored_event,
    execution_learned_event,
    knowledge_extracted_event,
    memory_ranked_event,
    retrieval_performed_event,
)
from app.learning.extractor import DefaultKnowledgeExtractor
from app.learning.factory import LearningEngineFactory
from app.learning.models import (
    ArtifactType,
    KnowledgeArtifact,
    LearningEventType,
    RankedMemory,
)
from app.learning.ranker import MultiFactorRanker
from app.learning.repository import LearningRepository
from app.learning.retriever import SemanticRetriever


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def store():
    return LearningRepository()


@pytest.fixture
def event_bus():
    bus = MagicMock()
    bus.emit = AsyncMock()
    return bus


@pytest.fixture
def engine(store, event_bus):
    return LearningEngine(
        store=store,
        event_bus=event_bus,
        auto_consolidate=False,
    )


@pytest.fixture
def auto_consolidate_engine(store, event_bus):
    return LearningEngine(
        store=store,
        event_bus=event_bus,
        auto_consolidate=True,
        consolidation_interval=2,
    )


# ======================================================================
# LearningEngine — learn_from_execution
# ======================================================================

class TestLearnFromExecution:
    @pytest.mark.asyncio
    async def test_basic_extraction(self, engine):
        execution_data = {"id": "e1", "status": "COMPLETED", "user_id": "u1"}
        task_data = {
            "id": "t1",
            "goal": "Build a REST API with FastAPI",
            "status": "COMPLETED",
            "artifacts": {"step_1": {"output": "created endpoints"}},
            "events": [],
        }
        session = await engine.learn_from_execution(execution_data, task_data)
        assert session.status == "completed"
        assert session.artifacts_extracted > 0
        assert session.artifacts_stored > 0
        assert session.error is None

    @pytest.mark.asyncio
    async def test_stores_artifacts(self, engine):
        execution_data = {"id": "e2", "status": "COMPLETED"}
        task_data = {
            "id": "t2",
            "goal": "Optimize database queries for performance",
            "status": "COMPLETED",
            "artifacts": {},
            "events": [],
        }
        session = await engine.learn_from_execution(execution_data, task_data)
        artifacts = await engine.list_artifacts()
        assert len(artifacts) == session.artifacts_stored

    @pytest.mark.asyncio
    async def test_emits_events(self, engine, event_bus):
        execution_data = {"id": "e3", "status": "COMPLETED"}
        task_data = {
            "id": "t3",
            "goal": "Research machine learning techniques",
            "status": "COMPLETED",
            "artifacts": {},
            "events": [],
        }
        await engine.learn_from_execution(execution_data, task_data)
        event_types = [
            call.args[0] for call in event_bus.emit.call_args_list
        ]
        assert LearningEventType.KNOWLEDGE_EXTRACTED.value in event_types
        assert LearningEventType.ARTIFACT_STORED.value in event_types
        assert LearningEventType.EXECUTION_LEARNED.value in event_types

    @pytest.mark.asyncio
    async def test_error_in_extraction_sets_failed(self, store, event_bus):
        extractor = MagicMock()
        extractor.extract = AsyncMock(side_effect=RuntimeError("boom"))
        eng = LearningEngine(store=store, extractor=extractor, event_bus=event_bus)
        session = await eng.learn_from_execution({"id": "e1"}, {"id": "t1"})
        assert session.status == "failed"
        assert "boom" in session.error

    @pytest.mark.asyncio
    async def test_empty_goal_still_extracts(self, engine):
        session = await engine.learn_from_execution(
            {"id": "e1", "status": "COMPLETED"},
            {"id": "t1", "goal": "", "status": "COMPLETED", "artifacts": {}, "events": []},
        )
        assert session.status == "completed"


# ======================================================================
# LearningEngine — search
# ======================================================================

class TestLearningSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(self, engine):
        await engine.learn_from_execution(
            {"id": "e1", "status": "COMPLETED"},
            {"id": "t1", "goal": "Python web development", "status": "COMPLETED", "artifacts": {}, "events": []},
        )
        result = await engine.search("Python web")
        assert result.total > 0

    @pytest.mark.asyncio
    async def test_search_with_user_filter(self, engine):
        await engine.learn_from_execution(
            {"id": "e1", "status": "COMPLETED", "user_id": "u1"},
            {"id": "t1", "goal": "Python web", "status": "COMPLETED", "user_id": "u1", "artifacts": {}, "events": []},
        )
        await engine.learn_from_execution(
            {"id": "e2", "status": "COMPLETED", "user_id": "u2"},
            {"id": "t2", "goal": "Python web", "status": "COMPLETED", "user_id": "u2", "artifacts": {}, "events": []},
        )
        result = await engine.search("Python", user_id="u1")
        assert result.total >= 1
        for r in result.results:
            assert r.artifact.user_id == "u1"

    @pytest.mark.asyncio
    async def test_search_emits_event(self, engine, event_bus):
        await engine.search("test query")
        event_types = [call.args[0] for call in event_bus.emit.call_args_list]
        assert LearningEventType.RETRIEVAL_PERFORMED.value in event_types


# ======================================================================
# LearningEngine — rank
# ======================================================================

class TestLearningRank:
    @pytest.mark.asyncio
    async def test_rank_default(self, engine):
        await engine.learn_from_execution(
            {"id": "e1", "status": "COMPLETED"},
            {"id": "t1", "goal": "Build FastAPI application", "status": "COMPLETED", "artifacts": {}, "events": []},
        )
        ranked = await engine.rank(query="FastAPI")
        assert len(ranked) > 0
        assert isinstance(ranked[0], RankedMemory)
        assert ranked[0].score > 0

    @pytest.mark.asyncio
    async def test_rank_by_user(self, engine):
        await engine.learn_from_execution(
            {"id": "e1", "status": "COMPLETED", "user_id": "u1"},
            {"id": "t1", "goal": "Test task A", "status": "COMPLETED", "user_id": "u1", "artifacts": {}, "events": []},
        )
        ranked = await engine.rank(user_id="u1")
        assert len(ranked) >= 1


# ======================================================================
# LearningEngine — consolidation
# ======================================================================

class TestLearningConsolidation:
    @pytest.mark.asyncio
    async def test_consolidation_reduces_duplicates(self, store, event_bus):
        eng = LearningEngine(store=store, event_bus=event_bus, auto_consolidate=False)
        await store.create(KnowledgeArtifact(
            id="a1", artifact_type="fact",
            content="Python is a programming language used for many things",
            tags=["python"],
        ))
        await store.create(KnowledgeArtifact(
            id="a2", artifact_type="fact",
            content="Python is a programming language used for many things in data science",
            tags=["python", "data"],
        ))
        result = await eng.run_consolidation()
        assert result.duplicates_removed >= 1

    @pytest.mark.asyncio
    async def test_auto_consolidation(self, auto_consolidate_engine):
        for i in range(3):
            await auto_consolidate_engine.learn_from_execution(
                {"id": f"e{i}", "status": "COMPLETED"},
                {
                    "id": f"t{i}",
                    "goal": "Optimize performance and speed",
                    "status": "COMPLETED",
                    "artifacts": {},
                    "events": [],
                },
            )
        assert auto_consolidate_engine._session_counter == 3


# ======================================================================
# LearningEngine — stats and listing
# ======================================================================

class TestLearningStats:
    @pytest.mark.asyncio
    async def test_stats(self, engine):
        await engine.learn_from_execution(
            {"id": "e1", "status": "COMPLETED"},
            {"id": "t1", "goal": "Test goal", "status": "COMPLETED", "artifacts": {}, "events": []},
        )
        stats = await engine.stats()
        assert stats["total_artifacts"] > 0
        assert stats["total_sessions"] == 1

    @pytest.mark.asyncio
    async def test_list_artifacts(self, engine):
        await engine.learn_from_execution(
            {"id": "e1", "status": "COMPLETED"},
            {"id": "t1", "goal": "Build something", "status": "COMPLETED", "artifacts": {}, "events": []},
        )
        arts = await engine.list_artifacts()
        assert len(arts) > 0

    @pytest.mark.asyncio
    async def test_get_artifact(self, engine):
        await engine.learn_from_execution(
            {"id": "e1", "status": "COMPLETED"},
            {"id": "t1", "goal": "Test goal", "status": "COMPLETED", "artifacts": {}, "events": []},
        )
        arts = await engine.list_artifacts()
        fetched = await engine.get_artifact(arts[0].id)
        assert fetched is not None

    @pytest.mark.asyncio
    async def test_delete_artifact(self, engine):
        await engine.learn_from_execution(
            {"id": "e1", "status": "COMPLETED"},
            {"id": "t1", "goal": "Test goal", "status": "COMPLETED", "artifacts": {}, "events": []},
        )
        arts = await engine.list_artifacts()
        deleted = await engine.delete_artifact(arts[0].id)
        assert deleted is True
        assert await engine.get_artifact(arts[0].id) is None

    @pytest.mark.asyncio
    async def test_get_session(self, engine):
        session = await engine.learn_from_execution(
            {"id": "e1", "status": "COMPLETED"},
            {"id": "t1", "goal": "Test", "status": "COMPLETED", "artifacts": {}, "events": []},
        )
        fetched = engine.get_session(session.session_id)
        assert fetched is not None
        assert fetched.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, engine):
        assert engine.get_session("nonexistent") is None


# ======================================================================
# LearningEngineFactory
# ======================================================================

class TestLearningEngineFactory:
    def test_create_default(self):
        eng = LearningEngineFactory.create()
        assert isinstance(eng, LearningEngine)
        assert isinstance(eng.store, LearningRepository)
        assert isinstance(eng.extractor, DefaultKnowledgeExtractor)
        assert isinstance(eng.ranker, MultiFactorRanker)
        assert isinstance(eng.consolidator, DefaultConsolidator)
        assert isinstance(eng.retriever, SemanticRetriever)

    def test_create_with_custom_components(self):
        custom_store = LearningRepository()
        eng = LearningEngineFactory.create(store=custom_store)
        assert eng.store is custom_store

    def test_create_with_event_bus(self):
        bus = MagicMock()
        eng = LearningEngineFactory.create(event_bus=bus)
        assert eng._event_bus is bus


# ======================================================================
# Event helpers
# ======================================================================

class TestEventHelpers:
    def test_knowledge_extracted_event(self):
        event = knowledge_extracted_event("e1", 3, task_id="t1", user_id="u1")
        assert event.event_type == LearningEventType.KNOWLEDGE_EXTRACTED.value
        assert event.payload["artifact_count"] == 3

    def test_artifact_stored_event(self):
        event = artifact_stored_event("a1", "fact", source_execution_id="e1")
        assert event.event_type == LearningEventType.ARTIFACT_STORED.value
        assert event.payload["artifact_id"] == "a1"

    def test_artifact_consolidated_event(self):
        event = artifact_consolidated_event(2, 5, ["a", "b"])
        assert event.event_type == LearningEventType.ARTIFACT_CONSOLIDATED.value
        assert event.payload["duplicates_removed"] == 5

    def test_memory_ranked_event(self):
        event = memory_ranked_event("query", 0.9, 10)
        assert event.event_type == LearningEventType.MEMORY_RANKED.value
        assert event.payload["top_score"] == 0.9

    def test_retrieval_performed_event(self):
        event = retrieval_performed_event("query", 5, user_id="u1")
        assert event.event_type == LearningEventType.RETRIEVAL_PERFORMED.value

    def test_execution_learned_event(self):
        event = execution_learned_event("e1", "s1", 3, 2)
        assert event.event_type == LearningEventType.EXECUTION_LEARNED.value
        assert event.payload["artifacts_extracted"] == 3


# ======================================================================
# CognitiveEngine integration (learning_engine param)
# ======================================================================

class TestCognitiveEngineLearningIntegration:
    @pytest.fixture
    def mock_learning_engine(self):
        le = MagicMock()
        le.learn_from_execution = AsyncMock()
        return le

    @pytest.fixture
    def engine_with_learning(self, mock_learning_engine):
        from app.cognitive.engine import CognitiveEngine
        return CognitiveEngine(
            goal_manager=MagicMock(list_goals=AsyncMock(return_value=[])),
            task_manager=MagicMock(list_tasks=AsyncMock(return_value=[])),
            agent_manager=MagicMock(list_runtime_agents=MagicMock(return_value=[])),
            profile_memory=MagicMock(get_profile=AsyncMock(return_value=None)),
            conversation_memory=MagicMock(get_history=AsyncMock(return_value=[])),
            learning_engine=mock_learning_engine,
        )

    @pytest.mark.asyncio
    async def test_create_task_triggers_learning(self, engine_with_learning, mock_learning_engine):
        engine_with_learning._task_manager.create_task = AsyncMock(
            return_value={"id": "t1", "goal": "test", "status": "CREATED"}
        )
        from app.cognitive.context import CognitiveContext
        from app.cognitive.decision import CognitiveDecision, DecisionAction

        ctx = CognitiveContext(raw_input="build an app", user_id="u1")
        decision = CognitiveDecision(
            action=DecisionAction.CREATE_TASK,
            payload={"goal": "build an app", "assigned_agent": "coder"},
        )
        result = await engine_with_learning._execute_decision(decision, ctx)
        assert result is not None
        mock_learning_engine.learn_from_execution.assert_awaited_once()
