"""Tests for TaskExecutor — event-driven task lifecycle orchestration."""

from unittest.mock import AsyncMock, MagicMock, patch
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
    t.assigned_agent = overrides.get("assigned_agent", "executor")
    t.created_at = datetime.datetime.now(tz=datetime.timezone.utc)
    t.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    return t


def _make_task_dict(**overrides):
    """Create a task dictionary (as returned by TaskManager.get_task)."""
    return {
        "id": str(overrides.get("id", uuid4())),
        "goal": overrides.get("goal", "Test goal"),
        "status": overrides.get("status", "CREATED"),
        "dependencies": overrides.get("dependencies", []),
        "assigned_agent": overrides.get("assigned_agent", "executor"),
        "plan": overrides.get("plan", {}),
        "steps": overrides.get("steps", []),
        "current_step": overrides.get("current_step", 0),
        "artifacts": overrides.get("artifacts", {}),
        "events": overrides.get("events", []),
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "started_at": None,
        "completed_at": None,
    }


class TestTaskExecutor:
    """Tests for TaskExecutor."""

    @pytest.fixture
    def mock_bus(self):
        """Mock InMemoryEventBus."""
        bus = AsyncMock()
        bus.subscribe = AsyncMock(return_value="sub-id")
        bus.unsubscribe = AsyncMock(return_value=True)
        bus.publish = AsyncMock()
        return bus

    @pytest.fixture
    def mock_task_manager(self):
        """Mock TaskManager."""
        tm = AsyncMock()
        tm.get_task = AsyncMock(return_value=None)
        tm.transition_task = AsyncMock(return_value={})
        return tm

    @pytest.fixture
    def mock_agent_manager(self):
        """Mock AgentManager."""
        am = AsyncMock()
        am.dispatch = AsyncMock(return_value={"status": "success", "result": "done"})
        return am

    @pytest.fixture
    def executor(self, mock_bus, mock_task_manager, mock_agent_manager):
        """Create TaskExecutor with mocked dependencies."""
        from app.orchestrator.task_executor import TaskExecutor
        return TaskExecutor(mock_bus, mock_task_manager, mock_agent_manager)

    @pytest.mark.asyncio
    async def test_subscribe_registers_listeners(self, executor, mock_bus):
        """start() should subscribe to task.created and task.queued events."""
        await executor.start()

        calls = mock_bus.subscribe.call_args_list
        subscribed_events = [c[0][0] for c in calls]
        assert "task.created" in subscribed_events
        assert "task.queued" in subscribed_events

    @pytest.mark.asyncio
    async def test_stop_unsubscribes(self, executor, mock_bus):
        """stop() should unsubscribe from all events."""
        await executor.start()
        await executor.stop()

        assert mock_bus.unsubscribe.call_count == 2
        assert executor._subscriptions == []

    @pytest.mark.asyncio
    async def test_handle_task_created_no_aggregate_id(
        self, executor, mock_bus, mock_task_manager
    ):
        """Task created with no aggregate_id should be skipped."""
        event = Event(
            event_type="task.created",
            aggregate_id="",
            payload={},
        )

        await executor._handle_task_created(event)

        mock_task_manager.get_task.assert_not_awaited()
        mock_task_manager.transition_task.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_task_created_task_not_found(
        self, executor, mock_bus, mock_task_manager
    ):
        """Task created for non-existent task should be skipped."""
        task_id = uuid4()
        mock_task_manager.get_task.return_value = None

        event = Event(
            event_type="task.created",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        await executor._handle_task_created(event)

        mock_task_manager.transition_task.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_task_created_no_deps_queues(
        self, executor, mock_bus, mock_task_manager
    ):
        """Task with no dependencies should be queued immediately."""
        task_id = uuid4()
        task_dict = _make_task_dict(id=task_id, dependencies=[], assigned_agent="executor")
        mock_task_manager.get_task.return_value = task_dict

        event = Event(
            event_type="task.created",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        await executor._handle_task_created(event)

        mock_task_manager.transition_task.assert_awaited_once_with(task_id, "QUEUED")
        assert mock_bus.publish.await_count == 1
        published_event = mock_bus.publish.call_args[0][0]
        assert published_event.event_type == "task.queued"
        assert published_event.aggregate_id == str(task_id)

    @pytest.mark.asyncio
    async def test_handle_task_created_deps_met_queues(
        self, executor, mock_bus, mock_task_manager
    ):
        """Task with all dependencies completed should be queued."""
        task_id = uuid4()
        dep_id = uuid4()
        task_dict = _make_task_dict(
            id=task_id, dependencies=[str(dep_id)], assigned_agent="executor"
        )
        dep_dict = _make_task_dict(id=dep_id, status="COMPLETED")

        mock_task_manager.get_task.side_effect = lambda tid: {
            task_id: task_dict,
            dep_id: dep_dict,
        }.get(tid)

        event = Event(
            event_type="task.created",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        await executor._handle_task_created(event)

        mock_task_manager.transition_task.assert_awaited_once_with(task_id, "QUEUED")

    @pytest.mark.asyncio
    async def test_handle_task_created_deps_unmet_holds(
        self, executor, mock_bus, mock_task_manager
    ):
        """Task with unmet dependencies should remain in CREATED."""
        task_id = uuid4()
        dep_id = uuid4()
        task_dict = _make_task_dict(
            id=task_id, dependencies=[str(dep_id)], assigned_agent="executor"
        )
        dep_dict = _make_task_dict(id=dep_id, status="RUNNING")  # Not completed

        mock_task_manager.get_task.side_effect = lambda tid: {
            task_id: task_dict,
            dep_id: dep_dict,
        }.get(tid)

        event = Event(
            event_type="task.created",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        await executor._handle_task_created(event)

        mock_task_manager.transition_task.assert_not_awaited()
        mock_bus.publish.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_task_queued_dispatches_to_agent(
        self, executor, mock_bus, mock_task_manager, mock_agent_manager
    ):
        """Task queued event should dispatch to assigned agent."""
        task_id = uuid4()
        task_dict = _make_task_dict(
            id=task_id, assigned_agent="executor", goal="Build something"
        )
        mock_task_manager.get_task.return_value = task_dict

        event = Event(
            event_type="task.queued",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id), "assigned_agent": "executor"},
        )

        await executor._handle_task_queued(event)

        # Should transition to RUNNING, then to COMPLETED (from agent success)
        assert mock_task_manager.transition_task.await_count == 2
        calls = mock_task_manager.transition_task.call_args_list
        assert calls[0][0][1] == "RUNNING"
        assert calls[1][0][1] == "COMPLETED"

        mock_agent_manager.dispatch.assert_awaited_once_with(
            agent_id="executor",
            task="Build something",
            context={"task_id": str(task_id), "task": task_dict},
        )

    @pytest.mark.asyncio
    async def test_handle_task_queued_no_agent_skips(
        self, executor, mock_bus, mock_task_manager, mock_agent_manager
    ):
        """Task queued with no assigned agent should skip dispatch."""
        task_id = uuid4()
        task_dict = _make_task_dict(id=task_id, assigned_agent=None)
        mock_task_manager.get_task.return_value = task_dict

        event = Event(
            event_type="task.queued",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id)},
        )

        await executor._handle_task_queued(event)

        mock_agent_manager.dispatch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_agent_success_completes_task(
        self, executor, mock_bus, mock_task_manager, mock_agent_manager
    ):
        """Successful agent result should transition task to COMPLETED."""
        task_id = uuid4()
        task_dict = _make_task_dict(id=task_id, assigned_agent="executor")
        mock_task_manager.get_task.return_value = task_dict
        mock_agent_manager.dispatch.return_value = {
            "status": "success",
            "result": "Task completed",
        }

        event = Event(
            event_type="task.queued",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id), "assigned_agent": "executor"},
        )

        await executor._handle_task_queued(event)

        # Should transition RUNNING then COMPLETED
        assert mock_task_manager.transition_task.await_count == 2
        calls = mock_task_manager.transition_task.call_args_list
        assert calls[0][0][1] == "RUNNING"
        assert calls[1][0][1] == "COMPLETED"

        # Should emit task.completed
        published_events = [
            c[0][0] for c in mock_bus.publish.call_args_list
        ]
        completed_events = [e for e in published_events if e.event_type == "task.completed"]
        assert len(completed_events) == 1

    @pytest.mark.asyncio
    async def test_agent_failure_fails_task(
        self, executor, mock_bus, mock_task_manager, mock_agent_manager
    ):
        """Failed agent result should transition task to FAILED."""
        task_id = uuid4()
        task_dict = _make_task_dict(id=task_id, assigned_agent="executor")
        mock_task_manager.get_task.return_value = task_dict
        mock_agent_manager.dispatch.return_value = {
            "status": "failed",
            "error": "Agent crashed",
        }

        event = Event(
            event_type="task.queued",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id), "assigned_agent": "executor"},
        )

        await executor._handle_task_queued(event)

        # Should transition RUNNING then FAILED
        assert mock_task_manager.transition_task.await_count == 2
        calls = mock_task_manager.transition_task.call_args_list
        assert calls[0][0][1] == "RUNNING"
        assert calls[1][0][1] == "FAILED"

        # Should emit task.failed
        published_events = [
            c[0][0] for c in mock_bus.publish.call_args_list
        ]
        failed_events = [e for e in published_events if e.event_type == "task.failed"]
        assert len(failed_events) == 1
        assert failed_events[0].payload["failure_reason"] == "agent_error"

    @pytest.mark.asyncio
    async def test_agent_exception_fails_task(
        self, executor, mock_bus, mock_task_manager, mock_agent_manager
    ):
        """Agent exception should transition task to FAILED."""
        task_id = uuid4()
        task_dict = _make_task_dict(id=task_id, assigned_agent="executor")
        mock_task_manager.get_task.return_value = task_dict
        mock_agent_manager.dispatch.side_effect = RuntimeError("Agent crashed")

        event = Event(
            event_type="task.queued",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id), "assigned_agent": "executor"},
        )

        await executor._handle_task_queued(event)

        # Should transition RUNNING then FAILED
        assert mock_task_manager.transition_task.await_count == 2
        calls = mock_task_manager.transition_task.call_args_list
        assert calls[0][0][1] == "RUNNING"
        assert calls[1][0][1] == "FAILED"

    @pytest.mark.asyncio
    async def test_check_dependencies_all_completed(
        self, executor, mock_task_manager
    ):
        """_check_dependencies should return True when all deps are completed."""
        dep1_id = uuid4()
        dep2_id = uuid4()

        mock_task_manager.get_task.side_effect = lambda tid: {
            dep1_id: _make_task_dict(id=dep1_id, status="COMPLETED"),
            dep2_id: _make_task_dict(id=dep2_id, status="COMPLETED"),
        }.get(tid)

        result = await executor._check_dependencies(
            str(uuid4()), [str(dep1_id), str(dep2_id)]
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_check_dependencies_one_not_completed(
        self, executor, mock_task_manager
    ):
        """_check_dependencies should return False when any dep is not completed."""
        dep1_id = uuid4()
        dep2_id = uuid4()

        mock_task_manager.get_task.side_effect = lambda tid: {
            dep1_id: _make_task_dict(id=dep1_id, status="COMPLETED"),
            dep2_id: _make_task_dict(id=dep2_id, status="RUNNING"),
        }.get(tid)

        result = await executor._check_dependencies(
            str(uuid4()), [str(dep1_id), str(dep2_id)]
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_check_dependencies_missing_dep(
        self, executor, mock_task_manager
    ):
        """_check_dependencies should return False for missing dep."""
        dep_id = uuid4()

        mock_task_manager.get_task.return_value = None

        result = await executor._check_dependencies(str(uuid4()), [str(dep_id)])
        assert result is False
