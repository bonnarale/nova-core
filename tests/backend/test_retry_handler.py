"""Tests for RetryHandler — retry logic with exponential backoff."""

import asyncio
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
    t.status = overrides.get("status", "FAILED")
    t.events = overrides.get("events", [])
    t.dependencies = overrides.get("dependencies", [])
    t.retry_count = overrides.get("retry_count", 0)
    t.max_retries = overrides.get("max_retries", 3)
    t.started_at = overrides.get("started_at", None)
    t.created_at = datetime.datetime.now(tz=datetime.timezone.utc)
    t.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    return t


class TestRetryHandler:
    """Tests for RetryHandler."""

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
        bus.subscribe = AsyncMock(return_value="sub-retry")
        bus.publish = AsyncMock()
        bus.publish_delayed = AsyncMock(return_value="delay-retry")
        return bus

    @pytest.fixture
    def handler(self, mock_bus, mock_repo):
        """Create RetryHandler with mocked dependencies."""
        from app.orchestrator.retry_handler import RetryHandler
        return RetryHandler(mock_bus, mock_repo, default_max_retries=3)

    @pytest.mark.asyncio
    async def test_subscribe_registers_listener(self, handler, mock_bus):
        """subscribe_to should register for task.failed events."""
        await handler.subscribe_to()
        mock_bus.subscribe.assert_awaited_with("task.failed", handler._handle_failure)

    @pytest.mark.asyncio
    async def test_retry_increments_count(self, handler, mock_repo, mock_bus):
        """On retryable failure, retry_count should be incremented."""
        task_id = uuid4()
        task = _make_task_mock(id=task_id, events=[], status="FAILED")
        mock_repo.get.return_value = task

        event = Event(
            event_type="task.failed",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id), "failure_reason": "agent_error"},
        )

        await handler.handle_failure(event)

        # Should have called update with incremented retry_count
        mock_repo.update.assert_awaited()
        # Extract events from the update call (positional arg is task_id, kwargs contain events)
        call_args, call_kwargs = mock_repo.update.call_args
        updated_events = call_kwargs.get("events")
        assert updated_events is not None
        # Last event should be retry_incremented with count 1
        last_event = updated_events[-1]
        assert last_event["type"] == "task.retry_incremented"
        assert last_event["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_retry_emits_retrying_event(self, handler, mock_repo, mock_bus):
        """On retry, should emit task.retrying event."""
        task_id = uuid4()
        task = _make_task_mock(id=task_id, events=[], status="FAILED")
        mock_repo.get.return_value = task

        event = Event(
            event_type="task.failed",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id), "failure_reason": "agent_error"},
        )

        await handler.handle_failure(event)

        # Should emit task.retrying
        publish_calls = [c for c in mock_bus.publish.call_args_list]
        retrying_events = [
            c for c in publish_calls
            if c[0][0].event_type == "task.retrying"
        ]
        assert len(retrying_events) == 1

    @pytest.mark.asyncio
    async def test_retry_schedules_delayed_requeue(self, handler, mock_repo, mock_bus):
        """On retry, should schedule delayed re-queue."""
        task_id = uuid4()
        task = _make_task_mock(id=task_id, events=[], status="FAILED")
        mock_repo.get.return_value = task

        event = Event(
            event_type="task.failed",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id), "failure_reason": "agent_error"},
        )

        await handler.handle_failure(event)

        mock_bus.publish_delayed.assert_awaited_once()
        delay_args = mock_bus.publish_delayed.call_args
        assert delay_args[0][1] == 30  # First retry: 30s backoff

    @pytest.mark.asyncio
    async def test_retry_exhaustion_marks_failed(self, handler, mock_repo, mock_bus):
        """When retries exhausted, should mark FAILED permanently."""
        task_id = uuid4()
        # Already retried 3 times
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

        event = Event(
            event_type="task.failed",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id), "failure_reason": "agent_error"},
        )

        await handler.handle_failure(event)

        # Should NOT schedule retry
        mock_bus.publish_delayed.assert_not_awaited()

        # Should emit task.retry_exhausted
        publish_calls = [c[0][0] for c in mock_bus.publish.call_args_list]
        exhausted_events = [e for e in publish_calls if e.event_type == "task.retry_exhausted"]
        assert len(exhausted_events) == 1

    @pytest.mark.asyncio
    async def test_non_retryable_failure_skips_retry(self, handler, mock_repo, mock_bus):
        """Non-retryable failure reason should not trigger retry."""
        task_id = uuid4()
        task = _make_task_mock(id=task_id, events=[], status="FAILED")
        mock_repo.get.return_value = task

        event = Event(
            event_type="task.failed",
            aggregate_id=str(task_id),
            payload={"task_id": str(task_id), "failure_reason": "validation_error"},
        )

        await handler.handle_failure(event)

        # Should NOT update or retry
        mock_repo.update.assert_not_awaited()
        mock_bus.publish_delayed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_task_id_ignored(self, handler, mock_repo, mock_bus):
        """Events without task_id should be silently ignored."""
        event = Event(
            event_type="task.failed",
            aggregate_id="",
            payload={},
        )

        await handler.handle_failure(event)
        mock_repo.get.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_task_not_found_ignored(self, handler, mock_repo, mock_bus):
        """Tasks not found in repo should be silently ignored."""
        mock_repo.get.return_value = None
        event = Event(
            event_type="task.failed",
            aggregate_id=str(uuid4()),
            payload={"task_id": str(uuid4())},
        )

        await handler.handle_failure(event)
        mock_repo.update.assert_not_awaited()

    def test_backoff_calculation(self, handler):
        """Backoff should be exponential: 30, 60, 120 (capped)."""
        assert handler._calculate_backoff(0) == 30
        assert handler._calculate_backoff(1) == 60
        assert handler._calculate_backoff(2) == 120
        assert handler._calculate_backoff(3) == 120  # Capped
        assert handler._calculate_backoff(4) == 120  # Capped

    def test_extract_retry_count_from_events(self, handler):
        """Should extract retry_count from task events list."""
        task = _make_task_mock(events=[
            {"type": "task.retry_incremented", "retry_count": 1},
            {"type": "task.retry_incremented", "retry_count": 2},
        ])
        assert handler._extract_retry_count(task) == 2

    def test_extract_retry_count_empty_events(self, handler):
        """Should return 0 when no retry events exist."""
        task = _make_task_mock(events=[])
        assert handler._extract_retry_count(task) == 0
