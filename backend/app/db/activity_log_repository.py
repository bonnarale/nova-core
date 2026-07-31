"""ActivityLogRepository — data access layer for activity log persistence."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
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
        tool_name: str | None = None,
        tool_params: dict | None = None,
        tool_result: dict | None = None,
        duration_ms: int | None = None,
        session_id: UUID | None = None,
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
                tool_name=tool_name,
                tool_params=tool_params or {},
                tool_result=tool_result or {},
                duration_ms=duration_ms,
                session_id=session_id,
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

    async def list_tool_executions(
        self,
        user_id: UUID | None = None,
        tool_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ActivityLog]:
        """List tool executions with optional filters."""
        async with self._session_factory() as session:
            stmt = select(ActivityLog).where(ActivityLog.tool_name.isnot(None))
            if user_id:
                stmt = stmt.where(ActivityLog.user_id == user_id)
            if tool_name:
                stmt = stmt.where(ActivityLog.tool_name == tool_name)
            stmt = stmt.order_by(ActivityLog.created_at.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_decisions(
        self,
        user_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ActivityLog]:
        """List entries that have reasoning (decisions)."""
        async with self._session_factory() as session:
            stmt = select(ActivityLog).where(ActivityLog.reason.isnot(None))
            if user_id:
                stmt = stmt.where(ActivityLog.user_id == user_id)
            stmt = stmt.order_by(ActivityLog.created_at.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_tool_metrics(
        self,
        hours: int = 24,
    ) -> dict:
        """Get aggregated tool metrics for the last N hours."""
        async with self._session_factory() as session:
            since = datetime.now(timezone.utc) - timedelta(hours=hours)

            # Total executions per tool
            stmt = (
                select(
                    ActivityLog.tool_name,
                    func.count().label("executions"),
                    func.count(ActivityLog.id).filter(ActivityLog.status == "success").label("successes"),
                    func.count(ActivityLog.id).filter(ActivityLog.status == "failed").label("failures"),
                    func.avg(ActivityLog.duration_ms).label("avg_duration_ms"),
                    func.max(ActivityLog.created_at).label("last_used"),
                )
                .where(ActivityLog.tool_name.isnot(None))
                .where(ActivityLog.created_at >= since)
                .group_by(ActivityLog.tool_name)
            )
            result = await session.execute(stmt)
            rows = result.all()

            tools = {}
            for row in rows:
                tools[row.tool_name] = {
                    "executions": row.executions,
                    "successes": row.successes,
                    "failures": row.failures,
                    "success_rate": round(row.successes / max(row.executions, 1) * 100, 1),
                    "avg_duration_ms": round(row.avg_duration_ms or 0, 1),
                    "last_used": row.last_used.isoformat() if row.last_used else None,
                }

            return {
                "period_hours": hours,
                "tools": tools,
                "total_executions": sum(t["executions"] for t in tools.values()),
            }

    async def list_timeline(
        self,
        session_id: UUID | None = None,
        user_id: UUID | None = None,
        limit: int = 100,
    ) -> list[ActivityLog]:
        """List all activity for a timeline view (decisions + tool executions)."""
        async with self._session_factory() as session:
            stmt = select(ActivityLog)
            if session_id:
                stmt = stmt.where(ActivityLog.session_id == session_id)
            if user_id:
                stmt = stmt.where(ActivityLog.user_id == user_id)
            stmt = stmt.order_by(ActivityLog.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())
