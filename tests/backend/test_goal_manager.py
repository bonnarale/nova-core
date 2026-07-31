"""Tests for GoalManager — the goal management service.

Covers:
- CRUD operations (create, get, list, update, delete)
- analyze_progress() analytics
- get_next_actions() and get_blocked_goals()
- GoalProvider abstract interface
- Edge cases (None database, missing goals, etc.)
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.memory.goals import GoalManager, GoalProvider

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fake goal object (simulates SQLAlchemy model)
# ---------------------------------------------------------------------------


class FakeGoal:
    """Simulates a Goal SQLAlchemy model instance."""

    def __init__(
        self,
        id: UUID | None = None,
        user_id: UUID | None = None,
        title: str = "Test Goal",
        description: str | None = None,
        status: str = "active",
        priority: int = 3,
        progress: int = 0,
        block_reason: str | None = None,
    ):
        self.id = id or uuid4()
        self.user_id = user_id or uuid4()
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.progress = progress
        self.block_reason = block_reason
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_repo():
    """Mock GoalRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def manager(mock_repo):
    """GoalManager with mocked repository."""
    m = GoalManager(database=MagicMock())
    m._repo = mock_repo
    return m


@pytest.fixture
def sample_goal():
    return FakeGoal(
        title="Learn Python",
        description="Complete the tutorial",
        status="active",
        priority=5,
        progress=40,
    )


# ---------------------------------------------------------------------------
# Interface tests
# ---------------------------------------------------------------------------


class TestGoalProviderInterface:
    def test_implements_abc(self):
        assert issubclass(GoalManager, GoalProvider)

    def test_has_all_abstract_methods(self):
        abstracts = GoalProvider.__abstractmethods__
        expected = {
            "create_goal", "get_goal", "list_goals",
            "update_goal", "delete_goal", "get_next_actions",
            "get_blocked_goals", "analyze_progress",
        }
        assert expected == abstracts


# ---------------------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------------------


class TestInit:
    def test_none_database_creates_no_repo(self):
        m = GoalManager(database=None)
        assert m._repo is None

    def test_valid_database_creates_repo(self):
        mock_db = MagicMock()
        m = GoalManager(database=mock_db)
        assert m._repo is not None


# ---------------------------------------------------------------------------
# create_goal()
# ---------------------------------------------------------------------------


class TestCreateGoal:
    async def test_create_goal(self, manager, mock_repo, sample_goal):
        user_id = uuid4()
        mock_repo.create.return_value = sample_goal
        result = await manager.create_goal(user_id, "Learn Python", "Complete tutorial", 5)

        assert result["title"] == "Learn Python"
        assert result["status"] == "active"
        assert result["priority"] == 5
        mock_repo.create.assert_awaited_once_with(user_id, "Learn Python", "Complete tutorial", 5)

    async def test_create_goal_returns_dict(self, manager, mock_repo, sample_goal):
        mock_repo.create.return_value = sample_goal
        result = await manager.create_goal(uuid4(), "test")
        assert isinstance(result, dict)
        assert "id" in result
        assert "created_at" in result


# ---------------------------------------------------------------------------
# get_goal()
# ---------------------------------------------------------------------------


class TestGetGoal:
    async def test_get_goal_found(self, manager, mock_repo, sample_goal):
        mock_repo.get.return_value = sample_goal
        result = await manager.get_goal(sample_goal.id)

        assert result is not None
        assert result["title"] == "Learn Python"
        assert result["progress"] == 40

    async def test_get_goal_not_found(self, manager, mock_repo):
        mock_repo.get.return_value = None
        result = await manager.get_goal(uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list_goals()
# ---------------------------------------------------------------------------


class TestListGoals:
    async def test_list_goals(self, manager, mock_repo, sample_goal):
        mock_repo.list_by_user.return_value = [sample_goal]
        result = await manager.list_goals(uuid4())

        assert len(result) == 1
        assert result[0]["title"] == "Learn Python"

    async def test_list_goals_empty(self, manager, mock_repo):
        mock_repo.list_by_user.return_value = []
        result = await manager.list_goals(uuid4())
        assert result == []

    async def test_list_goals_with_status_filter(self, manager, mock_repo):
        mock_repo.list_by_user.return_value = []
        await manager.list_goals(uuid4(), status="completed")
        mock_repo.list_by_user.assert_awaited_once()


# ---------------------------------------------------------------------------
# update_goal()
# ---------------------------------------------------------------------------


class TestUpdateGoal:
    async def test_update_goal(self, manager, mock_repo, sample_goal):
        mock_repo.update.return_value = sample_goal
        result = await manager.update_goal(
            sample_goal.id,
            title="Updated Title",
            status="completed",
            progress=100,
        )

        assert result is not None
        mock_repo.update.assert_awaited_once()

    async def test_update_goal_not_found(self, manager, mock_repo):
        mock_repo.update.return_value = None
        result = await manager.update_goal(uuid4(), title="x")
        assert result is None


# ---------------------------------------------------------------------------
# delete_goal()
# ---------------------------------------------------------------------------


class TestDeleteGoal:
    async def test_delete_goal_success(self, manager, mock_repo):
        mock_repo.delete.return_value = True
        result = await manager.delete_goal(uuid4())
        assert result is True

    async def test_delete_goal_not_found(self, manager, mock_repo):
        mock_repo.delete.return_value = False
        result = await manager.delete_goal(uuid4())
        assert result is False


# ---------------------------------------------------------------------------
# get_next_actions()
# ---------------------------------------------------------------------------


class TestGetNextActions:
    async def test_get_next_actions(self, manager, mock_repo, sample_goal):
        mock_repo.get_next_actions.return_value = [sample_goal]
        result = await manager.get_next_actions(uuid4())

        assert len(result) == 1
        assert result[0]["title"] == "Learn Python"

    async def test_get_next_actions_empty(self, manager, mock_repo):
        mock_repo.get_next_actions.return_value = []
        result = await manager.get_next_actions(uuid4())
        assert result == []


# ---------------------------------------------------------------------------
# get_blocked_goals()
# ---------------------------------------------------------------------------


class TestGetBlockedGoals:
    async def test_get_blocked_goals(self, manager, mock_repo):
        blocked = FakeGoal(title="Blocked Task", status="blocked", block_reason="Missing API key")
        mock_repo.get_blocked.return_value = [blocked]
        result = await manager.get_blocked_goals(uuid4())

        assert len(result) == 1
        assert result[0]["status"] == "blocked"
        assert result[0]["block_reason"] == "Missing API key"


# ---------------------------------------------------------------------------
# analyze_progress()
# ---------------------------------------------------------------------------


class TestAnalyzeProgress:
    async def test_analyze_progress_mixed(self, manager, mock_repo):
        goals = [
            FakeGoal(status="active", progress=30),
            FakeGoal(status="active", progress=70),
            FakeGoal(status="completed", progress=100),
            FakeGoal(status="blocked", progress=50),
            FakeGoal(status="abandoned", progress=10),
        ]
        mock_repo.list_by_user.return_value = goals
        mock_repo.get_next_actions.return_value = []

        result = await manager.analyze_progress(uuid4())

        assert result["total"] == 5
        assert result["active"] == 2
        assert result["completed"] == 1
        assert result["blocked"] == 1
        assert result["abandoned"] == 1
        assert result["avg_progress"] == 52.0

    async def test_analyze_progress_empty(self, manager, mock_repo):
        mock_repo.list_by_user.return_value = []
        mock_repo.get_next_actions.return_value = []

        result = await manager.analyze_progress(uuid4())

        assert result["total"] == 0
        assert result["avg_progress"] == 0.0

    async def test_analyze_progress_includes_next_actions(self, manager, mock_repo):
        next_goal = FakeGoal(title="Next Step")
        mock_repo.list_by_user.return_value = [FakeGoal()]
        mock_repo.get_next_actions.return_value = [next_goal]

        result = await manager.analyze_progress(uuid4())
        assert len(result["next_actions"]) == 1


# ---------------------------------------------------------------------------
# _to_dict() helper
# ---------------------------------------------------------------------------


class TestToDict:
    def test_to_dict_none(self, manager):
        assert manager._to_dict(None) is None

    def test_to_dict_full_goal(self, manager, sample_goal):
        d = manager._to_dict(sample_goal)
        assert d is not None
        assert d["title"] == "Learn Python"
        assert d["description"] == "Complete the tutorial"
        assert d["status"] == "active"
        assert d["priority"] == 5
        assert d["progress"] == 40
        assert d["block_reason"] is None
        assert "id" in d
        assert "created_at" in d
        assert "updated_at" in d

    def test_to_dict_blocked_goal(self, manager):
        g = FakeGoal(block_reason="Needs approval")
        d = manager._to_dict(g)
        assert d["block_reason"] == "Needs approval"
