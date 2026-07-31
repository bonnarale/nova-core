"""Tests for CognitiveEngine semantic memory integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.cognitive.engine import CognitiveEngine
from app.cognitive.context import CognitiveContext


@pytest.fixture
def mock_semantic_memory():
    """Mock SemanticMemory with search returning results."""
    sm = AsyncMock()
    sm.search = AsyncMock(return_value=[
        {"content": "Past knowledge about AI", "score": 0.85},
        {"content": "Previous learning about ML", "score": 0.72},
    ])
    return sm


@pytest.fixture
def engine_with_semantic(mock_semantic_memory):
    """Create CognitiveEngine with mocked dependencies and semantic memory."""
    goal_manager = AsyncMock()
    goal_manager.list_goals = AsyncMock(return_value=[])
    task_manager = AsyncMock()
    task_manager.list_tasks = AsyncMock(return_value=[])
    agent_manager = MagicMock()
    agent_manager.list_runtime_agents = MagicMock(return_value=[])
    profile_memory = AsyncMock()
    profile_memory.get_profile = AsyncMock(return_value=None)
    conversation_memory = AsyncMock()
    conversation_memory.get_history = AsyncMock(return_value=[])

    engine = CognitiveEngine(
        goal_manager=goal_manager,
        task_manager=task_manager,
        agent_manager=agent_manager,
        profile_memory=profile_memory,
        conversation_memory=conversation_memory,
        semantic_memory=mock_semantic_memory,
    )
    return engine


@pytest.mark.asyncio
async def test_load_context_searches_semantic_memory(engine_with_semantic, mock_semantic_memory):
    """_load_context calls semantic_memory.search with the raw input."""
    ctx = await engine_with_semantic._load_context(
        raw_input="What is machine learning?",
        user_id=None,
        session_id=None,
    )
    mock_semantic_memory.search.assert_called_once_with("What is machine learning?", top_k=5)


@pytest.mark.asyncio
async def test_load_context_populates_semantic_memories(engine_with_semantic):
    """_load_context puts search results into ctx.semantic_memories."""
    ctx = await engine_with_semantic._load_context(
        raw_input="How does neural networks work?",
        user_id=None,
        session_id=None,
    )
    assert len(ctx.semantic_memories) == 2
    assert ctx.semantic_memories[0]["content"] == "Past knowledge about AI"


@pytest.mark.asyncio
async def test_load_context_semantic_search_failure_graceful():
    """If semantic memory search fails, context still loads."""
    sm = AsyncMock()
    sm.search = AsyncMock(side_effect=Exception("Search failed"))

    engine = CognitiveEngine(
        goal_manager=AsyncMock(list_goals=AsyncMock(return_value=[])),
        task_manager=AsyncMock(list_tasks=AsyncMock(return_value=[])),
        agent_manager=MagicMock(list_runtime_agents=MagicMock(return_value=[])),
        profile_memory=AsyncMock(get_profile=AsyncMock(return_value=None)),
        conversation_memory=AsyncMock(get_history=AsyncMock(return_value=[])),
        semantic_memory=sm,
    )

    ctx = await engine._load_context(
        raw_input="Test query",
        user_id=None,
        session_id=None,
    )
    # Should still get a valid context, just empty semantic_memories
    assert ctx.semantic_memories == []


@pytest.mark.asyncio
async def test_load_context_no_semantic_memory():
    """When semantic_memory is None, semantic_memories stays empty."""
    engine = CognitiveEngine(
        goal_manager=AsyncMock(list_goals=AsyncMock(return_value=[])),
        task_manager=AsyncMock(list_tasks=AsyncMock(return_value=[])),
        agent_manager=MagicMock(list_runtime_agents=MagicMock(return_value=[])),
        profile_memory=AsyncMock(get_profile=AsyncMock(return_value=None)),
        conversation_memory=AsyncMock(get_history=AsyncMock(return_value=[])),
        semantic_memory=None,
    )

    ctx = await engine._load_context(
        raw_input="Test query",
        user_id=None,
        session_id=None,
    )
    assert ctx.semantic_memories == []


@pytest.mark.asyncio
async def test_context_to_dict_includes_semantic_memories_count(engine_with_semantic):
    """CognitiveContext.to_dict includes semantic_memories_count."""
    ctx = await engine_with_semantic._load_context(
        raw_input="Test",
        user_id=None,
        session_id=None,
    )
    d = ctx.to_dict()
    assert "semantic_memories_count" in d
    assert d["semantic_memories_count"] == 2
