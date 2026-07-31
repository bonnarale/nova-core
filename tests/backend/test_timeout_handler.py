"""Tests for TimeoutHandler — timeout detection on state transitions."""

import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.events.schemas import Event


def _make_task_mock(**overrides):
    """Create a mock task object."""
    t = MagicMock()
    t.id = overrides.get("id", uuid4())
    t.goal = overrides.get("goal", "Test goal")
    t.status = overrides.get("status", "RUNNING")
    t.events = overrides.get("events", [])
    t.started_at = overrides.get("started_at", None)
    t.dependencies = overrides.get("dependencies", [])
    t.created_at = datetime.datetime.now(tz=datetime.timezone.utc)
    t.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    return t


class TestTimeoutHandler:
    """Tests for TimeoutHandler."""

    @pytest.fixture
    def mock_repo(self):
        """Mock TaskRepository."""
        repo = AsyncMock()
        repo.get = AsyncMock()
        repo.update = AsyncMock()
        return repo

    @pytest.fixture
    def mock_bus(self):
        """Mock InMemoryEventBus."""
        bus = AsyncMock()
        bus.subscribe = AsyncMock(return_value="sub-timeout")
        bus.publish = AsyncMock()
        return bus

    @pytest.fixture
    def handler(self, mock_bus, mock_repo):
        """Create TimeoutHandler with mocked dependencies."""
        from app.orchestrator.timeout_handler import TimeoutHandler
        return TimeoutHandler(mock_bus, mock_repo, default_timeout=300)

    @pytest.mark.asyncio
    async def test_subscribe_registers_listeners(self, handler, mock_bus):
        """subscribe_to should register for started, running, step_advanced, retrying events."""
        await handler.subscribe_to()

        calls = mock_bus.subscribe.call_args_list
        subscribed_events = [c[0][0] for c in calls]
        assert "task.started" in subscribed_events
        assert "task.running" in subscribed_events
        assert "task.step_advanced" in subscribed_events
        assert "task.retrying" in subscribed_events

    @pytest.mark.asyncio
    async def test_task_within_timeout_continues(self, handler, mock_repo, mock_bus):
        """Task within timeout should not be marked FAILED."""
        task_id = uuid4()
        started = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(seconds=100)
        task = _make_task_mock(id=task_id, status="RUNNING", started_at=started)
        mock_repo.get.return_value = task

        event = Event(
            event_type="task.started",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        await handler.check_timeout(event)

        # Should NOT mark as FAILED
        mock_repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_task_exceeding_timeout_fails(self, handler, mock_repo, mock_bus):
        """Task exceeding timeout should be marked FAILED."""
        task_id = uuid4()
        # Started 400 seconds ago, timeout is 300s
        started = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(seconds=400)
        task = _make_task_mock(id=task_id, status="RUNNING", started_at=started)
        mock_repo.get.return_value = task

        event = Event(
            event_type="task.started",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        await handler.check_timeout(event)

        # Should mark as FAILED
        mock_repo.update.assert_awaited_once()
        call_kwargs = mock_repo.update.call_args[1]
        assert call_kwargs["status"] == "FAILED"

    @pytest.mark.asyncio
    async def test_timeout_emits_event(self, handler, mock_repo, mock_bus):
        """When timeout exceeded, should emit task.timeout event."""
        task_id = uuid4()
        started = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(seconds=400)
        task = _make_task_mock(id=task_id, status="RUNNING", started_at=started)
        mock_repo.get.return_value = task

        event = Event(
            event_type="task.started",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        await handler.check_timeout(event)

        # Should publish timeout event
        publish_calls = [c[0][0] for c in mock_bus.publish.call_args_list]
        timeout_events = [e for e in publish_calls if e.event_type == "task.timeout"]
        assert len(timeout_events) == 1

        payload = timeout_events[0].payload
        assert "timeout_seconds" in payload
        assert "actual_duration" in payload
        assert "triggering_transition" in payload

    @pytest.mark.asyncio
    async def test_non_running_task_skipped(self, handler, mock_repo, mock_bus):
        """Non-RUNNING tasks should not be checked for timeout."""
        task_id = uuid4()
        task = _make_task_mock(id=task_id, status="CREATED")
        mock_repo.get.return_value = task

        event = Event(
            event_type="task.started",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        await handler.check_timeout(event)
        mock_repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_task_without_started_at_skipped(self, handler, mock_repo, mock_bus):
        """Task with no started_at should be skipped."""
        task_id = uuid4()
        task = _make_task_mock(id=task_id, status="RUNNING", started_at=None)
        mock_repo.get.return_value = task

        event = Event(
            event_type="task.started",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        await handler.check_timeout(event)
        mock_repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_per_task_timeout_override(self, handler, mock_repo, mock_bus):
        """Per-task timeout_seconds should override default."""
        task_id = uuid4()
        # Started 400s ago, but per-task timeout is 500s — should NOT fail
        started = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(seconds=400)
        task = _make_task_mock(
            id=task_id,
            status="RUNNING",
            started_at=started,
            events=[{"timeout_seconds": 500}],
        )
        mock_repo.get.return_value = task

        event = Event(
            event_type="task.started",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        await handler.check_timeout(event)
        mock_repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_task_id_ignored(self, handler, mock_repo, mock_bus):
        """Events without aggregate_id should be silently ignored."""
        event = Event(
            event_type="task.started",
            aggregate_id="",
            payload={},
        )

        await handler.check_timeout(event)
        mock_repo.get.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_task_not_found_ignored(self, handler, mock_repo, mock_bus):
        """Tasks not found in repo should be silently ignored."""
        mock_repo.get.return_value = None
        event = Event(
            event_type="task.started",
            aggregate_id=str(uuid4()),
            payload={"task_id": str(uuid4())},
        )

        await handler.check_timeout(event)
        mock_repo.update.assert_not_awaited()

    def test_default_timeout_from_env(self, mock_bus, mock_repo):
        """Default timeout should be configurable via env var."""
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"NOVA_TASK_TIMEOUT_SECONDS": "600"}):
            from app.orchestrator.timeout_handler import TimeoutHandler
            h = TimeoutHandler(mock_bus, mock_repo)
            assert h._default_timeout == 600

    @pytest.mark.asyncio
    async def test_timeout_event_payload_fields(self, handler, mock_repo, mock_bus):
        """Timeout event should include all required payload fields."""
        task_id = uuid4()
        started = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(seconds=400)
        task = _make_task_mock(id=task_id, status="RUNNING", started_at=started)
        mock_repo.get.return_value = task

        event = Event(
            event_type="task.step_advanced",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        await handler.check_timeout(event)

        timeout_event = mock_bus.publish.call_args[0][0]
        assert timeout_event.payload["task_id"] == str(task_id)
        assert timeout_event.payload["timeout_seconds"] == 300
        assert timeout_event.payload["actual_duration"] > 300
        assert timeout_event.payload["triggering_transition"] == "task.step_advanced"
