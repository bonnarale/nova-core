"""Planner that creates tasks from goals and generates execution plans."""

from __future__ import annotations

import logging
from uuid import UUID

from app.db.postgres import Database
from app.db.task_repository import TaskRepository
from app.orchestrator.event_bus import EventBus

logger = logging.getLogger(__name__)


class Planner:
    def __init__(self, database: Database, event_bus: EventBus) -> None:
        self._repo = TaskRepository(database.session_factory)
        self._event_bus = event_bus

    async def create_task(
        self,
        goal: str,
        plan: dict | None = None,
        steps: list | None = None,
        dependencies: list | None = None,
        assigned_agent: str | None = None,
    ) -> dict:
        task = await self._repo.create(
            goal=goal,
            plan=plan or {},
            steps=steps or [],
            dependencies=dependencies or [],
            assigned_agent=assigned_agent,
        )
        await self._event_bus.emit("task.created", {"task_id": str(task.id), "goal": goal})
        result = self._to_dict(task)
        logger.info("Planner: task created %s for goal: %s", task.id, goal)
        return result

    @staticmethod
    def _serialize_dt(val) -> str | None:
        if val is None:
            return None
        if hasattr(val, "isoformat"):
            return val.isoformat()
        return str(val)

    def _to_dict(self, task) -> dict:
        return {
            "id": str(task.id),
            "goal": task.goal,
            "plan": task.plan or {},
            "steps": task.steps or [],
            "current_step": task.current_step,
            "status": task.status,
            "dependencies": task.dependencies or [],
            "artifacts": task.artifacts or {},
            "events": task.events or [],
            "assigned_agent": task.assigned_agent,
            "created_at": self._serialize_dt(task.created_at),
            "updated_at": self._serialize_dt(task.updated_at),
            "started_at": self._serialize_dt(task.started_at),
            "completed_at": self._serialize_dt(task.completed_at),
        }
