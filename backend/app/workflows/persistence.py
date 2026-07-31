"""Workflow persistence — pluggable persistence for workflow definitions and executions."""

from __future__ import annotations

import logging
from typing import Any

from app.workflows.models import WorkflowDefinition, WorkflowExecution

logger = logging.getLogger(__name__)


class InMemoryWorkflowPersistence:
    """In-memory persistence store for workflow definitions and executions."""

    def __init__(self) -> None:
        self._definitions: dict[str, WorkflowDefinition] = {}
        self._executions: dict[str, WorkflowExecution] = {}

    async def store_definition(self, definition: WorkflowDefinition) -> None:
        self._definitions[definition.id] = definition

    async def get_definition(self, workflow_id: str) -> WorkflowDefinition | None:
        return self._definitions.get(workflow_id)

    async def update_definition(self, definition: WorkflowDefinition) -> None:
        self._definitions[definition.id] = definition

    async def delete_definition(self, workflow_id: str) -> bool:
        return self._definitions.pop(workflow_id, None) is not None

    async def list_definitions(self, tag: str | None = None, limit: int = 100, offset: int = 0) -> list[WorkflowDefinition]:
        results = list(self._definitions.values())
        if tag:
            results = [w for w in results if tag in w.tags]
        return results[offset:offset + limit]

    async def count_definitions(self) -> int:
        return len(self._definitions)

    async def store_execution(self, execution: WorkflowExecution) -> None:
        self._executions[execution.id] = execution

    async def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        return self._executions.get(execution_id)

    async def update_execution(self, execution: WorkflowExecution) -> None:
        self._executions[execution.id] = execution

    async def delete_execution(self, execution_id: str) -> bool:
        return self._executions.pop(execution_id, None) is not None

    async def list_executions(self, workflow_id: str | None = None, status: str | None = None, limit: int = 100, offset: int = 0) -> list[WorkflowExecution]:
        results = list(self._executions.values())
        if workflow_id:
            results = [e for e in results if e.workflow_id == workflow_id]
        if status:
            results = [e for e in results if e.status.value == status]
        return results[offset:offset + limit]

    async def count_executions(self) -> int:
        return len(self._executions)

    async def clear(self) -> int:
        count = len(self._definitions) + len(self._executions)
        self._definitions.clear()
        self._executions.clear()
        return count
