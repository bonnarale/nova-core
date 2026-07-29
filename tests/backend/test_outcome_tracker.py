"""Tests for OutcomeTracker — outcome creation, deduplication, event subscription."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.learning.outcome_tracker import InMemoryOutcomeStore, OutcomeTracker


class TestInMemoryOutcomeStore:
    """Tests for InMemoryOutcomeStore."""

    @pytest.fixture
    def store(self):
        return InMemoryOutcomeStore()

    @pytest.mark.asyncio
    async def test_create_and_get(self, store):
        from app.learning.models import ExecutionOutcome

        outcome = ExecutionOutcome(
            id="o1",
            execution_id="exec-1",
            task_id="task-1",
            strategy_used="greedy",
            outcome="success",
            duration_ms=150,
            error_count=0,
        )
        await store.create(outcome)
        result = await store.get_by_execution("exec-1")
        assert result is not None
        assert result.id == "o1"
        assert result.outcome == "success"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store):
        result = await store.get_by_execution("nope")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_strategy(self, store):
        from app.learning.models import ExecutionOutcome

        for i in range(5):
            await store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"exec-{i}",
                    strategy_used="greedy" if i < 3 else "lazy",
                    outcome="success",
                )
            )
        greedy = await store.list_by_strategy("greedy")
        assert len(greedy) == 3
        lazy = await store.list_by_strategy("lazy")
        assert len(lazy) == 2

    @pytest.mark.asyncio
    async def test_list_all(self, store):
        from app.learning.models import ExecutionOutcome

        for i in range(3):
            await store.create(
                ExecutionOutcome(id=f"o{i}", execution_id=f"exec-{i}", outcome="success")
            )
        all_outcomes = await store.list_all()
        assert len(all_outcomes) == 3

    @pytest.mark.asyncio
    async def test_count(self, store):
        from app.learning.models import ExecutionOutcome

        assert await store.count() == 0
        await store.create(ExecutionOutcome(id="o1", execution_id="e1", outcome="success"))
        assert await store.count() == 1

    @pytest.mark.asyncio
    async def test_list_by_agent(self, store):
        from app.learning.models import ExecutionOutcome

        await store.create(
            ExecutionOutcome(id="o1", execution_id="e1", task_id="agent-a", outcome="success")
        )
        await store.create(
            ExecutionOutcome(id="o2", execution_id="e2", task_id="agent-b", outcome="failure")
        )
        agent_a = await store.list_by_agent("agent-a")
        assert len(agent_a) == 1
        assert agent_a[0].task_id == "agent-a"


class TestOutcomeTracker:
    """Tests for OutcomeTracker."""

    @pytest.fixture
    def mock_event_bus(self):
        bus = MagicMock()
        bus.on = MagicMock()
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def tracker(self, mock_event_bus):
        return OutcomeTracker(event_bus=mock_event_bus)

    @pytest.mark.asyncio
    async def test_record_outcome_creates_record(self, tracker):
        outcome = await tracker.record_outcome(
            execution_id="exec-1",
            task_id="task-1",
            strategy_used="greedy",
            outcome="success",
            duration_ms=200,
        )
        assert outcome.execution_id == "exec-1"
        assert outcome.outcome == "success"
        assert outcome.strategy_used == "greedy"

    @pytest.mark.asyncio
    async def test_deduplication(self, tracker):
        first = await tracker.record_outcome(execution_id="exec-1", outcome="success")
        second = await tracker.record_outcome(execution_id="exec-1", outcome="failure")
        assert first.id == second.id  # same record returned
        assert second.outcome == "success"  # original preserved

    @pytest.mark.asyncio
    async def test_subscribe_registers_handlers(self, tracker, mock_event_bus):
        await tracker.subscribe()
        event_types = [c[0][0] for c in mock_event_bus.on.call_args_list]
        assert "task.completed" in event_types
        assert "task.failed" in event_types

    @pytest.mark.asyncio
    async def test_on_task_completed_records_success(self, tracker, mock_event_bus):
        await tracker.subscribe()
        # Find the handler registered for task.completed
        handler = None
        for call in mock_event_bus.on.call_args_list:
            if call[0][0] == "task.completed":
                handler = call[0][1]
                break
        assert handler is not None

        await handler("task.completed", {"task_id": "t1", "duration_ms": 100})
        outcome = await tracker.store.get_by_execution("t1")
        assert outcome is not None
        assert outcome.outcome == "success"

    @pytest.mark.asyncio
    async def test_on_task_failed_records_failure(self, tracker, mock_event_bus):
        await tracker.subscribe()
        handler = None
        for call in mock_event_bus.on.call_args_list:
            if call[0][0] == "task.failed":
                handler = call[0][1]
                break
        assert handler is not None

        await handler("task.failed", {"task_id": "t2", "error_count": 3})
        outcome = await tracker.store.get_by_execution("t2")
        assert outcome is not None
        assert outcome.outcome == "failure"
        assert outcome.error_count == 3
