"""Tests for AutonomousReviewHandler."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.autonomy.autonomous_handler import AutonomousReviewHandler
from app.autonomy.enums import AutonomyLevel
from app.command_center.schemas import ApprovalRequest
from app.scheduler.schemas import Job


def _make_goal(
    goal_id: Any = None,
    title: str = "Test Goal",
    priority: int = 3,
    progress: int = 0,
) -> MagicMock:
    goal = MagicMock()
    goal.id = goal_id or uuid4()
    goal.title = title
    goal.priority = priority
    goal.progress = progress
    return goal


def _make_approval(
    status: str = "approved",
    reason: str | None = None,
    approval_id: str = "approval-1",
) -> ApprovalRequest:
    return ApprovalRequest(
        id=approval_id,
        action_type="autonomous_task",
        description="Test",
        risk_level="medium",
        requester="nova-autonomous",
        status=status,
        reason=reason,
    )


def _make_handler(**overrides: Any) -> tuple[AutonomousReviewHandler, dict[str, Any]]:
    user_id = uuid4()
    goal_repo = AsyncMock()
    autonomy_manager = MagicMock()
    approvals_manager = MagicMock()
    activity_repo = AsyncMock()
    event_bus = MagicMock()
    event_bus.publish = AsyncMock()

    # Default: governor allows execution
    autonomy_manager.governor.can_execute.return_value = True
    autonomy_manager.governor.level = MagicMock(value="autonomous")

    # Default: approval approved
    approvals_manager.request.return_value = _make_approval(status="approved")

    # Default: no goals
    goal_repo.get_next_actions = AsyncMock(return_value=[])

    deps = {
        "goal_repository": goal_repo,
        "autonomy_manager": autonomy_manager,
        "approvals_manager": approvals_manager,
        "activity_repository": activity_repo,
        "event_bus": event_bus,
        "user_id": user_id,
        "max_goals_per_cycle": overrides.get("max_goals_per_cycle", 5),
    }
    deps.update({k: v for k, v in overrides.items() if k in deps})

    handler = AutonomousReviewHandler(**deps)
    return handler, {
        "goal_repo": goal_repo,
        "autonomy_manager": autonomy_manager,
        "approvals_manager": approvals_manager,
        "activity_repo": activity_repo,
        "event_bus": event_bus,
        "user_id": user_id,
    }


class TestAutonomousReviewHandler:
    """Tests for AutonomousReviewHandler."""

    @pytest.mark.asyncio
    async def test_processes_active_goals(self) -> None:
        """Handler processes active goals and returns executed count."""
        handler, deps = _make_handler()
        goal = _make_goal(title="Ship feature")
        deps["goal_repo"].get_next_actions = AsyncMock(return_value=[goal])

        job = Job(name="autonomous_cycle")
        result = await handler.handle(job)

        assert result["executed"] == 1
        assert result["skipped"] == 0
        assert result["blocked"] == 0
        assert result["failed"] == 0
        deps["approvals_manager"].request.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_blocked_goals(self) -> None:
        """Handler skips goals when approval is rejected."""
        handler, deps = _make_handler()
        goal = _make_goal(title="Risky action")
        deps["goal_repo"].get_next_actions = AsyncMock(return_value=[goal])
        deps["approvals_manager"].request.return_value = _make_approval(
            status="rejected", reason="too risky"
        )

        job = Job(name="autonomous_cycle")
        result = await handler.handle(job)

        assert result["executed"] == 0
        assert result["blocked"] == 1
        deps["activity_repo"].create.assert_called_once_with(
            user_id=deps["user_id"],
            action="reviewed",
            status="blocked",
            goal_id=goal.id,
            goal_title=goal.title,
            goal_priority=goal.priority,
            approval_id="approval-1",
            reason="too risky",
        )

    @pytest.mark.asyncio
    async def test_respects_autonomy_level_too_low(self) -> None:
        """Handler skips goals when autonomy level is too low."""
        handler, deps = _make_handler()
        deps["autonomy_manager"].governor.can_execute.return_value = False
        deps["autonomy_manager"].governor.level = MagicMock(value="manual")
        goal = _make_goal(title="Manual only")
        deps["goal_repo"].get_next_actions = AsyncMock(return_value=[goal])

        job = Job(name="autonomous_cycle")
        result = await handler.handle(job)

        assert result["executed"] == 0
        assert result["skipped"] == 1
        deps["approvals_manager"].request.assert_not_called()
        deps["activity_repo"].create.assert_called_once_with(
            user_id=deps["user_id"],
            action="reviewed",
            status="skipped",
            goal_id=goal.id,
            goal_title=goal.title,
            goal_priority=goal.priority,
            reason="autonomy level too low",
            details={"autonomy_level": "manual"},
        )

    @pytest.mark.asyncio
    async def test_creates_approval_request(self) -> None:
        """Handler creates an approval request for each goal."""
        handler, deps = _make_handler()
        goal = _make_goal(title="Needs approval")
        deps["goal_repo"].get_next_actions = AsyncMock(return_value=[goal])
        deps["approvals_manager"].request.return_value = _make_approval(
            status="pending"
        )

        job = Job(name="autonomous_cycle")
        await handler.handle(job)

        deps["approvals_manager"].request.assert_called_once_with(
            action_type="autonomous_task",
            description="Autonomous execution of goal: Needs approval",
            risk_level="medium",
            requester="nova-autonomous",
            metadata={"goal_id": str(goal.id), "goal_title": "Needs approval"},
        )

    @pytest.mark.asyncio
    async def test_logs_activity_for_each_goal(self) -> None:
        """Handler logs an activity entry for every goal processed."""
        handler, deps = _make_handler()
        goals = [_make_goal(title=f"Goal {i}") for i in range(3)]
        deps["goal_repo"].get_next_actions = AsyncMock(return_value=goals)

        job = Job(name="autonomous_cycle")
        result = await handler.handle(job)

        # 3 executed goals = 3 activity logs
        assert deps["activity_repo"].create.call_count == 3
        assert result["executed"] == 3

    @pytest.mark.asyncio
    async def test_handles_execution_failure_gracefully(self) -> None:
        """Handler marks goal as failed when execution throws."""
        handler, deps = _make_handler()
        goal = _make_goal(title="Failing goal")
        deps["goal_repo"].get_next_actions = AsyncMock(return_value=[goal])
        deps["approvals_manager"].request.return_value = _make_approval(
            status="approved"
        )
        # Make begin_action raise to trigger the failure path
        deps["autonomy_manager"].governor.begin_action.side_effect = RuntimeError(
            "executor crashed"
        )

        job = Job(name="autonomous_cycle")
        result = await handler.handle(job)

        assert result["failed"] == 1
        assert result["executed"] == 0
        deps["activity_repo"].create.assert_called_once_with(
            user_id=deps["user_id"],
            action="executed",
            status="failed",
            goal_id=goal.id,
            goal_title=goal.title,
            goal_priority=goal.priority,
            reason="Execution failed",
        )

    @pytest.mark.asyncio
    async def test_max_goals_limit_is_respected(self) -> None:
        """Handler passes max_goals_per_cycle to get_next_actions."""
        handler, deps = _make_handler(max_goals_per_cycle=10)
        deps["goal_repo"].get_next_actions = AsyncMock(return_value=[])

        job = Job(name="autonomous_cycle")
        await handler.handle(job)

        deps["goal_repo"].get_next_actions.assert_called_once_with(
            deps["user_id"], limit=10
        )

    @pytest.mark.asyncio
    async def test_no_goals_returns_skipped(self) -> None:
        """Handler returns skipped=1 when no active goals exist."""
        handler, deps = _make_handler()
        deps["goal_repo"].get_next_actions = AsyncMock(return_value=[])

        job = Job(name="autonomous_cycle")
        result = await handler.handle(job)

        assert result == {"executed": 0, "skipped": 1, "blocked": 0, "failed": 0}
        deps["activity_repo"].create.assert_called_once_with(
            user_id=deps["user_id"],
            action="reviewed",
            status="skipped",
            reason="no active goals",
        )

    @pytest.mark.asyncio
    async def test_goal_fetch_failure_returns_failed(self) -> None:
        """Handler returns failed=1 when goal fetching throws."""
        handler, deps = _make_handler()
        deps["goal_repo"].get_next_actions = AsyncMock(
            side_effect=RuntimeError("db down")
        )

        job = Job(name="autonomous_cycle")
        result = await handler.handle(job)

        assert result == {"executed": 0, "skipped": 0, "blocked": 0, "failed": 1}
        deps["activity_repo"].create.assert_called_once_with(
            user_id=deps["user_id"],
            action="reviewed",
            status="failed",
            reason="Failed to fetch goals",
        )

    @pytest.mark.asyncio
    async def test_pending_approval_returns_blocked(self) -> None:
        """Handler blocks goals when approval is pending."""
        handler, deps = _make_handler()
        goal = _make_goal(title="Pending goal")
        deps["goal_repo"].get_next_actions = AsyncMock(return_value=[goal])
        deps["approvals_manager"].request.return_value = _make_approval(
            status="pending"
        )

        job = Job(name="autonomous_cycle")
        result = await handler.handle(job)

        assert result["blocked"] == 1
        deps["activity_repo"].create.assert_called_once_with(
            user_id=deps["user_id"],
            action="reviewed",
            status="blocked",
            goal_id=goal.id,
            goal_title=goal.title,
            goal_priority=goal.priority,
            approval_id="approval-1",
            reason="approval required",
        )

    @pytest.mark.asyncio
    async def test_mixed_goals_summary(self) -> None:
        """Handler correctly counts executed, skipped, and blocked goals."""
        handler, deps = _make_handler()
        goal_exec = _make_goal(title="Executed")
        goal_skip = _make_goal(title="Skipped")
        goal_block = _make_goal(title="Blocked")
        deps["goal_repo"].get_next_actions = AsyncMock(
            return_value=[goal_exec, goal_skip, goal_block]
        )

        # First call: approved, second: autonomy too low, third: rejected
        call_count = 0

        def side_effect(**kwargs: Any) -> ApprovalRequest:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_approval(status="approved")
            if call_count == 2:
                return _make_approval(status="rejected")
            return _make_approval(status="approved")

        deps["approvals_manager"].request.side_effect = side_effect

        # Second goal: autonomy blocks it
        can_execute_calls = [True, False, True]
        deps["autonomy_manager"].governor.can_execute.side_effect = can_execute_calls

        job = Job(name="autonomous_cycle")
        result = await handler.handle(job)

        assert result["executed"] == 1
        assert result["skipped"] == 1
        assert result["blocked"] == 1
