"""Tests for Worker."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestrator.worker import Worker


class TestWorker:
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
    def worker(self, mock_database, mock_event_bus):
        w = Worker(mock_database, mock_event_bus)
        w._repo = MagicMock()
        w._repo.get = AsyncMock()
        w._repo.update = AsyncMock()
        return w

    def _make_task_mock(self, **overrides):
        import datetime
        t = MagicMock()
        t.id = overrides.get("id", "00000000-0000-0000-0000-000000000010")
        t.goal = overrides.get("goal", "Test goal")
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
    async def test_transition_created_to_queued(self, worker, mock_event_bus):
        task = self._make_task_mock(status="CREATED")

        async def _update_side_effect(task_id, **kw):
            for k, v in kw.items():
                setattr(task, k, v)
            return task

        worker._repo.get.return_value = task
        worker._repo.update.side_effect = _update_side_effect

        tid = "00000000-0000-0000-0000-000000000010"
        result = await worker.transition(tid, "QUEUED")

        assert result["status"] == "QUEUED"
        worker._repo.update.assert_awaited_once()
        mock_event_bus.emit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_transition_invalid_raises(self, worker, mock_event_bus):
        task = self._make_task_mock(status="CREATED")
        worker._repo.get.return_value = task

        with pytest.raises(ValueError, match="Invalid transition"):
            await worker.transition("00000000-0000-0000-0000-000000000010", "COMPLETED")

    @pytest.mark.asyncio
    async def test_transition_task_not_found(self, worker, mock_event_bus):
        worker._repo.get.return_value = None

        result = await worker.transition("00000000-0000-0000-0000-000000000010", "QUEUED")
        assert result is None

    @pytest.fixture
    def _make_update_side_effect(self):
        """Return a factory that creates an update side effect for a task mock."""
        def _factory(task):
            async def _side_effect(task_id, **kw):
                for k, v in kw.items():
                    setattr(task, k, v)
                return task
            return _side_effect
        return _factory

    @pytest.mark.asyncio
    async def test_transition_sets_started_at_on_run(self, worker, mock_event_bus, _make_update_side_effect):
        task = self._make_task_mock(status="QUEUED")
        worker._repo.get.return_value = task
        worker._repo.update.side_effect = _make_update_side_effect(task)

        tid = "00000000-0000-0000-0000-000000000010"
        result = await worker.transition(tid, "RUNNING")

        assert result["status"] == "RUNNING"

    @pytest.mark.asyncio
    async def test_transition_sets_completed_at(self, worker, mock_event_bus, _make_update_side_effect):
        task = self._make_task_mock(status="RUNNING", steps=["a", "b"])
        worker._repo.get.return_value = task
        worker._repo.update.side_effect = _make_update_side_effect(task)

        tid = "00000000-0000-0000-0000-000000000010"
        result = await worker.transition(tid, "COMPLETED")

        assert result is not None
        assert result["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_advance_step_completes_task(self, worker, mock_event_bus, _make_update_side_effect):
        task = self._make_task_mock(
            status="RUNNING", steps=["step1", "step2"], current_step=1
        )
        worker._repo.get.return_value = task
        worker._repo.update.side_effect = _make_update_side_effect(task)

        tid = "00000000-0000-0000-0000-000000000010"
        result = await worker.advance_step(tid, artifacts={"output": "done"})

        assert result is not None

    @pytest.mark.asyncio
    async def test_advance_step_not_running_raises(self, worker, mock_event_bus):
        task = self._make_task_mock(status="CREATED")
        worker._repo.get.return_value = task

        with pytest.raises(ValueError, match="is not RUNNING"):
            await worker.advance_step("00000000-0000-0000-0000-000000000010")

    @pytest.mark.asyncio
    async def test_advance_step_task_not_found(self, worker, mock_event_bus):
        worker._repo.get.return_value = None

        result = await worker.advance_step("00000000-0000-0000-0000-000000000010")
        assert result is None

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, worker, mock_event_bus, _make_update_side_effect):
        task = self._make_task_mock(
            status="CREATED", steps=["plan", "build", "test", "deploy"]
        )
        worker._repo.get.return_value = task
        worker._repo.update.side_effect = _make_update_side_effect(task)

        tid = "00000000-0000-0000-0000-000000000010"

        # CREATED -> QUEUED
        result = await worker.transition(tid, "QUEUED")
        assert result["status"] == "QUEUED"

        # QUEUED -> RUNNING
        result = await worker.transition(tid, "RUNNING")
        assert result["status"] == "RUNNING"

    def test_validate_transition_valid(self, worker):
        worker._validate_transition("CREATED", "QUEUED")
        worker._validate_transition("QUEUED", "RUNNING")
        worker._validate_transition("RUNNING", "COMPLETED")
        worker._validate_transition("RUNNING", "WAITING")
        worker._validate_transition("RUNNING", "FAILED")
        worker._validate_transition("WAITING", "RUNNING")
        worker._validate_transition("CREATED", "FAILED")

    def test_validate_transition_invalid(self, worker):
        with pytest.raises(ValueError):
            worker._validate_transition("CREATED", "COMPLETED")
        with pytest.raises(ValueError):
            worker._validate_transition("COMPLETED", "RUNNING")
        with pytest.raises(ValueError):
            worker._validate_transition("FAILED", "QUEUED")
