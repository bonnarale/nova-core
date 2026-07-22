"""Tests for ExecutivePlanner."""

from __future__ import annotations

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from app.executive.planner import ExecutivePlanner
from app.executive.strategy import PlanningOutput, PlanningStrategy, SuggestedTask


class _TestStrategy(PlanningStrategy):
    """Strategy that returns controllable output for testing."""

    def __init__(self, output: PlanningOutput | None = None) -> None:
        self.analyze = AsyncMock(return_value=output or PlanningOutput())
        self.last_goals = None
        self.last_tasks = None

    async def analyze(self, goals, tasks, profile, recent_messages) -> PlanningOutput:
        self.last_goals = goals
        self.last_tasks = tasks
        return await self.analyze(goals, tasks, profile, recent_messages)


@pytest.fixture
def mock_goal_manager():
    gm = MagicMock()
    gm.list_goals = AsyncMock(return_value=[])
    return gm


@pytest.fixture
def mock_task_manager():
    tm = MagicMock()
    tm.list_tasks = AsyncMock(return_value=[])
    tm.create_task = AsyncMock(return_value={"id": "new-task-id", "goal": "test"})
    return tm


@pytest.fixture
def mock_agent_manager():
    am = MagicMock()
    am.get_runtime_agent = MagicMock(return_value=None)
    am.dispatch = AsyncMock(return_value={"status": "completed"})
    return am


@pytest.fixture
def mock_profile_memory():
    pm = MagicMock()
    pm.get_profile = AsyncMock(return_value={"id": "p1", "name": "Test"})
    return pm


@pytest.fixture
def mock_conversation_memory():
    cm = MagicMock()
    cm.get_history = AsyncMock(return_value=[{"role": "user", "content": "hello"}])
    return cm


@pytest.fixture
def mock_event_bus():
    eb = MagicMock()
    eb.emit = AsyncMock()
    return eb


@pytest.fixture
def planner(mock_goal_manager, mock_task_manager, mock_agent_manager,
            mock_profile_memory, mock_conversation_memory, mock_event_bus):
    return ExecutivePlanner(
        goal_manager=mock_goal_manager,
        task_manager=mock_task_manager,
        agent_manager=mock_agent_manager,
        profile_memory=mock_profile_memory,
        conversation_memory=mock_conversation_memory,
        event_bus=mock_event_bus,
    )


class TestExecutivePlanner:
    @pytest.mark.asyncio
    async def test_plan_no_goals_returns_empty(self, planner, mock_goal_manager):
        mock_goal_manager.list_goals.return_value = []

        output = await planner.plan(user_id="00000000-0000-0000-0000-000000000001")

        assert output.reviewed_goal_ids == []
        assert output.suggested_tasks == []

    @pytest.mark.asyncio
    async def test_plan_creates_task_from_goal(self, planner, mock_goal_manager, mock_task_manager, mock_event_bus):
        mock_goal_manager.list_goals.return_value = [
            {"id": "g1", "title": "Build feature", "status": "active", "priority": 3, "progress": 0},
        ]
        mock_task_manager.create_task.return_value = {
            "id": "task-1", "goal": "Execute: Build feature",
        }

        output = await planner.plan(user_id="00000000-0000-0000-0000-000000000001")

        assert len(output.suggested_tasks) == 1
        mock_task_manager.create_task.assert_awaited_once()
        mock_event_bus.emit.assert_any_call(
            "executive.goal_reviewed", ANY
        )
        mock_event_bus.emit.assert_any_call(
            "executive.task_generated", ANY
        )

    @pytest.mark.asyncio
    async def test_plan_dispatches_to_registered_agent(self, planner, mock_goal_manager,
                                                        mock_task_manager, mock_agent_manager,
                                                        mock_event_bus):
        mock_goal_manager.list_goals.return_value = [
            {"id": "g1", "title": "Build feature", "status": "active", "priority": 3, "progress": 0},
        ]
        mock_agent_manager.get_runtime_agent.return_value = MagicMock()

        await planner.plan(user_id="00000000-0000-0000-0000-000000000001")

        mock_agent_manager.dispatch.assert_awaited_once()
        mock_event_bus.emit.assert_any_call(
            "executive.task_assigned", ANY
        )

    @pytest.mark.asyncio
    async def test_plan_skips_dispatch_when_no_agent_registered(self, planner, mock_goal_manager,
                                                                  mock_task_manager, mock_agent_manager):
        mock_goal_manager.list_goals.return_value = [
            {"id": "g1", "title": "Build feature", "status": "active", "priority": 3, "progress": 0},
        ]
        mock_agent_manager.get_runtime_agent.return_value = None

        await planner.plan(user_id="00000000-0000-0000-0000-000000000001")

        mock_agent_manager.dispatch.assert_not_called()

    @pytest.mark.asyncio
    async def test_plan_honors_max_tasks(self, planner, mock_goal_manager, mock_task_manager):
        mock_goal_manager.list_goals.return_value = [
            {"id": f"g{i}", "title": f"Goal {i}", "status": "active", "priority": 3, "progress": 0}
            for i in range(10)
        ]

        output = await planner.plan(
            user_id="00000000-0000-0000-0000-000000000001",
            max_tasks=2,
        )

        assert mock_task_manager.create_task.call_count == 2
        assert any("max_tasks" in obs for obs in output.observations)

    @pytest.mark.asyncio
    async def test_review_does_not_create_tasks(self, planner, mock_goal_manager, mock_task_manager):
        mock_goal_manager.list_goals.return_value = [
            {"id": "g1", "title": "Build feature", "status": "active", "priority": 3, "progress": 0},
        ]

        output = await planner.review(user_id="00000000-0000-0000-0000-000000000001")

        mock_task_manager.create_task.assert_not_called()
        assert len(output.suggested_tasks) > 0

    @pytest.mark.asyncio
    async def test_strategy_setter(self, planner):
        new_strategy = _TestStrategy()
        planner.strategy = new_strategy
        assert planner.strategy is new_strategy

    @pytest.mark.asyncio
    async def test_custom_strategy_is_used(self, planner, mock_goal_manager):
        custom_output = PlanningOutput(
            reviewed_goal_ids=["g1"],
            suggested_tasks=[SuggestedTask(goal_id="g1", goal_title="Custom", title="Custom task")],
        )
        custom_strategy = _TestStrategy(custom_output)
        planner.strategy = custom_strategy

        mock_goal_manager.list_goals.return_value = [
            {"id": "g1", "title": "Custom goal", "status": "active", "priority": 3, "progress": 0},
        ]

        output = await planner.plan(user_id="00000000-0000-0000-0000-000000000001", max_tasks=0)

        assert output.suggested_tasks[0].title == "Custom task"

    @pytest.mark.asyncio
    async def test_plan_passes_goals_and_tasks_to_strategy(self, planner, mock_goal_manager, mock_task_manager):
        mock_goal_manager.list_goals.return_value = [
            {"id": "g1", "title": "Goal", "status": "active", "priority": 3, "progress": 0},
        ]
        mock_task_manager.list_tasks.return_value = [
            {"id": "t1", "goal_id": "g1", "status": "CREATED"},
        ]

        test_strategy = _TestStrategy()
        planner.strategy = test_strategy

        await planner.plan(user_id="00000000-0000-0000-0000-000000000001")

        assert test_strategy.analyze.await_count == 1

    @pytest.mark.asyncio
    async def test_plan_emits_goal_reviewed_event(self, planner, mock_goal_manager, mock_event_bus):
        mock_goal_manager.list_goals.return_value = [
            {"id": "g1", "title": "Goal", "status": "active", "priority": 3, "progress": 0},
        ]

        await planner.plan(user_id="00000000-0000-0000-0000-000000000001")

        mock_event_bus.emit.assert_any_call(
            "executive.goal_reviewed", ANY
        )

    @pytest.mark.asyncio
    async def test_plan_emits_task_generated_event(self, planner, mock_goal_manager,
                                                    mock_task_manager, mock_event_bus):
        mock_goal_manager.list_goals.return_value = [
            {"id": "g1", "title": "Goal", "status": "active", "priority": 3, "progress": 0},
        ]
        mock_task_manager.create_task.return_value = {"id": "t1", "goal": "test"}

        await planner.plan(user_id="00000000-0000-0000-0000-000000000001")

        mock_event_bus.emit.assert_any_call(
            "executive.task_generated", ANY
        )

    @pytest.mark.asyncio
    async def test_review_does_not_emit_task_events(self, planner, mock_goal_manager, mock_event_bus):
        mock_goal_manager.list_goals.return_value = [
            {"id": "g1", "title": "Goal", "status": "active", "priority": 3, "progress": 0},
        ]

        await planner.review(user_id="00000000-0000-0000-0000-000000000001")

        task_events = [c for c in mock_event_bus.emit.call_args_list
                       if c[0][0].startswith("executive.task")]
        assert len(task_events) == 0
