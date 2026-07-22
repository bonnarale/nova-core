"""Abstract base classes for the Workflow Engine."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.workflows.models import WorkflowDefinition, WorkflowExecution, WorkflowStep, WorkflowStepExecution


class WorkflowExecutor(ABC):
    """Executes a workflow definition, producing an execution result."""

    @abstractmethod
    async def execute(
        self,
        definition: WorkflowDefinition,
        execution: WorkflowExecution,
    ) -> WorkflowExecution:
        ...


class StepHandler(ABC):
    """Handles execution of a single workflow step."""

    @property
    @abstractmethod
    def handler_name(self) -> str:
        ...

    @abstractmethod
    async def can_handle(self, step: WorkflowStep) -> bool:
        ...

    @abstractmethod
    async def execute(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
        context: dict,
    ) -> WorkflowStepExecution:
        ...

    @abstractmethod
    async def rollback(
        self,
        step: WorkflowStep,
        step_execution: WorkflowStepExecution,
    ) -> None:
        ...


class ConditionEvaluator(ABC):
    """Evaluates conditions for conditional branching."""

    @abstractmethod
    async def evaluate(
        self,
        condition: dict,
        context: dict,
    ) -> bool:
        ...


class RollbackHandler(ABC):
    """Handles rollback of a workflow execution."""

    @abstractmethod
    async def rollback(
        self,
        execution: WorkflowExecution,
        definition: WorkflowDefinition,
    ) -> WorkflowExecution:
        ...
