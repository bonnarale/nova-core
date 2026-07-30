"""ActivityLogRepository — data access layer for activity log persistence."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import ActivityLog

logger = logging.getLogger(__name__)


class ActivityLogRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        user_id: UUID,
        action: str,
        status: str,
        goal_id: UUID | None = None,
        goal_title: str | None = None,
        goal_priority: int | None = None,
        approval_id: str | None = None,
        reason: str | None = None,
        details: dict | None = None,
    ) -> ActivityLog:
        async with self._session_factory() as session:
            entry = ActivityLog(
                user_id=user_id,
                action=action,
                status=status,
                goal_id=goal_id,
                goal_title=goal_title,
                goal_priority=goal_priority,
                approval_id=approval_id,
                reason=reason,
                details=details or {},
            )
            session.add(entry)
            await session.commit()
            logger.debug("ActivityLog created: %s", entry.id)
            return entry

    async def get_by_id(self, entry_id: UUID) -> ActivityLog | None:
        async with self._session_factory() as session:
            return await session.get(ActivityLog, entry_id)

    async def list_recent(self, limit: int = 20) -> list[ActivityLog]:
        async with self._session_factory() as session:
            stmt = (
                select(ActivityLog)
                .order_by(ActivityLog.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_by_user(
        self, user_id: UUID, limit: int = 20
    ) -> list[ActivityLog]:
        async with self._session_factory() as session:
            stmt = (
                select(ActivityLog)
                .where(ActivityLog.user_id == user_id)
                .order_by(ActivityLog.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_by_goal(
        self, goal_id: UUID, limit: int = 20
    ) -> list[ActivityLog]:
        async with self._session_factory() as session:
            stmt = (
                select(ActivityLog)
                .where(ActivityLog.goal_id == goal_id)
                .order_by(ActivityLog.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
