"""Data access repository for orchestrator tasks."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import OrchestratorTask

logger = logging.getLogger(__name__)

_VALID_STATUSES = frozenset({"CREATED", "QUEUED", "RUNNING", "WAITING", "FAILED", "COMPLETED"})


class TaskRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        goal: str,
        plan: dict | None = None,
        steps: list | None = None,
        dependencies: list | None = None,
        assigned_agent: str | None = None,
    ) -> OrchestratorTask:
        async with self._session_factory() as session:
            task = OrchestratorTask(
                goal=goal,
                plan=plan or {},
                steps=steps or [],
                status="CREATED",
                dependencies=dependencies or [],
                artifacts={},
                events=[],
                assigned_agent=assigned_agent,
            )
            session.add(task)
            await session.commit()
            logger.debug("Task created: %s", task.id)
            return task

    async def get(self, task_id: UUID) -> OrchestratorTask | None:
        async with self._session_factory() as session:
            return await session.get(OrchestratorTask, task_id)

    async def list(
        self, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[OrchestratorTask]:
        async with self._session_factory() as session:
            stmt = select(OrchestratorTask).order_by(OrchestratorTask.created_at.desc())
            if status:
                if status not in _VALID_STATUSES:
                    raise ValueError(f"Invalid status: {status}")
                stmt = stmt.where(OrchestratorTask.status == status)
            stmt = stmt.offset(offset).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update(
        self,
        task_id: UUID,
        status: str | None = None,
        current_step: int | None = None,
        plan: dict | None = None,
        steps: list | None = None,
        artifacts: dict | None = None,
        events: list | None = None,
        assigned_agent: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
    ) -> OrchestratorTask | None:
        async with self._session_factory() as session:
            task = await session.get(OrchestratorTask, task_id)
            if task is None:
                return None
            if status is not None:
                task.status = status
            if current_step is not None:
                task.current_step = current_step
            if plan is not None:
                task.plan = plan
            if steps is not None:
                task.steps = steps
            if artifacts is not None:
                task.artifacts = artifacts
            if events is not None:
                task.events = events
            if assigned_agent is not None:
                task.assigned_agent = assigned_agent
            if started_at is not None:
                import datetime
                task.started_at = datetime.datetime.fromisoformat(started_at)
            if completed_at is not None:
                import datetime
                task.completed_at = datetime.datetime.fromisoformat(completed_at)
            await session.commit()
            logger.debug("Task updated: %s", task_id)
            return task

    async def delete(self, task_id: UUID) -> bool:
        async with self._session_factory() as session:
            task = await session.get(OrchestratorTask, task_id)
            if task is None:
                return False
            await session.delete(task)
            await session.commit()
            logger.debug("Task deleted: %s", task_id)
            return True

    async def add_event(self, task_id: UUID, event: dict) -> OrchestratorTask | None:
        async with self._session_factory() as session:
            task = await session.get(OrchestratorTask, task_id)
            if task is None:
                return None
            events = list(task.events or [])
            events.append(event)
            task.events = events
            await session.commit()
            return task
