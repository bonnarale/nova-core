"""Worker that executes tasks and manages their lifecycle."""

from __future__ import annotations

import datetime
import logging
from uuid import UUID

from app.db.postgres import Database
from app.db.task_repository import TaskRepository
from app.orchestrator.event_bus import EventBus

logger = logging.getLogger(__name__)

_VALID_TRANSITIONS = {
    "CREATED": {"QUEUED", "FAILED"},
    "QUEUED": {"RUNNING", "FAILED"},
    "RUNNING": {"WAITING", "COMPLETED", "FAILED"},
    "WAITING": {"RUNNING", "FAILED"},
    "FAILED": set(),
    "COMPLETED": set(),
}


class Worker:
    def __init__(self, database: Database, event_bus: EventBus) -> None:
        self._repo = TaskRepository(database.session_factory)
        self._event_bus = event_bus
        self._running: bool = False

    def _validate_transition(self, current: str, next_status: str) -> None:
        allowed = _VALID_TRANSITIONS.get(current, set())
        if next_status not in allowed:
            raise ValueError(
                f"Invalid transition: {current} -> {next_status}. "
                f"Allowed: {allowed}"
            )

    async def transition(
        self, task_id: UUID, next_status: str, **updates
    ) -> dict | None:
        task = await self._repo.get(task_id)
        if task is None:
            return None

        self._validate_transition(task.status, next_status)

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        event = {
            "type": f"task.{next_status.lower()}",
            "from": task.status,
            "to": next_status,
            "timestamp": now.isoformat(),
        }

        update_kwargs = {"status": next_status, "events": list(task.events or []) + [event]}

        if next_status == "RUNNING" and task.started_at is None:
            update_kwargs["started_at"] = now.isoformat()
        if next_status == "COMPLETED":
            update_kwargs["completed_at"] = now.isoformat()
            update_kwargs["current_step"] = len(task.steps or [])
        for k, v in updates.items():
            if v is not None:
                update_kwargs[k] = v

        updated = await self._repo.update(task_id, **update_kwargs)
        if updated:
            await self._event_bus.emit(
                f"task.{next_status.lower()}",
                {"task_id": str(task_id), "goal": task.goal, "event": event},
            )
            logger.info("Worker: task %s %s", task_id, next_status)

        return self._to_dict(updated) if updated else None

    async def advance_step(self, task_id: UUID, artifacts: dict | None = None) -> dict | None:
        task = await self._repo.get(task_id)
        if task is None:
            return None
        if task.status != "RUNNING":
            raise ValueError(f"Task {task_id} is not RUNNING (status: {task.status})")

        next_step = (task.current_step or 0) + 1
        total = len(task.steps or [])
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        event = {
            "type": "task.step_advanced",
            "step": next_step,
            "total": total,
            "timestamp": now.isoformat(),
        }

        merged_artifacts = dict(task.artifacts or {})
        if artifacts:
            merged_artifacts[f"step_{next_step}"] = artifacts

        events = list(task.events or []) + [event]

        if next_step >= total:
            return await self.transition(task_id, "COMPLETED", artifacts=merged_artifacts, events=events)
        else:
            return await self._transition_with_events(
                task_id, "RUNNING", current_step=next_step,
                artifacts=merged_artifacts, events=events,
            )

    async def _transition_with_events(self, task_id, status, **updates) -> dict | None:
        updated = await self._repo.update(task_id, status=status, **updates)
        return self._to_dict(updated) if updated else None

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
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "started_at": self._serialize_dt(task.started_at),
            "completed_at": self._serialize_dt(task.completed_at),
        }
