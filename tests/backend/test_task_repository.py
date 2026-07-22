"""Tests for TaskRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.task_repository import TaskRepository


class TestTaskRepository:
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
        return TaskRepository(mock_session_factory)

    @pytest.mark.asyncio
    async def test_create(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value

        result = await repo.create(
            goal="Build a website",
            plan={"key": "value"},
            steps=["design", "code", "deploy"],
            dependencies=[],
            assigned_agent="assistant",
        )

        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        added = session.add.call_args[0][0]
        assert added.goal == "Build a website"
        assert added.plan == {"key": "value"}
        assert added.steps == ["design", "code", "deploy"]
        assert added.status == "CREATED"

    @pytest.mark.asyncio
    async def test_get_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        task = MagicMock()
        session.get.return_value = task

        result = await repo.get("00000000-0000-0000-0000-000000000001")
        assert result is task

    @pytest.mark.asyncio
    async def test_get_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get.return_value = None

        result = await repo.get("00000000-0000-0000-0000-000000000001")
        assert result is None

    @pytest.mark.asyncio
    async def test_list(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]
        session.execute.return_value = result_mock

        result = await repo.list()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute.return_value = result_mock

        result = await repo.list(status="RUNNING")
        assert result == []

    @pytest.mark.asyncio
    async def test_list_invalid_status(self, repo, mock_session_factory):
        with pytest.raises(ValueError, match="Invalid status"):
            await repo.list(status="INVALID")

    @pytest.mark.asyncio
    async def test_update(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        task = MagicMock()
        task.status = "CREATED"
        task.steps = []
        session.get.return_value = task

        tid = "00000000-0000-0000-0000-000000000001"
        result = await repo.update(tid, status="QUEUED")

        assert task.status == "QUEUED"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get.return_value = None

        tid = "00000000-0000-0000-0000-000000000001"
        result = await repo.update(tid, status="QUEUED")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        task = MagicMock()
        session.get.return_value = task

        tid = "00000000-0000-0000-0000-000000000001"
        result = await repo.delete(tid)

        assert result is True
        session.delete.assert_called_once_with(task)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get.return_value = None

        tid = "00000000-0000-0000-0000-000000000001"
        result = await repo.delete(tid)
        assert result is False

    @pytest.mark.asyncio
    async def test_add_event(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        task = MagicMock()
        task.events = []
        session.get.return_value = task

        tid = "00000000-0000-0000-0000-000000000001"
        event = {"type": "test", "timestamp": "now"}
        result = await repo.add_event(tid, event)

        assert task.events == [event]

    @pytest.mark.asyncio
    async def test_add_event_not_found(self, repo, mock_session_factory):
        session = mock_session_factory.return_value.__aenter__.return_value
        session.get.return_value = None

        tid = "00000000-0000-0000-0000-000000000001"
        result = await repo.add_event(tid, {"type": "test"})
        assert result is None
