"""Execution history tracking for workflow runs."""

from __future__ import annotations

from typing import Any

from app.workflows.models import WorkflowExecution


class WorkflowHistory:
    """In-memory store of workflow execution history."""

    def __init__(self) -> None:
        self._executions: dict[str, WorkflowExecution] = {}

    @property
    def executions(self) -> dict[str, WorkflowExecution]:
        return dict(self._executions)

    def record(self, execution: WorkflowExecution) -> None:
        self._executions[execution.id] = execution

    def get(self, execution_id: str) -> WorkflowExecution | None:
        return self._executions.get(execution_id)

    def list(
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

    def delete(self, execution_id: str) -> bool:
        return self._executions.pop(execution_id, None) is not None

    def count(self, workflow_id: str | None = None) -> int:
        if workflow_id:
            return sum(1 for e in self._executions.values() if e.workflow_id == workflow_id)
        return len(self._executions)
