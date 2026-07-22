"""TaskManager — high-level task orchestration facade."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from app.db.task_repository import Task, TaskRepository
from app.events.bus import InMemoryEventBus
from app.events.schemas import Event

logger = logging.getLogger(__name__)


class TaskManager:
    """High-level task management facade."""

    def __init__(
        self,
        event_bus: InMemoryEventBus | None = None,
    ) -> None:
        self._repo = TaskRepository()
        self._event_bus = event_bus

    @property
    def event_bus(self) -> InMemoryEventBus | None:
        return self._event_bus

    async def create_task(
        self,
        goal: str,
        dependencies: list[str] | None = None,
        assigned_agent: str | None = None,
        plan: dict[str, Any] | None = None,
        steps: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a new task."""
        task_id = uuid4()
        task = Task(
            id=task_id,
            goal=goal,
            dependencies=dependencies or [],
            assigned_agent=assigned_agent,
            plan=plan or {},
            steps=steps or [],
        )

        await self._repo.create(task)

        # Emit task.created event
        if self._event_bus:
            await self._event_bus.publish(Event(
                event_type="task.created",
                aggregate_id=str(task_id),
                payload={
                    "task_id": str(task_id),
                    "goal": goal,
                    "assigned_agent": assigned_agent,
                },
                source="task_manager",
            ))

        logger.info("TaskManager: created task %s", task_id)
        return self._to_dict(task)

    async def get_task(self, task_id: UUID) -> dict[str, Any] | None:
        """Get a task by ID."""
        task = await self._repo.get(task_id)
        if task is None:
            return None
        return self._to_dict(task)

    async def transition_task(
        self, task_id: UUID, next_status: str, **updates: Any
    ) -> dict[str, Any] | None:
        """Transition a task to a new status."""
        task = await self._repo.get(task_id)
        if task is None:
            logger.warning("TaskManager: task %s not found", task_id)
            return None

        old_status = task.status
        task.status = next_status

        # Apply updates
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)

        # Set timestamps based on status
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        task.updated_at = now

        if next_status == "RUNNING" and task.started_at is None:
            task.started_at = now
        elif next_status in ("COMPLETED", "FAILED"):
            task.completed_at = now

        # Store status transition in events
        task.events.append({
            "type": "status_transition",
            "from": old_status,
            "to": next_status,
            "timestamp": now.isoformat(),
        })

        await self._repo.update(task_id, **{
            "status": task.status,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "events": task.events,
            "artifacts": task.artifacts,
        })

        logger.info(
            "TaskManager: task %s transitioned %s -> %s",
            task_id, old_status, next_status,
        )
        return self._to_dict(task)

    async def list_tasks(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List tasks."""
        tasks = await self._repo.list(status=status, limit=limit, offset=offset)
        return [self._to_dict(t) for t in tasks]

    async def delete_task(self, task_id: UUID) -> bool:
        """Delete a task."""
        return await self._repo.delete(task_id)

    def _to_dict(self, task: Task) -> dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": str(task.id),
            "goal": task.goal,
            "status": task.status,
            "dependencies": task.dependencies,
            "assigned_agent": task.assigned_agent,
            "plan": task.plan,
            "steps": task.steps,
            "current_step": task.current_step,
            "artifacts": task.artifacts,
            "events": task.events,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
