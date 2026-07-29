"""Tests for EvolutionEngine."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.learning.evolution_engine import (
    EvolutionAlreadyRunning,
    EvolutionEngine,
    EvolutionState,
    RateLimitExceeded,
)


class TestEvolutionEngine:
    @pytest.fixture
    def mock_bus(self):
        bus = AsyncMock()
        bus.emit = AsyncMock()
        return bus

    @pytest.fixture
    def mock_meta_agent(self):
        agent = AsyncMock()
        agent.execute = AsyncMock(return_value={
            "status": "completed",
            "summary": "Audit found 0 gaps",
        })
        return agent

    @pytest.fixture
    def engine(self, mock_bus, mock_meta_agent):
        return EvolutionEngine(
            bus=mock_bus,
            meta_agent=mock_meta_agent,
            min_tasks_between_cycles=3,
        )

    def test_initial_state(self, engine):
        """Engine should start in IDLE state with 0 tasks."""
        assert engine.state == EvolutionState.IDLE
        assert engine.tasks_since_last_cycle == 0
        assert engine.history == []

    @pytest.mark.asyncio
    async def test_on_task_completed_increments_counter(self, engine):
        """on_task_completed should increment the task counter."""
        await engine.on_task_completed("task.completed", {"task_id": "1"})
        assert engine.tasks_since_last_cycle == 1

    @pytest.mark.asyncio
    async def test_on_task_completed_triggers_cycle(self, engine, mock_meta_agent):
        """When threshold is met, on_task_completed should trigger a cycle."""
        for i in range(3):
            await engine.on_task_completed("task.completed", {"task_id": str(i)})

        assert engine.tasks_since_last_cycle == 0  # Reset after cycle
        assert len(engine.history) == 1
        mock_meta_agent.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_cycle_sets_running(self, engine):
        """start_cycle should set state to RUNNING."""
        engine._tasks_since_last_cycle = 3
        await engine.start_cycle()
        assert engine.state == EvolutionState.RUNNING

    @pytest.mark.asyncio
    async def test_reject_concurrent_cycle(self, engine):
        """Starting a cycle while running should raise EvolutionAlreadyRunning."""
        engine._tasks_since_last_cycle = 3
        await engine.start_cycle()

        with pytest.raises(EvolutionAlreadyRunning):
            await engine.start_cycle()

    @pytest.mark.asyncio
    async def test_rate_limiting(self, engine):
        """Cycle should be rejected if tasks < min_tasks_between_cycles."""
        engine._tasks_since_last_cycle = 1  # Below threshold of 3

        with pytest.raises(RateLimitExceeded) as exc_info:
            await engine.start_cycle()

        assert exc_info.value.tasks_since == 1
        assert exc_info.value.min_tasks == 3

    @pytest.mark.asyncio
    async def test_run_evolution_cycle_completes(self, engine, mock_meta_agent):
        """run_evolution_cycle should complete and record history."""
        engine._tasks_since_last_cycle = 3

        result = await engine.run_evolution_cycle()

        assert result["status"] == "completed"
        assert result["cycle_id"] is not None
        assert engine.state == EvolutionState.IDLE
        assert len(engine.history) == 1

    @pytest.mark.asyncio
    async def test_cycle_publishes_events(self, engine, mock_bus):
        """Cycle should publish started and completed events."""
        engine._tasks_since_last_cycle = 3

        await engine.run_evolution_cycle()

        assert mock_bus.emit.call_count == 2
        first_call = mock_bus.emit.call_args_list[0]
        assert first_call[0][0] == "evolution_cycle_started"
        second_call = mock_bus.emit.call_args_list[1]
        assert second_call[0][0] == "evolution_cycle_completed"

    @pytest.mark.asyncio
    async def test_cycle_resets_counter(self, engine):
        """After cycle completes, counter should reset to 0."""
        engine._tasks_since_last_cycle = 5

        await engine.run_evolution_cycle()

        assert engine.tasks_since_last_cycle == 0

    @pytest.mark.asyncio
    async def test_get_history_limit(self, engine):
        """get_history should respect the limit parameter."""
        for _ in range(5):
            engine._history.append({"cycle_id": "test"})

        assert len(engine.get_history(limit=3)) == 3
        assert len(engine.get_history(limit=10)) == 5

    @pytest.mark.asyncio
    async def test_cycle_failure_recorded(self, engine, mock_meta_agent):
        """If meta_agent fails, cycle should record failure."""
        mock_meta_agent.execute = AsyncMock(side_effect=Exception("meta failed"))
        engine._tasks_since_last_cycle = 3

        result = await engine.run_evolution_cycle()

        assert result["status"] == "failed"
        assert "meta failed" in result["error"]
        assert engine.state == EvolutionState.IDLE

    @pytest.mark.asyncio
    async def test_cycle_failure_publishes_failed_event(self, engine, mock_bus, mock_meta_agent):
        """Failed cycle should publish evolution_cycle_failed event."""
        mock_meta_agent.execute = AsyncMock(side_effect=Exception("boom"))
        engine._tasks_since_last_cycle = 3

        await engine.run_evolution_cycle()

        failed_call = mock_bus.emit.call_args_list[-1]
        assert failed_call[0][0] == "evolution_cycle_failed"

    @pytest.mark.asyncio
    async def test_no_meta_agent_cycle_skips(self, engine, mock_bus):
        """Cycle should handle missing meta_agent gracefully."""
        engine._meta_agent = None
        engine._tasks_since_last_cycle = 3

        result = await engine.run_evolution_cycle()

        assert result["status"] == "completed"
        assert result["result"]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_concurrent_cycle_rejection_via_event(self, engine):
        """on_task_completed should skip if cycle already running."""
        engine._tasks_since_last_cycle = 2
        # Simulate a running cycle
        engine._state = EvolutionState.RUNNING

        # This should not raise, just log and skip
        await engine.on_task_completed("task.completed", {"task_id": "99"})
        assert engine.tasks_since_last_cycle == 2  # Counter not incremented during running
