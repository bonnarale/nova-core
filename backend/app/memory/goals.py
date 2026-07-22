"""Goal manager interface and GoalManager service."""

import logging
from abc import ABC, abstractmethod
from uuid import UUID

from app.db.goal_repository import GoalRepository
from app.db.postgres import Database

logger = logging.getLogger(__name__)


class GoalProvider(ABC):
    @abstractmethod
    async def create_goal(
        self,
        user_id: UUID,
        title: str,
        description: str | None = None,
        priority: int = 3,
    ) -> dict:
        ...

    @abstractmethod
    async def get_goal(self, goal_id: UUID) -> dict | None:
        ...

    @abstractmethod
    async def list_goals(
        self, user_id: UUID, status: str | None = None
    ) -> list[dict]:
        ...

    @abstractmethod
    async def update_goal(
        self,
        goal_id: UUID,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: int | None = None,
        progress: int | None = None,
        block_reason: str | None = None,
    ) -> dict | None:
        ...

    @abstractmethod
    async def delete_goal(self, goal_id: UUID) -> bool:
        ...

    @abstractmethod
    async def get_next_actions(
        self, user_id: UUID, limit: int = 3
    ) -> list[dict]:
        ...

    @abstractmethod
    async def get_blocked_goals(self, user_id: UUID) -> list[dict]:
        ...

    @abstractmethod
    async def analyze_progress(self, user_id: UUID) -> dict:
        ...


class GoalManager(GoalProvider):
    def __init__(self, database: Database) -> None:
        self._repo = GoalRepository(database.session_factory)

    def _to_dict(self, goal) -> dict | None:
        if goal is None:
            return None
        return {
            "id": str(goal.id),
            "user_id": str(goal.user_id),
            "title": goal.title,
            "description": goal.description,
            "status": goal.status,
            "priority": goal.priority,
            "progress": goal.progress,
            "block_reason": goal.block_reason,
            "created_at": goal.created_at.isoformat() if goal.created_at else None,
            "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
        }

    async def create_goal(
        self,
        user_id: UUID,
        title: str,
        description: str | None = None,
        priority: int = 3,
    ) -> dict:
        goal = await self._repo.create(user_id, title, description, priority)
        logger.debug("GoalManager: goal created %s", goal.id)
        return self._to_dict(goal)

    async def get_goal(self, goal_id: UUID) -> dict | None:
        goal = await self._repo.get(goal_id)
        return self._to_dict(goal)

    async def list_goals(
        self, user_id: UUID, status: str | None = None
    ) -> list[dict]:
        goals = await self._repo.list_by_user(user_id, status)
        return [self._to_dict(g) for g in goals]

    async def update_goal(
        self,
        goal_id: UUID,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: int | None = None,
        progress: int | None = None,
        block_reason: str | None = None,
    ) -> dict | None:
        goal = await self._repo.update(
            goal_id, title, description, status, priority, progress, block_reason
        )
        return self._to_dict(goal)

    async def delete_goal(self, goal_id: UUID) -> bool:
        return await self._repo.delete(goal_id)

    async def get_next_actions(
        self, user_id: UUID, limit: int = 3
    ) -> list[dict]:
        goals = await self._repo.get_next_actions(user_id, limit)
        return [self._to_dict(g) for g in goals]

    async def get_blocked_goals(self, user_id: UUID) -> list[dict]:
        goals = await self._repo.get_blocked(user_id)
        return [self._to_dict(g) for g in goals]

    async def analyze_progress(self, user_id: UUID) -> dict:
        goals = await self._repo.list_by_user(user_id)
        total = len(goals)
        active = sum(1 for g in goals if g.status == "active" and g.progress < 100)
        blocked = sum(1 for g in goals if g.status == "blocked")
        completed = sum(1 for g in goals if g.status == "completed" or g.progress >= 100)
        abandoned = sum(1 for g in goals if g.status == "abandoned")
        avg_progress = sum(g.progress for g in goals) / total if total else 0.0
        next_actions = await self._repo.get_next_actions(user_id, limit=3)
        return {
            "total": total,
            "active": active,
            "blocked": blocked,
            "completed": completed,
            "abandoned": abandoned,
            "avg_progress": round(avg_progress, 1),
            "next_actions": [self._to_dict(g) for g in next_actions],
        }
