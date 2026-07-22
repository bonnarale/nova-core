"""AutonomousPlanner — orchestrator that decomposes objectives into executable
plans, executes steps, reviews results, and replans when necessary.

Flow:
  Objective → decompose → Plan → for each ready Step → execute →
  review → (retry|replan|continue) → until complete or failed.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any
from uuid import UUID

from app.planner.executor import AgentStepExecutor, StepExecutor
from app.planner.plan import Plan, PlanStatus, Step, StepStatus
from app.planner.replanner import BasicReplanStrategy, ReplanStrategy
from app.planner.reviewer import ResultStepReviewer, ReviewVerdict, StepReviewer
from app.planner.strategy import PlanDecompositionStrategy, RuleBasedDecompositionStrategy

logger = logging.getLogger(__name__)


class Planner:
    """Autonomous planner — the main orchestrator.

    Dependencies are injected via the constructor (Strategy Pattern).

    Usage::

        planner = Planner(
            agent_manager=agent_manager,
            decomposition_strategy=RuleBasedDecompositionStrategy(),
            step_executor=AgentStepExecutor(agent_manager),
            step_reviewer=ResultStepReviewer(),
            replan_strategy=BasicReplanStrategy(),
        )
        plan = await planner.create_plan("Build a landing page")
        result = await planner.execute_plan(plan)
    """

    def __init__(
        self,
        agent_manager: Any,
        decomposition_strategy: PlanDecompositionStrategy | None = None,
        step_executor: StepExecutor | None = None,
        step_reviewer: StepReviewer | None = None,
        replan_strategy: ReplanStrategy | None = None,
        max_replans: int = 10,
    ) -> None:
        self._agent_manager = agent_manager
        self._decomposition_strategy = decomposition_strategy or RuleBasedDecompositionStrategy()
        self._step_executor = step_executor or AgentStepExecutor(agent_manager)
        self._step_reviewer = step_reviewer or ResultStepReviewer()
        self._replan_strategy = replan_strategy or BasicReplanStrategy()
        self._max_replans = max_replans

    @property
    def decomposition_strategy(self) -> PlanDecompositionStrategy:
        return self._decomposition_strategy

    @decomposition_strategy.setter
    def decomposition_strategy(self, s: PlanDecompositionStrategy) -> None:
        self._decomposition_strategy = s

    @property
    def step_executor(self) -> StepExecutor:
        return self._step_executor

    @step_executor.setter
    def step_executor(self, e: StepExecutor) -> None:
        self._step_executor = e

    @property
    def step_reviewer(self) -> StepReviewer:
        return self._step_reviewer

    @step_reviewer.setter
    def step_reviewer(self, r: StepReviewer) -> None:
        self._step_reviewer = r

    @property
    def replan_strategy(self) -> ReplanStrategy:
        return self._replan_strategy

    @replan_strategy.setter
    def replan_strategy(self, r: ReplanStrategy) -> None:
        self._replan_strategy = r

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_plan(
        self,
        objective: str,
        user_id: str | None = None,
        session_id: str | None = None,
        goal_id: str | None = None,
    ) -> Plan:
        """Decompose *objective* into a Plan with ordered Steps."""
        plan = await self._decomposition_strategy.decompose(objective, user_id=user_id)
        plan.user_id = user_id
        plan.session_id = session_id
        plan.goal_id = goal_id
        plan.status = PlanStatus.ACTIVE
        logger.info(
            "Created plan %s for objective '%s' with %d steps",
            plan.id, objective[:60], len(plan.steps),
        )
        return plan

    async def execute_plan(
        self,
        plan: Plan,
        context: dict[str, Any] | None = None,
    ) -> Plan:
        """Execute all steps in *plan* sequentially, with review and replan.

        Returns the updated plan with final status.
        """
        if plan.status not in (PlanStatus.DRAFT, PlanStatus.ACTIVE):
            logger.warning("Plan %s is %s — skipping execution", plan.id, plan.status)
            return plan

        ctx = dict(context or {})
        ctx["plan_id"] = plan.id
        ctx["objective"] = plan.objective

        plan.status = PlanStatus.ACTIVE
        history: list[dict[str, Any]] = []
        replan_count = 0

        while True:
            ready = plan.next_ready_steps
            if not ready:
                break

            for step in ready:
                step = await self._run_step(step, plan, ctx)
                history.append(self._step_to_history(step))

                if step.status == StepStatus.SUCCEEDED:
                    continue

                if step.status == StepStatus.FAILED:
                    replan_count += 1
                    if replan_count > self._max_replans:
                        logger.warning(
                            "Plan %s exceeded %d replans — stopping",
                            plan.id, self._max_replans,
                        )
                        plan.status = PlanStatus.FAILED
                        plan.error = f"Exceeded maximum replans ({self._max_replans})"
                        plan.updated_at = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
                        plan.metadata["history"] = history
                        return plan
                    plan = await self._replan_strategy.replan(plan, step, step.error or "Unknown", context=ctx)
                    plan.metadata["history"] = history
                    break

        # Determine final plan status
        all_done = all(
            s.status in (StepStatus.SUCCEEDED, StepStatus.SKIPPED)
            for s in plan.steps
        )
        any_failed = any(s.status == StepStatus.FAILED for s in plan.steps)
        any_running = any(s.status == StepStatus.RUNNING for s in plan.steps)

        if all_done:
            plan.status = PlanStatus.COMPLETED
            plan.completed_at = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
            logger.info("Plan %s completed successfully", plan.id)
        elif any_failed and not any_running:
            plan.status = PlanStatus.FAILED
            errors = [s.error for s in plan.steps if s.error]
            plan.error = "; ".join(errors) if errors else "Plan execution failed"
            logger.warning("Plan %s failed: %s", plan.id, plan.error)
        else:
            # Still some steps pending/running — keep ACTIVE
            pass

        plan.updated_at = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        plan.metadata["history"] = history
        return plan

    async def get_plan_status(self, plan: Plan) -> dict[str, Any]:
        """Return a summary of the plan's current state."""
        return {
            "plan_id": plan.id,
            "objective": plan.objective,
            "status": plan.status.value,
            "progress": plan.progress,
            "steps_total": len(plan.steps),
            "steps_completed": sum(
                1 for s in plan.steps if s.status == StepStatus.SUCCEEDED
            ),
            "steps_failed": sum(1 for s in plan.steps if s.status == StepStatus.FAILED),
            "active_step": plan.active_step.title if plan.active_step else None,
        }

    async def cancel_plan(self, plan: Plan) -> Plan:
        """Cancel an active plan."""
        if plan.status != PlanStatus.ACTIVE:
            logger.warning("Plan %s is not active — cannot cancel", plan.id)
            return plan
        plan.status = PlanStatus.CANCELLED
        for s in plan.steps:
            if s.status == StepStatus.RUNNING:
                s.status = StepStatus.SKIPPED
                s.error = "Plan cancelled"
        plan.updated_at = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        plan.completed_at = plan.updated_at
        logger.info("Plan %s cancelled", plan.id)
        return plan

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _run_step(
        self,
        step: Step,
        plan: Plan,
        context: dict[str, Any],
    ) -> Step:
        """Execute a single step with retry and review loop."""
        max_attempts = max(1, step.retry_policy.max_retries + 1)

        for attempt in range(max_attempts):
            if attempt > 0:
                delay = step.retry_policy.delay_seconds * (
                    step.retry_policy.backoff_multiplier ** (attempt - 1)
                )
                logger.info("Retrying step '%s' in %.1fs (attempt %d/%d)", step.title, delay, attempt + 1, max_attempts)
                await asyncio.sleep(delay)

            step = await self._step_executor.execute(step, context=context)
            review = await self._step_reviewer.review(step, plan_context=context)

            if review.verdict == ReviewVerdict.SUCCESS:
                return step
            if review.verdict == ReviewVerdict.RETRY:
                continue
            if review.verdict == ReviewVerdict.REPLAN:
                step.status = StepStatus.FAILED
                return step
            if review.verdict == ReviewVerdict.SKIP:
                step.status = StepStatus.SKIPPED
                return step
            if review.verdict == ReviewVerdict.FAIL:
                step.status = StepStatus.FAILED
                return step

        step.status = StepStatus.FAILED
        return step

    @staticmethod
    def _step_to_history(step: Step) -> dict[str, Any]:
        return {
            "step_id": step.id,
            "title": step.title,
            "status": step.status.value,
            "agent": step.assigned_agent,
            "error": step.error,
            "started_at": step.started_at,
            "completed_at": step.completed_at,
        }
