"""ReplanStrategy — modifies a Plan when steps fail or conditions change."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.planner.plan import Plan, PlanStatus, Step, StepStatus

logger = logging.getLogger(__name__)


class ReplanStrategy(ABC):
    """Abstract strategy for modifying a plan when a step fails."""

    @abstractmethod
    async def replan(
        self,
        plan: Plan,
        failed_step: Step,
        error: str,
        context: dict[str, Any] | None = None,
    ) -> Plan:
        """Modify and return the plan (or a new plan) to recover from failure."""
        ...


class BasicReplanStrategy(ReplanStrategy):
    """Simple replanning strategy.

    - If there's a fallback step, insert it after the failed step.
    - Otherwise, mark downstream steps as BLOCKED and the plan as FAILED.
    """

    _FALLBACK_ACTIONS: dict[str, str] = {
        "planner": "Re-evaluate the objective and create a new approach",
        "researcher": "Gather more information before retrying",
        "coder": "Review and fix the implementation",
        "reviewer": "Perform a detailed review to identify issues",
        "executor": "Check environment and try alternative approach",
        "memory": "Retrieve context from past similar tasks",
    }

    async def replan(
        self,
        plan: Plan,
        failed_step: Step,
        error: str,
        context: dict[str, Any] | None = None,
    ) -> Plan:
        agent = failed_step.assigned_agent or "executor"
        fallback_desc = self._FALLBACK_ACTIONS.get(agent, "Try a different approach")

        title = f"Fallback: {failed_step.title}"
        description = f"{fallback_desc} (original error: {error})"

        fallback_step = Step(
            title=title,
            description=description,
            assigned_agent=agent,
            dependencies=[sid for sid in [s.id for s in plan.steps if s.status == StepStatus.SUCCEEDED]],
            metadata={"source": "replanner", "original_step_id": failed_step.id},
        )

        # Insert fallback after the failed step
        failed_index = next(
            (i for i, s in enumerate(plan.steps) if s.id == failed_step.id),
            len(plan.steps) - 1,
        )
        plan.steps.insert(failed_index + 1, fallback_step)

        # Mark remaining downstream steps as BLOCKED (they'll need the fallback to succeed)
        for s in plan.steps[failed_index + 2 :]:
            if s.status not in (StepStatus.SUCCEEDED, StepStatus.FAILED):
                s.status = StepStatus.BLOCKED

        plan.updated_at = __import__("datetime").datetime.now(
            tz=__import__("datetime").timezone.utc
        ).isoformat()

        logger.info(
            "Replanned: inserted fallback step '%s' for failed step '%s'",
            fallback_step.title, failed_step.title,
        )
        return plan
