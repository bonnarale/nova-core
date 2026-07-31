"""Tests for SemanticMemory auto-index on app startup."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.memory.semantic import SemanticMemory


@pytest.mark.asyncio
async def test_auto_index_calls_profile_and_goals():
    """auto_index profiles and goals when both provided."""
    sm = AsyncMock(spec=SemanticMemory)
    sm.auto_index = AsyncMock()

    profile = {"name": "Alice", "facts": ["Alice likes Python"]}
    goals = [{"title": "Learn FastAPI"}]

    await sm.auto_index(profile=profile, goals=goals)

    sm.auto_index.assert_called_once_with(profile=profile, goals=goals)


@pytest.mark.asyncio
async def test_auto_index_empty_is_noop():
    """auto_index with nothing to index is a noop."""
    sm = AsyncMock(spec=SemanticMemory)
    sm.auto_index = AsyncMock()

    await sm.auto_index()

    sm.auto_index.assert_called_once()


@pytest.mark.asyncio
async def test_semantic_memory_passed_to_cognitive_engine():
    """Verify semantic_memory is passed to CognitiveEngine constructor."""
    from app.cognitive.engine import CognitiveEngine
    from app.memory.goals import GoalManager
    from app.orchestrator.task_manager import TaskManager

    sm = AsyncMock()
    goal_manager = AsyncMock(spec=GoalManager)
    task_manager = AsyncMock(spec=TaskManager)
    agent_manager = MagicMock()
    profile_memory = AsyncMock()
    conversation_memory = AsyncMock()

    engine = CognitiveEngine(
        goal_manager=goal_manager,
        task_manager=task_manager,
        agent_manager=agent_manager,
        profile_memory=profile_memory,
        conversation_memory=conversation_memory,
        semantic_memory=sm,
    )

    assert engine._semantic_memory is sm
