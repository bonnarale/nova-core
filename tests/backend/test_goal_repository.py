"""Tests for GoalRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.goal_repository import GoalRepository


class TestGoalRepository:
    @pytest.fixture
    def mock_session_factory(self):
        factory = MagicMock()
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.get = AsyncMock()
        session.delete = AsyncMock()
        cm = MagicMock()
        cm.__aenter__.return_value = session
        cm.__aexit__.return_value = None
        factory.return_value = cm
        return factory

    @pytest.fixture
    def repo(self, mock_session_factory):
        return GoalRepository(mock_session_factory)

    @pytest.mark.asyncio
    async def test_create(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        uid = "00000000-0000-0000-0000-000000000001"

        result = await repo.create(uid, "Build Nova Core", description="The big one", priority=5)

        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        added = session.add.call_args[0][0]
        assert added.title == "Build Nova Core"
        assert added.description == "The big one"
        assert added.priority == 5
        assert added.status == "active"
        assert added.progress == 0

    @pytest.mark.asyncio
    async def test_get_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        goal = MagicMock()
        session.get.return_value = goal

        result = await repo.get("00000000-0000-0000-0000-000000000010")

        assert result is goal

    @pytest.mark.asyncio
    async def test_get_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get.return_value = None

        result = await repo.get("00000000-0000-0000-0000-000000000010")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_user(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        goal_a = MagicMock()
        goal_b = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [goal_a, goal_b]
        session.execute.return_value = result_mock

        uid = "00000000-0000-0000-0000-000000000001"
        result = await repo.list_by_user(uid)

        assert result == [goal_a, goal_b]

    @pytest.mark.asyncio
    async def test_list_by_user_with_status_filter(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute.return_value = result_mock

        uid = "00000000-0000-0000-0000-000000000001"
        result = await repo.list_by_user(uid, status="blocked")

        assert result == []

    @pytest.mark.asyncio
    async def test_update_full(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        goal = MagicMock()
        goal.title = "Old"
        goal.status = "active"
        session.get.return_value = goal

        gid = "00000000-0000-0000-0000-000000000010"
        result = await repo.update(gid, title="New", status="blocked", block_reason="stuck")

        assert goal.title == "New"
        assert goal.status == "blocked"
        assert goal.block_reason == "stuck"
        session.commit.assert_awaited_once()
        assert result is goal

    @pytest.mark.asyncio
    async def test_update_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get.return_value = None

        gid = "00000000-0000-0000-0000-000000000010"
        result = await repo.update(gid, title="New")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        goal = MagicMock()
        session.get.return_value = goal

        gid = "00000000-0000-0000-0000-000000000010"
        result = await repo.delete(gid)

        assert result is True
        session.delete.assert_called_once_with(goal)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get.return_value = None

        gid = "00000000-0000-0000-0000-000000000010"
        result = await repo.delete(gid)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_next_actions(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        goal = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [goal]
        session.execute.return_value = result_mock

        uid = "00000000-0000-0000-0000-000000000001"
        result = await repo.get_next_actions(uid, limit=3)

        assert result == [goal]

    @pytest.mark.asyncio
    async def test_get_blocked(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        goal = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [goal]
        session.execute.return_value = result_mock

        uid = "00000000-0000-0000-0000-000000000001"
        result = await repo.get_blocked(uid)

        assert result == [goal]
