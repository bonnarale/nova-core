from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .schemas import DelegationTask


class DelegationEngine:
    def __init__(self) -> None:
        self._tasks: dict[str, DelegationTask] = {}

    def delegate(
        self,
        task_description: str,
        delegation_type: str = "agent",
        context: dict | None = None,
    ) -> dict:
        task = DelegationTask(
            task_description=task_description,
            assigned_to=delegation_type,
            delegation_type=delegation_type,
            context=context or {},
        )
        self._tasks[task.id] = task
        return self._task_to_dict(task)

    def get_task(self, task_id: str) -> dict | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        return self._task_to_dict(task)

    def update_task(self, task_id: str, **kwargs: object) -> dict | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        for k, v in kwargs.items():
            if hasattr(task, k):
                setattr(task, k, v)
        return self._task_to_dict(task)

    def complete_task(
        self, task_id: str, result: str | None = None
    ) -> dict | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.status = "completed"
        if result is not None:
            task.context["result"] = result
        return self._task_to_dict(task)

    def fail_task(self, task_id: str, error: str | None = None) -> dict | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.status = "failed"
        if error is not None:
            task.context["error"] = error
        return self._task_to_dict(task)

    def list_tasks(
        self, status: str | None = None, delegation_type: str | None = None
    ) -> list[dict]:
        tasks = list(self._tasks.values())
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if delegation_type is not None:
            tasks = [t for t in tasks if t.delegation_type == delegation_type]
        return [self._task_to_dict(t) for t in tasks]

    def recommend_delegation(self, task_description: str) -> dict:
        desc_lower = task_description.lower()
        if any(k in desc_lower for k in ("code", "implement", "write", "build")):
            rec_type = "open_code"
            reason = "Task involves code generation or implementation"
        elif any(k in desc_lower for k in ("search", "research", "find", "analyze")):
            rec_type = "workflow"
            reason = "Task involves research or analysis workflow"
        elif any(k in desc_lower for k in ("review", "check", "validate")):
            rec_type = "agent"
            reason = "Task involves review or validation by an agent"
        else:
            rec_type = "manual"
            reason = "Task does not clearly fit automated delegation"

        return {
            "recommended_type": rec_type,
            "reason": reason,
            "alternatives": [
                t for t in ["open_code", "workflow", "agent", "manual"] if t != rec_type
            ],
        }

    def _task_to_dict(self, task: DelegationTask) -> dict:
        return {
            "id": task.id,
            "task_description": task.task_description,
            "assigned_to": task.assigned_to,
            "delegation_type": task.delegation_type,
            "status": task.status,
            "context": task.context,
            "created_at": task.created_at,
        }

    def to_dict(self) -> dict:
        return {
            "tasks": {
                k: self._task_to_dict(v) for k, v in self._tasks.items()
            }
        }
