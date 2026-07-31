"""Autonomous review handler — reviews goals and executes pending autonomous actions."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.autonomy.enums import AutonomyLevel
from app.autonomy.manager import AutonomyManager
from app.command_center.approvals import ApprovalsManager
from app.db.activity_log_repository import ActivityLogRepository
from app.db.goal_repository import GoalRepository
from app.events import Event
from app.events.bus import InMemoryEventBus
from app.scheduler.schemas import Job

logger = logging.getLogger(__name__)

# Autonomy levels that permit autonomous execution
_AUTONOMOUS_LEVELS = {AutonomyLevel.AUTONOMOUS, AutonomyLevel.FULL}


class AutonomousReviewHandler:
    """Reviews active goals and executes pending autonomous actions.

    Enforces dual gating: AutonomyManager level check + approval gate.
    Each goal reviewed produces one ActivityLog entry.
    """

    def __init__(
        self,
        goal_repository: GoalRepository,
        autonomy_manager: AutonomyManager,
        approvals_manager: ApprovalsManager,
        activity_repository: ActivityLogRepository,
        event_bus: InMemoryEventBus,
        user_id: UUID,
        max_goals_per_cycle: int = 5,
    ) -> None:
        self._goal_repo = goal_repository
        self._autonomy_manager = autonomy_manager
        self._approvals_manager = approvals_manager
        self._activity_repo = activity_repository
        self._event_bus = event_bus
        self._user_id = user_id
        self._max_goals = max_goals_per_cycle

    async def handle(self, job: Job) -> dict[str, Any]:
        """Review goals and execute pending autonomous actions.

        Returns a cycle summary with counts of executed, skipped, blocked, and failed goals.
        """
        logger.info("Autonomous cycle started for user %s", self._user_id)

        try:
            goals = await self._goal_repo.get_next_actions(
                self._user_id, limit=self._max_goals
            )
        except Exception as exc:
            # Log full exception server-side only — never expose to clients
            logger.error("Failed to fetch goals: %s", exc, exc_info=True)
            await self._activity_repo.create(
                user_id=self._user_id,
                action="reviewed",
                status="failed",
                reason="Failed to fetch goals",
            )
            return {"executed": 0, "skipped": 0, "blocked": 0, "failed": 1}

        if not goals:
            logger.info("No active goals found — skipping cycle")
            await self._activity_repo.create(
                user_id=self._user_id,
                action="reviewed",
                status="skipped",
                reason="no active goals",
            )
            return {"executed": 0, "skipped": 1, "blocked": 0, "failed": 0}

        summary = {"executed": 0, "skipped": 0, "blocked": 0, "failed": 0}

        for goal in goals:
            try:
                result = await self._process_goal(goal)
                summary[result] += 1
            except Exception as exc:
                # Log full exception server-side only — never expose to clients
                logger.error("Goal %s processing failed: %s", goal.id, exc, exc_info=True)
                summary["failed"] += 1
                await self._activity_repo.create(
                    user_id=self._user_id,
                    action="reviewed",
                    status="failed",
                    goal_id=goal.id,
                    goal_title=goal.title,
                    goal_priority=goal.priority,
                    reason="Execution failed",
                )

        logger.info("Autonomous cycle completed: %s", summary)
        return summary

    async def _process_goal(self, goal: Any) -> str:
        """Process a single goal through dual gating.

        Returns one of: 'executed', 'skipped', 'blocked'.
        """
        # Gate 1: AutonomyManager level check
        if not self._autonomy_manager.governor.can_execute():
            logger.debug(
                "Goal %s skipped: autonomy level too low (%s)",
                goal.id,
                self._autonomy_manager.governor.level.value,
            )
            await self._activity_repo.create(
                user_id=self._user_id,
                action="reviewed",
                status="skipped",
                goal_id=goal.id,
                goal_title=goal.title,
                goal_priority=goal.priority,
                reason="autonomy level too low",
                details={"autonomy_level": self._autonomy_manager.governor.level.value},
            )
            return "skipped"

        # Gate 2: Approval check
        approval = self._approvals_manager.request(
            action_type="autonomous_task",
            description=f"Autonomous execution of goal: {goal.title}",
            risk_level="medium",
            requester="nova-autonomous",
            metadata={"goal_id": str(goal.id), "goal_title": goal.title},
        )

        if approval.status == "rejected":
            logger.debug("Goal %s blocked: approval rejected (%s)", goal.id, approval.reason)
            await self._activity_repo.create(
                user_id=self._user_id,
                action="reviewed",
                status="blocked",
                goal_id=goal.id,
                goal_title=goal.title,
                goal_priority=goal.priority,
                approval_id=approval.id,
                reason=approval.reason or "approval rejected",
            )
            return "blocked"

        if approval.status == "pending":
            logger.debug("Goal %s blocked: approval pending", goal.id)
            await self._activity_repo.create(
                user_id=self._user_id,
                action="reviewed",
                status="blocked",
                goal_id=goal.id,
                goal_title=goal.title,
                goal_priority=goal.priority,
                approval_id=approval.id,
                reason="approval required",
            )
            return "blocked"

        # Execute the action
        try:
            self._autonomy_manager.governor.begin_action()
            try:
                result = await self._execute_goal_action(goal)
                self._autonomy_manager.governor.end_action()

                await self._activity_repo.create(
                    user_id=self._user_id,
                    action="executed",
                    status="executed",
                    goal_id=goal.id,
                    goal_title=goal.title,
                    goal_priority=goal.priority,
                    details={"result": result},
                )

                await self._publish_event(
                    event_type="autonomous.action.completed",
                    goal=goal,
                    status="executed",
                )
                return "executed"
            except Exception as exc:
                self._autonomy_manager.governor.end_action()
                raise exc
        except Exception as exc:
            # Log full exception server-side only — never expose to clients
            logger.error("Goal %s execution failed: %s", goal.id, exc, exc_info=True)
            await self._activity_repo.create(
                user_id=self._user_id,
                action="executed",
                status="failed",
                goal_id=goal.id,
                goal_title=goal.title,
                goal_priority=goal.priority,
                reason="Execution failed",
            )
            await self._publish_event(
                event_type="autonomous.action.failed",
                goal=goal,
                status="failed",
                error="Execution failed",
            )
            return "failed"

    async def _execute_goal_action(self, goal: Any) -> dict[str, Any]:
        """Execute the action for a goal.

        This is a placeholder for actual goal execution logic.
        In the current implementation, it records the review and returns a summary.
        """
        return {
            "goal_id": str(goal.id),
            "title": goal.title,
            "action": "reviewed",
            "progress": goal.progress,
        }

    async def _publish_event(
        self,
        event_type: str,
        goal: Any,
        status: str,
        error: str | None = None,
    ) -> None:
        """Publish an event to the EventBus."""
        try:
            event = Event(
                event_type=event_type,
                aggregate_id=str(goal.id),
                aggregate_type="goal",
                source="autonomous-handler",
                user_id=str(self._user_id),
                payload={
                    "goal_id": str(goal.id),
                    "goal_title": goal.title,
                    "status": status,
                    "error": error,
                },
            )
            await self._event_bus.publish(event)
        except Exception as exc:
            logger.warning("Failed to publish event %s: %s", event_type, exc)
