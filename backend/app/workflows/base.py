"""Abstract base classes for the Workflow Engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

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


class WorkflowProvider(ABC):
    """Provider interface for the workflow engine."""

    @abstractmethod
    async def initialize(self) -> None:
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        ...

    @abstractmethod
    async def create(self, definition: dict[str, Any]) -> Any:
        ...

    @abstractmethod
    async def execute(self, workflow_id: str, input_data: dict[str, Any] | None = None) -> Any:
        ...


class WorkflowRepositoryABC(ABC):
    """Repository interface for workflow persistence."""

    @abstractmethod
    async def save_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        ...

    @abstractmethod
    async def get_definition(self, workflow_id: str) -> WorkflowDefinition | None:
        ...

    @abstractmethod
    async def list_definitions(self, tag: str | None = None, limit: int = 100, offset: int = 0) -> list[WorkflowDefinition]:
        ...

    @abstractmethod
    async def delete_definition(self, workflow_id: str) -> bool:
        ...

    @abstractmethod
    async def save_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        ...

    @abstractmethod
    async def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        ...

    @abstractmethod
    async def list_executions(self, workflow_id: str | None = None, status: str | None = None, limit: int = 100, offset: int = 0) -> list[WorkflowExecution]:
        ...

    @abstractmethod
    async def delete_execution(self, execution_id: str) -> bool:
        ...


class WorkflowCompilerABC(ABC):
    """Compiler interface for workflow compilation."""

    @abstractmethod
    def compile(self, definition: WorkflowDefinition) -> Any:
        ...

    @abstractmethod
    def validate(self, definition: WorkflowDefinition) -> tuple[bool, list[str]]:
        ...


class WorkflowValidatorABC(ABC):
    """Validator interface for workflow validation."""

    @abstractmethod
    def validate_definition(self, definition: dict[str, Any]) -> tuple[bool, list[str]]:
        ...

    @abstractmethod
    def validate_graph(self, graph: Any) -> tuple[bool, list[str]]:
        ...


class WorkflowDispatcherABC(ABC):
    """Dispatcher interface for workflow node dispatch."""

    @abstractmethod
    async def dispatch(self, node: Any, context: Any) -> Any:
        ...

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...
