"""TaskManager - high-level orchestration facade."""

from __future__ import annotations

import logging
from uuid import UUID

from app.agents.agent_manager import AgentManager
from app.db.postgres import Database
from app.db.task_repository import TaskRepository
from app.orchestrator.event_bus import EventBus
from app.orchestrator.planner import Planner
from app.orchestrator.worker import Worker

logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(
        self,
        database: Database,
        event_bus: EventBus | None = None,
        agent_manager: AgentManager | None = None,
    ) -> None:
        self._database = database
        self._event_bus = event_bus or EventBus()
        self._agent_manager = agent_manager
        self._repo = TaskRepository(database.session_factory)
        self.planner = Planner(database, self._event_bus)
        self.worker = Worker(database, self._event_bus)

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def agent_manager(self) -> AgentManager | None:
        return self._agent_manager

    async def create_task(
        self,
        goal: str,
        plan: dict | None = None,
        steps: list | None = None,
        dependencies: list | None = None,
        assigned_agent: str | None = None,
    ) -> dict:
        return await self.planner.create_task(
            goal=goal,
            plan=plan,
            steps=steps,
            dependencies=dependencies,
            assigned_agent=assigned_agent,
        )

    async def get_task(self, task_id: UUID) -> dict | None:
        task = await self._repo.get(task_id)
        if task is None:
            return None
        return self._to_dict(task)

    async def list_tasks(
        self, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        tasks = await self._repo.list(status=status, limit=limit, offset=offset)
        return [self._to_dict(t) for t in tasks]

    async def delete_task(self, task_id: UUID) -> bool:
        return await self._repo.delete(task_id)

    async def transition_task(
        self, task_id: UUID, next_status: str, **updates
    ) -> dict | None:
        result = await self.worker.transition(task_id, next_status, **updates)
        if result and next_status == "RUNNING" and self._agent_manager:
            assigned = result.get("assigned_agent")
            if assigned:
                await self._agent_manager.dispatch(
                    agent_id=assigned,
                    task=result.get("goal", ""),
                    context={"task_id": str(task_id), "task": result},
                )
        return result

    async def advance_step(
        self, task_id: UUID, artifacts: dict | None = None
    ) -> dict | None:
        return await self.worker.advance_step(task_id, artifacts=artifacts)

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
