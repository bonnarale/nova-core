"""Execution strategies for workflow steps — sequential, parallel, conditional, loop."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.workflows.base import ConditionEvaluator, StepHandler
from app.workflows.models import (
    ConditionStep,
    LoopStep,
    ParallelStep,
    StepStatus,
    StepType,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepExecution,
)
from app.workflows.state_machine import WorkflowStateMachine

logger = logging.getLogger(__name__)


class SequentialExecutor:
    """Executes steps sequentially with dependency resolution."""

    def __init__(
        self,
        step_handlers: dict[str, StepHandler],
        condition_evaluator: ConditionEvaluator,
    ) -> None:
        self._handlers = step_handlers
        self._condition_evaluator = condition_evaluator

    async def execute(
        self,
        definition: WorkflowDefinition,
        execution: WorkflowExecution,
    ) -> WorkflowExecution:
        sorted_steps = self._topological_sort(definition.steps)

        for step in sorted_steps:
            if execution.status != WorkflowStatus.RUNNING:
                break

            if not await self._dependencies_met(step, execution):
                continue

            step_exec = await self._execute_step(step, execution)

            execution.step_executions.append(step_exec)
            execution.current_step_id = step.id

            if step_exec.status == StepStatus.FAILED:
                execution.error = step_exec.error
                break

        return execution

    async def _execute_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
    ) -> WorkflowStepExecution:
        step_exec = WorkflowStepExecution(
            step_id=step.id,
            step_name=step.name,
            step_type=step.step_type,
        )

        WorkflowStateMachine.assert_can_transition_step(
            step_exec.status, StepStatus.RUNNING
        )
        step_exec.status = StepStatus.RUNNING
        step_exec.started_at = datetime.now(timezone.utc).isoformat()

        try:
            context = self._build_context(step, execution)

            if step.step_type == StepType.CONDITION:
                result = await self._execute_condition(step, context)
            elif step.step_type == StepType.PARALLEL:
                result = await self._execute_parallel(step, context)
            elif step.step_type == StepType.LOOP:
                result = await self._execute_loop(step, context)
            else:
                result = await self._execute_handler_step(step, context)

            step_exec.output = result
            step_exec.status = StepStatus.COMPLETED

        except Exception as exc:
            logger.exception("Step %s failed: %s", step.id, exc)
            step_exec.error = str(exc)
            step_exec.status = StepStatus.FAILED

        step_exec.completed_at = datetime.now(timezone.utc).isoformat()
        return step_exec

    async def _execute_handler_step(
        self,
        step: WorkflowStep,
        context: dict,
    ) -> dict[str, Any]:
        handler = self._handlers.get(step.handler)
        if handler is None:
            raise ValueError(f"No handler registered for '{step.handler}'")
        step_exec = await handler.execute(step, WorkflowExecution(), context)
        return step_exec.output

    async def _execute_condition(
        self,
        step: ConditionStep,
        context: dict,
    ) -> dict[str, Any]:
        for condition in step.conditions:
            result = await self._condition_evaluator.evaluate(
                {"field": condition.field, "operator": condition.operator, "value": condition.value},
                context,
            )
            if result:
                return {"branch": "if", "result": True}
        return {"branch": "else", "result": False}

    async def _execute_parallel(
        self,
        step: ParallelStep,
        context: dict,
    ) -> dict[str, Any]:
        async def run_branch(branch):
            results = []
            for s in branch.steps:
                r = await self._execute_step(s, WorkflowExecution())
                results.append(r.to_dict())
            return {"branch_id": branch.id, "results": results}

        tasks = [run_branch(b) for b in step.branches]
        branch_results = await asyncio.gather(*tasks, return_exceptions=True)
        return {"branches": [r if not isinstance(r, Exception) else {"error": str(r)} for r in branch_results]}

    async def _execute_loop(
        self,
        step: LoopStep,
        context: dict,
    ) -> dict[str, Any]:
        iterations = []
        for i in range(step.max_iterations):
            iteration_results = []
            for s in step.body:
                r = await self._execute_step(s, WorkflowExecution())
                iteration_results.append(r.to_dict())
            iterations.append({"iteration": i, "results": iteration_results})

            if step.convergence_condition:
                eval_context = {"iteration": i, "results": iteration_results, **context}
                converged = await self._condition_evaluator.evaluate(
                    {"field": step.convergence_condition.field, "operator": step.convergence_condition.operator, "value": step.convergence_condition.value},
                    eval_context,
                )
                if converged:
                    break

        return {"iterations": len(iterations), "results": iterations}

    def _build_context(self, step: WorkflowStep, execution: WorkflowExecution) -> dict:
        context: dict = {"input": execution.input}
        for se in execution.step_executions:
            context[se.step_id] = se.output
        return context

    def _topological_sort(self, steps: list[WorkflowStep]) -> list[WorkflowStep]:
        step_map = {s.id: s for s in steps}
        visited: set[str] = set()
        result: list[WorkflowStep] = []

        def visit(step_id: str) -> None:
            if step_id in visited:
                return
            visited.add(step_id)
            step = step_map.get(step_id)
            if step:
                for dep in step.depends_on:
                    visit(dep)
                result.append(step)

        for s in steps:
            visit(s.id)

        return result

    async def _dependencies_met(
        self, step: WorkflowStep, execution: WorkflowExecution
    ) -> bool:
        completed_ids = {se.step_id for se in execution.step_executions if se.status == StepStatus.COMPLETED}
        return all(dep in completed_ids for dep in step.depends_on)
