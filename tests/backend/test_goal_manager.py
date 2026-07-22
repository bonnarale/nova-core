"""Tests for GoalManager service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.memory.goals import GoalManager


class TestGoalManager:
    @pytest.fixture
    def mock_database(self):
        db = MagicMock()
        db.session_factory = MagicMock()
        return db

    @pytest.fixture
    def manager(self, mock_database):
        mgr = GoalManager(mock_database)
        mgr._repo = MagicMock()
        mgr._repo.create = AsyncMock()
        mgr._repo.get = AsyncMock()
        mgr._repo.list_by_user = AsyncMock()
        mgr._repo.update = AsyncMock()
        mgr._repo.delete = AsyncMock()
        mgr._repo.get_next_actions = AsyncMock()
        mgr._repo.get_blocked = AsyncMock()
        return mgr

    def _make_goal_mock(self, **overrides):
        goal = MagicMock()
        goal.id = overrides.get("id", "00000000-0000-0000-0000-000000000010")
        goal.user_id = overrides.get("user_id", "00000000-0000-0000-0000-000000000001")
        goal.title = overrides.get("title", "Test goal")
        goal.description = overrides.get("description", None)
        goal.status = overrides.get("status", "active")
        goal.priority = overrides.get("priority", 3)
        goal.progress = overrides.get("progress", 0)
        goal.block_reason = overrides.get("block_reason", None)
        goal.created_at = None
        goal.updated_at = None
        return goal

    @pytest.mark.asyncio
    async def test_create_goal(self, manager):
        goal_mock = self._make_goal_mock(title="Build AI")
        manager._repo.create.return_value = goal_mock

        uid = "00000000-0000-0000-0000-000000000001"
        result = await manager.create_goal(uid, "Build AI", priority=5)

        manager._repo.create.assert_awaited_once_with(uid, "Build AI", None, 5)
        assert result["title"] == "Build AI"
        assert result["priority"] == 3  # from mock

    @pytest.mark.asyncio
    async def test_get_goal_found(self, manager):
        goal_mock = self._make_goal_mock(title="Test")
        manager._repo.get.return_value = goal_mock

        gid = "00000000-0000-0000-0000-000000000010"
        result = await manager.get_goal(gid)

        assert result["title"] == "Test"

    @pytest.mark.asyncio
    async def test_get_goal_not_found(self, manager):
        manager._repo.get.return_value = None

        result = await manager.get_goal("00000000-0000-0000-0000-000000000010")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_goals(self, manager):
        goal_a = self._make_goal_mock(title="Goal A")
        goal_b = self._make_goal_mock(title="Goal B")
        manager._repo.list_by_user.return_value = [goal_a, goal_b]

        uid = "00000000-0000-0000-0000-000000000001"
        result = await manager.list_goals(uid)

        assert len(result) == 2
        assert result[0]["title"] == "Goal A"

    @pytest.mark.asyncio
    async def test_update_goal(self, manager):
        goal_mock = self._make_goal_mock(title="Old")
        manager._repo.update.return_value = goal_mock

        gid = "00000000-0000-0000-0000-000000000010"
        result = await manager.update_goal(gid, title="New", progress=50)

        manager._repo.update.assert_awaited_once_with(gid, "New", None, None, None, 50, None)
        assert result["title"] == "Old"  # from mock

    @pytest.mark.asyncio
    async def test_update_goal_blocked(self, manager):
        goal_mock = self._make_goal_mock(title="Stuck", status="blocked", block_reason="Need help")
        manager._repo.update.return_value = goal_mock

        gid = "00000000-0000-0000-0000-000000000010"
        result = await manager.update_goal(gid, status="blocked", block_reason="Need help")

        assert result["status"] == "blocked"
        assert result["block_reason"] == "Need help"

    @pytest.mark.asyncio
    async def test_delete_goal(self, manager):
        manager._repo.delete.return_value = True

        gid = "00000000-0000-0000-0000-000000000010"
        result = await manager.delete_goal(gid)

        assert result is True

    @pytest.mark.asyncio
    async def test_get_next_actions(self, manager):
        goal_mock = self._make_goal_mock(title="Priority")
        manager._repo.get_next_actions.return_value = [goal_mock]

        uid = "00000000-0000-0000-0000-000000000001"
        result = await manager.get_next_actions(uid, limit=3)

        assert len(result) == 1
        assert result[0]["title"] == "Priority"

    @pytest.mark.asyncio
    async def test_get_blocked_goals(self, manager):
        goal_mock = self._make_goal_mock(title="Blocked", status="blocked")
        manager._repo.get_blocked.return_value = [goal_mock]

        uid = "00000000-0000-0000-0000-000000000001"
        result = await manager.get_blocked_goals(uid)

        assert len(result) == 1
        assert result[0]["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_analyze_progress(self, manager):
        goal_a = self._make_goal_mock(title="A", status="active", progress=50)
        goal_b = self._make_goal_mock(title="B", status="completed", progress=100)
        goal_c = self._make_goal_mock(title="C", status="blocked", progress=30)
        manager._repo.list_by_user.return_value = [goal_a, goal_b, goal_c]
        manager._repo.get_next_actions.return_value = [goal_a]

        uid = "00000000-0000-0000-0000-000000000001"
        result = await manager.analyze_progress(uid)

        assert result["total"] == 3
        assert result["active"] == 1
        assert result["blocked"] == 1
        assert result["completed"] == 1
        assert result["abandoned"] == 0
        assert result["avg_progress"] == 60.0
        assert len(result["next_actions"]) == 1

    @pytest.mark.asyncio
    async def test_analyze_progress_empty(self, manager):
        manager._repo.list_by_user.return_value = []
        manager._repo.get_next_actions.return_value = []

        uid = "00000000-0000-0000-0000-000000000001"
        result = await manager.analyze_progress(uid)

        assert result["total"] == 0
        assert result["avg_progress"] == 0.0
        assert result["next_actions"] == []

    @pytest.mark.asyncio
    async def test_update_goal_not_found(self, manager):
        manager._repo.update.return_value = None

        gid = "00000000-0000-0000-0000-000000000010"
        result = await manager.update_goal(gid, title="New")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_goal_not_found(self, manager):
        manager._repo.delete.return_value = False

        gid = "00000000-0000-0000-0000-000000000010"
        result = await manager.delete_goal(gid)

        assert result is False

    @pytest.mark.asyncio
    async def test_to_dict_none(self, manager):
        result = manager._to_dict(None)
        assert result is None
