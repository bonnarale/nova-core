"""Fluent builder for constructing WorkflowDefinition objects."""

from __future__ import annotations

from typing import Any

from app.workflows.models import (
    Condition,
    ConditionStep,
    LoopStep,
    ParallelBranch,
    ParallelStep,
    RetryPolicy,
    StepType,
    TimeoutPolicy,
    WorkflowDefinition,
    WorkflowStep,
)


class WorkflowBuilder:
    """Fluent builder for constructing WorkflowDefinition instances."""

    def __init__(self, name: str = "") -> None:
        self._definition = WorkflowDefinition(name=name)

    def with_description(self, description: str) -> WorkflowBuilder:
        self._definition.description = description
        return self

    def with_version(self, version: str) -> WorkflowBuilder:
        self._definition.version = version
        return self

    def with_id(self, wf_id: str) -> WorkflowBuilder:
        self._definition.id = wf_id
        return self

    def with_input_schema(self, schema: dict[str, Any]) -> WorkflowBuilder:
        self._definition.input_schema = schema
        return self

    def with_output_schema(self, schema: dict[str, Any]) -> WorkflowBuilder:
        self._definition.output_schema = schema
        return self

    def with_timeout(self, step_timeout: float = 300.0, workflow_timeout: float = 86400.0) -> WorkflowBuilder:
        self._definition.timeout_policy = TimeoutPolicy(
            step_timeout_seconds=step_timeout,
            workflow_timeout_seconds=workflow_timeout,
        )
        return self

    def with_tags(self, *tags: str) -> WorkflowBuilder:
        self._definition.tags = list(tags)
        return self

    def add_step(self, step: WorkflowStep) -> WorkflowBuilder:
        self._definition.steps.append(step)
        return self

    def task_step(
        self,
        step_id: str,
        name: str,
        handler: str,
        config: dict[str, Any] | None = None,
        depends_on: list[str] | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> WorkflowBuilder:
        step = WorkflowStep(
            id=step_id,
            name=name,
            step_type=StepType.TASK,
            handler=handler,
            config=config or {},
            depends_on=depends_on or [],
            retry_policy=retry_policy,
        )
        return self.add_step(step)

    def condition_step(
        self,
        step_id: str,
        name: str,
        conditions: list[Condition],
        if_branch: list[WorkflowStep] | None = None,
        else_branch: list[WorkflowStep] | None = None,
    ) -> WorkflowBuilder:
        step = ConditionStep(
            id=step_id,
            name=name,
            step_type=StepType.CONDITION,
            conditions=conditions,
            if_branch=if_branch or [],
            else_branch=else_branch or [],
        )
        return self.add_step(step)

    def parallel_step(
        self,
        step_id: str,
        name: str,
        branches: list[ParallelBranch],
    ) -> WorkflowBuilder:
        step = ParallelStep(
            id=step_id,
            name=name,
            step_type=StepType.PARALLEL,
            branches=branches,
        )
        return self.add_step(step)

    def loop_step(
        self,
        step_id: str,
        name: str,
        loop_over: str,
        body: list[WorkflowStep],
        max_iterations: int = 10,
        convergence_condition: Condition | None = None,
    ) -> WorkflowBuilder:
        step = LoopStep(
            id=step_id,
            name=name,
            step_type=StepType.LOOP,
            loop_over=loop_over,
            body=body,
            max_iterations=max_iterations,
            convergence_condition=convergence_condition,
        )
        return self.add_step(step)

    def build(self) -> WorkflowDefinition:
        if not self._definition.id:
            import uuid
            self._definition.id = str(uuid.uuid4())
        return self._definition
