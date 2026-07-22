"""Tests for TaskManager."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestrator.task_manager import TaskManager


class TestTaskManager:
    @pytest.fixture
    def mock_database(self):
        db = MagicMock()
        db.session_factory = MagicMock()
        return db

    @pytest.fixture
    def mock_event_bus(self):
        bus = MagicMock()
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def manager(self, mock_database, mock_event_bus):
        mgr = TaskManager(mock_database, mock_event_bus)
        mgr._repo = MagicMock()
        mgr._repo.create = AsyncMock()
        mgr._repo.get = AsyncMock()
        mgr._repo.list = AsyncMock()
        mgr._repo.update = AsyncMock()
        mgr._repo.delete = AsyncMock()
        mgr.planner._repo = mgr._repo
        mgr.worker._repo = mgr._repo
        return mgr

    def _make_task_mock(self, **overrides):
        import datetime
        t = MagicMock()
        t.id = overrides.get("id", "00000000-0000-0000-0000-000000000010")
        t.goal = overrides.get("goal", "Test")
        t.status = overrides.get("status", "CREATED")
        t.plan = overrides.get("plan", {})
        t.steps = overrides.get("steps", [])
        t.current_step = overrides.get("current_step", 0)
        t.dependencies = overrides.get("dependencies", [])
        t.artifacts = overrides.get("artifacts", {})
        t.events = overrides.get("events", [])
        t.assigned_agent = overrides.get("assigned_agent", None)
        t.created_at = datetime.datetime.now(tz=datetime.timezone.utc)
        t.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
        t.started_at = overrides.get("started_at", None)
        t.completed_at = overrides.get("completed_at", None)
        return t

    @pytest.mark.asyncio
    async def test_create_task(self, manager):
        task = self._make_task_mock(goal="Build AI")
        manager._repo.create.return_value = task

        result = await manager.create_task("Build AI", steps=["learn", "build"])

        assert result["goal"] == "Build AI"
        manager._repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_task_found(self, manager):
        task = self._make_task_mock(goal="Test")
        manager._repo.get.return_value = task

        result = await manager.get_task("00000000-0000-0000-0000-000000000010")
        assert result["goal"] == "Test"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, manager):
        manager._repo.get.return_value = None

        result = await manager.get_task("00000000-0000-0000-0000-000000000010")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_tasks(self, manager):
        manager._repo.list.return_value = [self._make_task_mock(goal="A")]

        result = await manager.list_tasks()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_delete_task(self, manager):
        manager._repo.delete.return_value = True

        result = await manager.delete_task("00000000-0000-0000-0000-000000000010")
        assert result is True

    @pytest.mark.asyncio
    async def test_transition_task(self, manager):
        task = self._make_task_mock(status="CREATED")

        async def _update_side_effect(task_id, **kw):
            for k, v in kw.items():
                setattr(task, k, v)
            return task

        manager._repo.get.return_value = task
        manager._repo.update.side_effect = _update_side_effect

        result = await manager.transition_task("00000000-0000-0000-0000-000000000010", "QUEUED")
        assert result["status"] == "QUEUED"

    @pytest.mark.asyncio
    async def test_event_bus_property(self, manager, mock_event_bus):
        assert manager.event_bus is mock_event_bus

    @pytest.mark.asyncio
    async def test_to_dict_none_handled(self, manager):
        assert manager._to_dict(self._make_task_mock()) is not None
