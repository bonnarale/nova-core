"""Workflow state machine — allowed transitions for workflows and steps."""

from __future__ import annotations

from app.workflows.models import StepStatus, WorkflowStatus


class WorkflowStateMachine:
    """Validates and applies state transitions for workflow executions."""

    _WORKFLOW_TRANSITIONS: dict[WorkflowStatus, set[WorkflowStatus]] = {
        WorkflowStatus.PENDING: {WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED},
        WorkflowStatus.RUNNING: {
            WorkflowStatus.PAUSED,
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
            WorkflowStatus.ROLLING_BACK,
        },
        WorkflowStatus.PAUSED: {WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED},
        WorkflowStatus.ROLLING_BACK: {WorkflowStatus.ROLLED_BACK, WorkflowStatus.FAILED},
        WorkflowStatus.COMPLETED: set(),
        WorkflowStatus.FAILED: {WorkflowStatus.RUNNING},
        WorkflowStatus.CANCELLED: set(),
        WorkflowStatus.ROLLED_BACK: set(),
    }

    _STEP_TRANSITIONS: dict[StepStatus, set[StepStatus]] = {
        StepStatus.PENDING: {StepStatus.RUNNING, StepStatus.SKIPPED},
        StepStatus.RUNNING: {
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.RETRYING,
            StepStatus.ROLLING_BACK,
        },
        StepStatus.COMPLETED: set(),
        StepStatus.FAILED: {StepStatus.RETRYING, StepStatus.ROLLING_BACK},
        StepStatus.SKIPPED: set(),
        StepStatus.RETRYING: {StepStatus.RUNNING, StepStatus.FAILED},
        StepStatus.ROLLING_BACK: {StepStatus.ROLLED_BACK, StepStatus.FAILED},
        StepStatus.ROLLED_BACK: set(),
    }

    @classmethod
    def can_transition_workflow(
        cls, current: WorkflowStatus, target: WorkflowStatus
    ) -> bool:
        allowed = cls._WORKFLOW_TRANSITIONS.get(current, set())
        return target in allowed

    @classmethod
    def can_transition_step(cls, current: StepStatus, target: StepStatus) -> bool:
        allowed = cls._STEP_TRANSITIONS.get(current, set())
        return target in allowed

    @classmethod
    def assert_can_transition_workflow(
        cls, current: WorkflowStatus, target: WorkflowStatus
    ) -> None:
        if not cls.can_transition_workflow(current, target):
            raise ValueError(
                f"Cannot transition workflow from {current.value} to {target.value}"
            )

    @classmethod
    def assert_can_transition_step(
        cls, current: StepStatus, target: StepStatus
    ) -> None:
        if not cls.can_transition_step(current, target):
            raise ValueError(
                f"Cannot transition step from {current.value} to {target.value}"
            )

    @classmethod
    def list_workflow_transitions(cls, status: WorkflowStatus) -> list[str]:
        return [s.value for s in cls._WORKFLOW_TRANSITIONS.get(status, set())]

    @classmethod
    def list_step_transitions(cls, status: StepStatus) -> list[str]:
        return [s.value for s in cls._STEP_TRANSITIONS.get(status, set())]
