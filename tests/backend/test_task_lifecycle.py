"""Integration tests for Phase 2 — full task lifecycle with handlers.

Tests the complete flow: create → fail → retry → complete, with dependency
gating and timeout detection. Uses mocked DB but real handler logic.
"""

import asyncio
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
    t.status = overrides.get("status", "CREATED")
    t.plan = overrides.get("plan", {})
    t.steps = overrides.get("steps", [])
    t.current_step = overrides.get("current_step", 0)
    t.events = overrides.get("events", [])
    t.dependencies = overrides.get("dependencies", [])
    t.artifacts = overrides.get("artifacts", {})
    t.assigned_agent = overrides.get("assigned_agent", None)
    t.started_at = overrides.get("started_at", None)
    t.created_at = datetime.datetime.now(tz=datetime.timezone.utc)
    t.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    return t


class TestRetryLifecycle:
    """Integration: create → fail → retry → complete flow."""

    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        repo.get = AsyncMock()
        repo.update = AsyncMock()
        repo.list = AsyncMock(return_value=[])
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock()
        bus.subscribe = AsyncMock(return_value="sub-1")
        bus.publish = AsyncMock()
        bus.publish_delayed = AsyncMock(return_value="delay-1")
        return bus

    @pytest.mark.asyncio
    async def test_fail_then_retry_flow(self, mock_bus, mock_repo):
        """Full retry flow: task fails, gets retried with backoff."""
        from app.orchestrator.retry_handler import RetryHandler

        task_id = uuid4()
        task = _make_task_mock(id=task_id, events=[], status="FAILED")
        mock_repo.get.return_value = task

        handler = RetryHandler(mock_bus, mock_repo, default_max_retries=3)

        # First failure — should retry
        event = Event(
            event_type="task.failed",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id), "failure_reason": "agent_error"},
        )
        await handler.handle_failure(event)

        # Verify: retry emitted, delayed requeue scheduled
        assert mock_bus.publish.await_count >= 1
        mock_bus.publish_delayed.assert_awaited_once()

        # Verify backoff is 30s for first retry
        delay_args = mock_bus.publish_delayed.call_args
        assert delay_args[0][1] == 30

    @pytest.mark.asyncio
    async def test_exhaustion_flow(self, mock_bus, mock_repo):
        """After max retries, task should be marked FAILED permanently."""
        from app.orchestrator.retry_handler import RetryHandler

        task_id = uuid4()
        task = _make_task_mock(
            id=task_id,
            events=[
                {"type": "task.retry_incremented", "retry_count": 1},
                {"type": "task.retry_incremented", "retry_count": 2},
                {"type": "task.retry_incremented", "retry_count": 3},
            ],
            status="FAILED",
        )
        mock_repo.get.return_value = task

        handler = RetryHandler(mock_bus, mock_repo, default_max_retries=3)

        event = Event(
            event_type="task.failed",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id), "failure_reason": "agent_error"},
        )
        await handler.handle_failure(event)

        # Should NOT schedule retry
        mock_bus.publish_delayed.assert_not_awaited()

        # Should emit retry_exhausted
        publish_calls = [c[0][0] for c in mock_bus.publish.call_args_list]
        exhausted = [e for e in publish_calls if e.event_type == "task.retry_exhausted"]
        assert len(exhausted) == 1
        assert exhausted[0].payload["status"] == "FAILED"


class TestDependencyGating:
    """Integration: dependency gate and release flow."""

    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        repo.get = AsyncMock()
        repo.update = AsyncMock()
        repo.list = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock()
        bus.subscribe = AsyncMock(return_value="sub-2")
        bus.publish = AsyncMock()
        return bus

    @pytest.mark.asyncio
    async def test_gate_and_release(self, mock_bus, mock_repo):
        """Task with unmet deps is held; when dep completes, task is released."""
        from app.orchestrator.dependency_resolver import DependencyResolver

        dep_id = uuid4()
        task_id = uuid4()

        # Initial state: dep is RUNNING
        dep_running = _make_task_mock(id=dep_id, status="RUNNING")
        task_waiting = _make_task_mock(
            id=task_id, dependencies=[str(dep_id)], status="CREATED"
        )

        mock_repo.get.side_effect = lambda tid: {
            dep_id: dep_running,
            task_id: task_waiting,
        }.get(tid)

        resolver = DependencyResolver(mock_bus, mock_repo)

        # Check deps — should be unmet
        event = Event(
            event_type="task.created",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )
        deps_met = await resolver.check_dependencies(event)
        assert deps_met is False

        # Now dep completes
        dep_completed = _make_task_mock(id=dep_id, status="COMPLETED")
        mock_repo.get.side_effect = lambda tid: {
            dep_id: dep_completed,
            task_id: task_waiting,
        }.get(tid)

        # Re-evaluate — task should be released
        mock_repo.list.return_value = [task_waiting]
        await resolver.re_evaluate_created()

        publish_calls = [c[0][0] for c in mock_bus.publish.call_args_list]
        requeue_events = [e for e in publish_calls if e.event_type == "task.created"]
        assert len(requeue_events) == 1
        assert requeue_events[0].payload["deps_resolved"] is True

    @pytest.mark.asyncio
    async def test_multiple_deps_release(self, mock_bus, mock_repo):
        """Multiple tasks released when a shared dependency completes."""
        from app.orchestrator.dependency_resolver import DependencyResolver

        dep_id = uuid4()
        task1_id = uuid4()
        task2_id = uuid4()

        dep_completed = _make_task_mock(id=dep_id, status="COMPLETED")
        task1 = _make_task_mock(id=task1_id, dependencies=[str(dep_id)])
        task2 = _make_task_mock(id=task2_id, dependencies=[str(dep_id)])

        mock_repo.get.side_effect = lambda tid: {
            dep_id: dep_completed,
        }.get(tid)
        mock_repo.list.return_value = [task1, task2]

        resolver = DependencyResolver(mock_bus, mock_repo)
        await resolver.re_evaluate_created()

        publish_calls = [c[0][0] for c in mock_bus.publish.call_args_list]
        requeue_events = [e for e in publish_calls if e.event_type == "task.created"]
        assert len(requeue_events) == 2


class TestTimeoutDetection:
    """Integration: timeout detection on running tasks."""

    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        repo.get = AsyncMock()
        repo.update = AsyncMock()
        return repo

    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock()
        bus.subscribe = AsyncMock(return_value="sub-3")
        bus.publish = AsyncMock()
        return bus

    @pytest.mark.asyncio
    async def test_timeout_detection_on_step_advance(self, mock_bus, mock_repo):
        """Timeout should be detected when a step advances."""
        from app.orchestrator.timeout_handler import TimeoutHandler

        task_id = uuid4()
        # Started 400s ago, timeout is 300s
        started = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(
            seconds=400
        )
        task = _make_task_mock(id=task_id, status="RUNNING", started_at=started)
        mock_repo.get.return_value = task

        handler = TimeoutHandler(mock_bus, mock_repo, default_timeout=300)

        event = Event(
            event_type="task.step_advanced",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )
        await handler.check_timeout(event)

        # Should mark as FAILED
        mock_repo.update.assert_awaited_once()
        update_kwargs = mock_repo.update.call_args[1]
        assert update_kwargs["status"] == "FAILED"

        # Should emit timeout event
        publish_calls = [c[0][0] for c in mock_bus.publish.call_args_list]
        timeout_events = [e for e in publish_calls if e.event_type == "task.timeout"]
        assert len(timeout_events) == 1

    @pytest.mark.asyncio
    async def test_no_false_timeout_within_window(self, mock_bus, mock_repo):
        """Tasks within timeout window should NOT be failed."""
        from app.orchestrator.timeout_handler import TimeoutHandler

        task_id = uuid4()
        started = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(
            seconds=100
        )
        task = _make_task_mock(id=task_id, status="RUNNING", started_at=started)
        mock_repo.get.return_value = task

        handler = TimeoutHandler(mock_bus, mock_repo, default_timeout=300)

        event = Event(
            event_type="task.step_advanced",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )
        await handler.check_timeout(event)

        mock_repo.update.assert_not_awaited()
