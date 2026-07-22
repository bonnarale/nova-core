"""Repository for workflow engine persistence — currently in-memory."""

from __future__ import annotations

from typing import Any

from app.workflows.models import WorkflowDefinition, WorkflowExecution


class WorkflowRepository:
    """Persistence interface for workflow definitions and executions.

    Currently in-memory; can be backed by a DB implementation.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, WorkflowDefinition] = {}
        self._executions: dict[str, WorkflowExecution] = {}

    # --- Definitions ---

    async def save_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        self._definitions[definition.id] = definition
        return definition

    async def get_definition(self, workflow_id: str) -> WorkflowDefinition | None:
        return self._definitions.get(workflow_id)

    async def list_definitions(
        self,
        tag: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkflowDefinition]:
        results = list(self._definitions.values())
        if tag:
            results = [w for w in results if tag in w.tags]
        return results[offset : offset + limit]

    async def delete_definition(self, workflow_id: str) -> bool:
        return self._definitions.pop(workflow_id, None) is not None

    # --- Executions ---

    async def save_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        self._executions[execution.id] = execution
        return execution

    async def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        return self._executions.get(execution_id)

    async def list_executions(
        self,
        workflow_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkflowExecution]:
        results = list(self._executions.values())
        if workflow_id:
            results = [e for e in results if e.workflow_id == workflow_id]
        if status:
            results = [e for e in results if e.status.value == status]
        results.sort(key=lambda e: e.created_at or "", reverse=True)
        return results[offset : offset + limit]

    async def delete_execution(self, execution_id: str) -> bool:
        return self._executions.pop(execution_id, None) is not None
