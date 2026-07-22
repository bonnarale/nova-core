import logging
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import Goal

logger = logging.getLogger(__name__)


class GoalRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        user_id: UUID,
        title: str,
        description: str | None = None,
        priority: int = 3,
    ) -> Goal:
        async with self._session_factory() as session:
            goal = Goal(
                user_id=user_id,
                title=title,
                description=description,
                priority=priority,
                status="active",
                progress=0,
            )
            session.add(goal)
            await session.commit()
            logger.debug("Goal created: %s for user %s", goal.id, user_id)
            return goal

    async def get(self, goal_id: UUID) -> Goal | None:
        async with self._session_factory() as session:
            return await session.get(Goal, goal_id)

    async def list_by_user(
        self, user_id: UUID, status: str | None = None
    ) -> list[Goal]:
        async with self._session_factory() as session:
            stmt = select(Goal).where(Goal.user_id == user_id)
            if status:
                stmt = stmt.where(Goal.status == status)
            stmt = stmt.order_by(Goal.priority.desc(), Goal.created_at.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update(
        self,
        goal_id: UUID,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: int | None = None,
        progress: int | None = None,
        block_reason: str | None = None,
    ) -> Goal | None:
        async with self._session_factory() as session:
            goal = await session.get(Goal, goal_id)
            if goal is None:
                return None
            if title is not None:
                goal.title = title
            if description is not None:
                goal.description = description
            if status is not None:
                goal.status = status
            if priority is not None:
                goal.priority = priority
            if progress is not None:
                goal.progress = progress
            if block_reason is not None:
                goal.block_reason = block_reason
            await session.commit()
            logger.debug("Goal updated: %s", goal_id)
            return goal

    async def delete(self, goal_id: UUID) -> bool:
        async with self._session_factory() as session:
            goal = await session.get(Goal, goal_id)
            if goal is None:
                return False
            await session.delete(goal)
            await session.commit()
            logger.debug("Goal deleted: %s", goal_id)
            return True

    async def get_next_actions(
        self, user_id: UUID, limit: int = 3
    ) -> list[Goal]:
        async with self._session_factory() as session:
            stmt = (
                select(Goal)
                .where(Goal.user_id == user_id)
                .where(Goal.status == "active")
                .where(Goal.progress < 100)
                .order_by(Goal.priority.desc(), Goal.progress.asc(), Goal.created_at.asc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_blocked(self, user_id: UUID) -> list[Goal]:
        async with self._session_factory() as session:
            stmt = (
                select(Goal)
                .where(Goal.user_id == user_id)
                .where(Goal.status == "blocked")
                .order_by(Goal.priority.desc(), Goal.updated_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
