"""TaskRepository — data access layer for task persistence."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """Task data model."""
    id: UUID
    goal: str
    status: str = "CREATED"
    dependencies: list[str] = field(default_factory=list)
    assigned_agent: str | None = None
    plan: dict[str, Any] = field(default_factory=dict)
    steps: list[dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    artifacts: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskRepository:
    """In-memory task repository for development and testing."""

    def __init__(self) -> None:
        self._store: dict[UUID, Task] = {}

    async def get(self, task_id: UUID) -> Task | None:
        """Get a task by ID."""
        return self._store.get(task_id)

    async def create(self, task: Task) -> Task:
        """Create a new task."""
        self._store[task.id] = task
        return task

    async def update(self, task_id: UUID, **kwargs: Any) -> Task | None:
        """Update a task."""
        task = self._store.get(task_id)
        if task is None:
            return None

        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)

        task.updated_at = datetime.now(timezone.utc)
        return task

    async def delete(self, task_id: UUID) -> bool:
        """Delete a task."""
        if task_id in self._store:
            del self._store[task_id]
            return True
        return False

    async def list(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """List tasks with optional filtering."""
        tasks = list(self._store.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        return tasks[offset : offset + limit]
