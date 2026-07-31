"""Tests for ActivityLogRepository."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.activity_log_repository import ActivityLogRepository


class TestActivityLogRepository:
    """Tests for ActivityLogRepository."""

    @pytest.fixture
    def mock_session_factory(self):
        """Create a mock async_sessionmaker that yields a controlled session."""
        factory = MagicMock()
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        cm = MagicMock()
        cm.__aenter__.return_value = session
        cm.__aexit__.return_value = None
        factory.return_value = cm

        return factory

    @pytest.fixture
    def repo(self, mock_session_factory):
        return ActivityLogRepository(mock_session_factory)

    def test_init_stores_session_factory(self, mock_session_factory):
        repo = ActivityLogRepository(mock_session_factory)
        assert repo._session_factory is mock_session_factory

    @pytest.mark.asyncio
    async def test_create_adds_entry_and_commits(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        user_id = uuid4()

        entry = await repo.create(
            user_id=user_id,
            action="reviewed",
            status="executed",
            goal_title="Build API",
            goal_priority=3,
        )

        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        assert entry.user_id == user_id
        assert entry.action == "reviewed"
        assert entry.status == "executed"
        assert entry.goal_title == "Build API"
        assert entry.goal_priority == 3

    @pytest.mark.asyncio
    async def test_create_with_optional_fields(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        user_id = uuid4()
        goal_id = uuid4()

        entry = await repo.create(
            user_id=user_id,
            action="executed",
            status="executed",
            goal_id=goal_id,
            goal_title="Test Goal",
            goal_priority=1,
            approval_id="approval-123",
            reason="Approved by user",
            details={"key": "value"},
        )

        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        assert entry.goal_id == goal_id
        assert entry.approval_id == "approval-123"
        assert entry.reason == "Approved by user"
        assert entry.details == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        entry_id = uuid4()
        mock_entry = MagicMock()
        mock_entry.id = entry_id

        session.get = AsyncMock(return_value=mock_entry)

        result = await repo.get_by_id(entry_id)

        assert result is mock_entry
        session.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get = AsyncMock(return_value=None)

        result = await repo.get_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_list_recent_returns_ordered_entries(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        mock_entries = [MagicMock(), MagicMock(), MagicMock()]

        scalar_result = MagicMock()
        scalar_result.all.return_value = mock_entries
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalar_result
        session.execute.return_value = result_mock

        entries = await repo.list_recent(limit=3)

        assert entries == mock_entries
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_recent_default_limit(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        scalar_result = MagicMock()
        scalar_result.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalar_result
        session.execute.return_value = result_mock

        await repo.list_recent()

        executed_stmt = session.execute.call_args[0][0]
        assert executed_stmt._limit == 20

    @pytest.mark.asyncio
    async def test_list_recent_empty_database(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        scalar_result = MagicMock()
        scalar_result.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalar_result
        session.execute.return_value = result_mock

        entries = await repo.list_recent()

        assert entries == []

    @pytest.mark.asyncio
    async def test_list_by_user_filters_and_orders(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        user_id = uuid4()
        mock_entries = [MagicMock()]

        scalar_result = MagicMock()
        scalar_result.all.return_value = mock_entries
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalar_result
        session.execute.return_value = result_mock

        entries = await repo.list_by_user(user_id, limit=10)

        assert entries == mock_entries
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_by_goal_filters_and_orders(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        goal_id = uuid4()
        mock_entries = [MagicMock(), MagicMock()]

        scalar_result = MagicMock()
        scalar_result.all.return_value = mock_entries
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalar_result
        session.execute.return_value = result_mock

        entries = await repo.list_by_goal(goal_id, limit=5)

        assert entries == mock_entries
        session.execute.assert_awaited_once()
