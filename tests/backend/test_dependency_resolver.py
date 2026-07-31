"""Tests for DependencyResolver — dependency gating and re-evaluation."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.events.schemas import Event


def _make_task_mock(**overrides):
    """Create a mock task object."""
    import datetime
    t = MagicMock()
    t.id = overrides.get("id", uuid4())
    t.goal = overrides.get("goal", "Test goal")
    t.status = overrides.get("status", "CREATED")
    t.events = overrides.get("events", [])
    t.dependencies = overrides.get("dependencies", [])
    t.created_at = datetime.datetime.now(tz=datetime.timezone.utc)
    t.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    return t


class TestDependencyResolver:
    """Tests for DependencyResolver."""

    @pytest.fixture
    def mock_repo(self):
        """Mock TaskRepository."""
        repo = AsyncMock()
        repo.get = AsyncMock()
        repo.update = AsyncMock()
        repo.list = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def mock_bus(self):
        """Mock InMemoryEventBus."""
        bus = AsyncMock()
        bus.subscribe = AsyncMock(return_value="sub-deps")
        bus.publish = AsyncMock()
        return bus

    @pytest.fixture
    def resolver(self, mock_bus, mock_repo):
        """Create DependencyResolver with mocked dependencies."""
        from app.orchestrator.dependency_resolver import DependencyResolver
        return DependencyResolver(mock_bus, mock_repo)

    @pytest.mark.asyncio
    async def test_subscribe_registers_listeners(self, resolver, mock_bus):
        """subscribe_to should register for task.created and task.completed events."""
        await resolver.subscribe_to()

        calls = mock_bus.subscribe.call_args_list
        subscribed_events = [c[0][0] for c in calls]
        assert "task.created" in subscribed_events
        assert "task.completed" in subscribed_events

    @pytest.mark.asyncio
    async def test_no_dependencies_returns_true(self, resolver, mock_repo, mock_bus):
        """Task with no dependencies should return True."""
        task_id = uuid4()
        task = _make_task_mock(id=task_id, dependencies=[])
        mock_repo.get.return_value = task

        event = Event(
            event_type="task.created",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        result = await resolver.check_dependencies(event)
        assert result is True

    @pytest.mark.asyncio
    async def test_all_deps_met_returns_true(self, resolver, mock_repo, mock_bus):
        """Task with all deps COMPLETED should return True."""
        task_id = uuid4()
        dep1_id = uuid4()
        dep2_id = uuid4()

        task = _make_task_mock(id=task_id, dependencies=[str(dep1_id), str(dep2_id)])
        dep1 = _make_task_mock(id=dep1_id, status="COMPLETED")
        dep2 = _make_task_mock(id=dep2_id, status="COMPLETED")

        mock_repo.get.side_effect = lambda tid: {
            task_id: task, dep1_id: dep1, dep2_id: dep2
        }.get(tid)

        event = Event(
            event_type="task.created",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        result = await resolver.check_dependencies(event)
        assert result is True

    @pytest.mark.asyncio
    async def test_unmet_dep_returns_false(self, resolver, mock_repo, mock_bus):
        """Task with unmet dependency should return False."""
        task_id = uuid4()
        dep1_id = uuid4()
        dep2_id = uuid4()

        task = _make_task_mock(id=task_id, dependencies=[str(dep1_id), str(dep2_id)])
        dep1 = _make_task_mock(id=dep1_id, status="COMPLETED")
        dep2 = _make_task_mock(id=dep2_id, status="RUNNING")  # Not completed

        mock_repo.get.side_effect = lambda tid: {
            task_id: task, dep1_id: dep1, dep2_id: dep2
        }.get(tid)

        event = Event(
            event_type="task.created",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        result = await resolver.check_dependencies(event)
        assert result is False

    @pytest.mark.asyncio
    async def test_unmet_dep_emits_event(self, resolver, mock_repo, mock_bus):
        """Unmet dependency should emit task.dependency_unmet event."""
        task_id = uuid4()
        dep1_id = uuid4()

        task = _make_task_mock(id=task_id, dependencies=[str(dep1_id)])
        dep1 = _make_task_mock(id=dep1_id, status="RUNNING")

        mock_repo.get.side_effect = lambda tid: {
            task_id: task, dep1_id: dep1,
        }.get(tid)

        event = Event(
            event_type="task.created",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        await resolver.check_dependencies(event)

        publish_calls = [c[0][0] for c in mock_bus.publish.call_args_list]
        unmet_events = [e for e in publish_calls if e.event_type == "task.dependency_unmet"]
        assert len(unmet_events) == 1
        assert unmet_events[0].payload["task_id"] == str(task_id)

    @pytest.mark.asyncio
    async def test_missing_dep_treated_as_unmet(self, resolver, mock_repo, mock_bus):
        """Non-existent dependency should be treated as unmet."""
        task_id = uuid4()
        dep1_id = uuid4()

        task = _make_task_mock(id=task_id, dependencies=[str(dep1_id)])

        mock_repo.get.side_effect = lambda tid: {
            task_id: task,
            # dep1_id returns None (not found)
        }.get(tid)

        event = Event(
            event_type="task.created",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        result = await resolver.check_dependencies(event)
        assert result is False

    @pytest.mark.asyncio
    async def test_re_evaluate_queues_unblocked_tasks(self, resolver, mock_repo, mock_bus):
        """re_evaluate_created should emit task.created for tasks whose deps are met."""
        dep_id = uuid4()
        task_id = uuid4()

        # Task waiting on dep_id
        waiting_task = _make_task_mock(id=task_id, dependencies=[str(dep_id)])
        # The dependency is now completed
        dep_task = _make_task_mock(id=dep_id, status="COMPLETED")

        mock_repo.list.return_value = [waiting_task]
        mock_repo.get.side_effect = lambda tid: {
            dep_id: dep_task,
        }.get(tid)

        await resolver.re_evaluate_created()

        publish_calls = [c[0][0] for c in mock_bus.publish.call_args_list]
        requeue_events = [e for e in publish_calls if e.event_type == "task.created"]
        assert len(requeue_events) == 1
        assert requeue_events[0].payload["deps_resolved"] is True

    @pytest.mark.asyncio
    async def test_re_evaluate_skips_still_unmet(self, resolver, mock_repo, mock_bus):
        """re_evaluate_created should not queue tasks with still-unmet deps."""
        dep_id = uuid4()
        task_id = uuid4()

        waiting_task = _make_task_mock(id=task_id, dependencies=[str(dep_id)])
        dep_task = _make_task_mock(id=dep_id, status="RUNNING")  # Not completed yet

        mock_repo.list.return_value = [waiting_task]
        mock_repo.get.side_effect = lambda tid: {
            dep_id: dep_task,
        }.get(tid)

        await resolver.re_evaluate_created()

        mock_bus.publish.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_re_evaluate_multiple_tasks(self, resolver, mock_repo, mock_bus):
        """re_evaluate_created should handle multiple tasks."""
        dep_id = uuid4()
        task1_id = uuid4()
        task2_id = uuid4()

        task1 = _make_task_mock(id=task1_id, dependencies=[str(dep_id)])
        task2 = _make_task_mock(id=task2_id, dependencies=[str(dep_id)])
        dep_task = _make_task_mock(id=dep_id, status="COMPLETED")

        mock_repo.list.return_value = [task1, task2]
        mock_repo.get.side_effect = lambda tid: {
            dep_id: dep_task,
        }.get(tid)

        await resolver.re_evaluate_created()

        publish_calls = [c[0][0] for c in mock_bus.publish.call_args_list]
        requeue_events = [e for e in publish_calls if e.event_type == "task.created"]
        assert len(requeue_events) == 2

    @pytest.mark.asyncio
    async def test_re_evaluate_skips_no_deps(self, resolver, mock_repo, mock_bus):
        """re_evaluate_created should skip tasks with no dependencies."""
        task = _make_task_mock(dependencies=[])
        mock_repo.list.return_value = [task]

        await resolver.re_evaluate_created()

        mock_bus.publish.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_task_id_ignored(self, resolver, mock_repo, mock_bus):
        """Events without aggregate_id should be silently ignored."""
        event = Event(
            event_type="task.created",
            aggregate_id="",
            payload={},
        )

        result = await resolver.check_dependencies(event)
        assert result is True

    @pytest.mark.asyncio
    async def test_task_not_found_returns_true(self, resolver, mock_repo, mock_bus):
        """Tasks not found in repo should return True (let them proceed)."""
        mock_repo.get.return_value = None
        event = Event(
            event_type="task.created",
            aggregate_id=str(uuid4()),
            payload={"task_id": str(uuid4())},
        )

        result = await resolver.check_dependencies(event)
        assert result is True
