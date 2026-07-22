"""Data access repository for Long-Term Memory entries."""

import logging
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import LongTermMemoryEntry

logger = logging.getLogger(__name__)


class LongTermMemoryRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def create(self, entry: LongTermMemoryEntry) -> LongTermMemoryEntry:
        async with self._session_factory() as session:
            session.add(entry)
            await session.commit()
            await session.refresh(entry)
            logger.debug("LTM entry created: %s", entry.id)
            return entry

    async def get(self, entry_id: UUID) -> LongTermMemoryEntry | None:
        async with self._session_factory() as session:
            return await session.get(LongTermMemoryEntry, entry_id)

    async def update(self, entry: LongTermMemoryEntry) -> LongTermMemoryEntry | None:
        async with self._session_factory() as session:
            existing = await session.get(LongTermMemoryEntry, entry.id)
            if existing is None:
                return None
            for col in LongTermMemoryEntry.__table__.columns:
                if col.name == "id" or col.name == "created_at":
                    continue
                val = getattr(entry, col.name, None)
                if val is not None:
                    setattr(existing, col.name, val)
            await session.commit()
            await session.refresh(existing)
            logger.debug("LTM entry updated: %s", entry.id)
            return existing

    async def delete(self, entry_id: UUID) -> bool:
        async with self._session_factory() as session:
            existing = await session.get(LongTermMemoryEntry, entry_id)
            if existing is None:
                return False
            await session.delete(existing)
            await session.commit()
            logger.debug("LTM entry deleted: %s", entry_id)
            return True

    async def list_by_user(
        self,
        user_id: UUID,
        memory_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LongTermMemoryEntry]:
        async with self._session_factory() as session:
            stmt = select(LongTermMemoryEntry).where(
                LongTermMemoryEntry.user_id == user_id
            )
            if memory_type:
                stmt = stmt.where(LongTermMemoryEntry.memory_type == memory_type)
            if status:
                stmt = stmt.where(LongTermMemoryEntry.status == status)
            stmt = stmt.order_by(
                LongTermMemoryEntry.importance_score.desc(),
                LongTermMemoryEntry.accessed_at.desc(),
            ).limit(limit).offset(offset)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_by_type(
        self,
        memory_type: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[LongTermMemoryEntry]:
        async with self._session_factory() as session:
            stmt = select(LongTermMemoryEntry).where(
                LongTermMemoryEntry.memory_type == memory_type
            )
            if status:
                stmt = stmt.where(LongTermMemoryEntry.status == status)
            stmt = stmt.order_by(LongTermMemoryEntry.importance_score.desc()).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def search_by_tags(
        self,
        tags: list[str],
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[LongTermMemoryEntry]:
        async with self._session_factory() as session:
            stmt = select(LongTermMemoryEntry)
            filters = []
            for tag in tags:
                filters.append(LongTermMemoryEntry.tags.any(tag))
            if filters:
                stmt = stmt.where(*filters)
            if memory_type:
                stmt = stmt.where(LongTermMemoryEntry.memory_type == memory_type)
            stmt = stmt.order_by(LongTermMemoryEntry.importance_score.desc()).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def search_by_entity(
        self,
        entity: str,
        limit: int = 50,
    ) -> list[LongTermMemoryEntry]:
        async with self._session_factory() as session:
            stmt = (
                select(LongTermMemoryEntry)
                .where(LongTermMemoryEntry.entities.any(entity))
                .order_by(LongTermMemoryEntry.importance_score.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_related(
        self, entry_id: UUID, limit: int = 20
    ) -> list[LongTermMemoryEntry]:
        async with self._session_factory() as session:
            entry = await session.get(LongTermMemoryEntry, entry_id)
            if entry is None:
                return []
            linked = entry.linked_memory_ids or []
            if not linked:
                return []
            uuids = []
            for lid in linked:
                try:
                    uuids.append(UUID(lid) if isinstance(lid, str) else lid)
                except (ValueError, TypeError):
                    continue
            if not uuids:
                return []
            stmt = (
                select(LongTermMemoryEntry)
                .where(LongTermMemoryEntry.id.in_(uuids))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_aging(
        self, age_days: int = 30, limit: int = 100
    ) -> list[LongTermMemoryEntry]:
        async with self._session_factory() as session:
            cutoff = func.now() - func.make_interval(days=age_days)
            stmt = (
                select(LongTermMemoryEntry)
                .where(LongTermMemoryEntry.status == "active")
                .where(LongTermMemoryEntry.accessed_at < cutoff)
                .order_by(LongTermMemoryEntry.accessed_at.asc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_archivable(
        self, min_age_days: int = 90, importance_below: int = 30, limit: int = 100
    ) -> list[LongTermMemoryEntry]:
        async with self._session_factory() as session:
            cutoff = func.now() - func.make_interval(days=min_age_days)
            stmt = (
                select(LongTermMemoryEntry)
                .where(LongTermMemoryEntry.status == "active")
                .where(LongTermMemoryEntry.importance_score < importance_below)
                .where(LongTermMemoryEntry.accessed_at < cutoff)
                .order_by(LongTermMemoryEntry.importance_score.asc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def count_by_status(self) -> dict[str, int]:
        async with self._session_factory() as session:
            stmt = (
                select(LongTermMemoryEntry.status, func.count(LongTermMemoryEntry.id))
                .group_by(LongTermMemoryEntry.status)
            )
            result = await session.execute(stmt)
            return {row[0]: row[1] for row in result}

    async def search_by_source(
        self, source: str, source_id: str | None = None, limit: int = 10
    ) -> list[LongTermMemoryEntry]:
        async with self._session_factory() as session:
            stmt = select(LongTermMemoryEntry).where(
                LongTermMemoryEntry.source == source
            )
            if source_id:
                stmt = stmt.where(LongTermMemoryEntry.source_id == source_id)
            stmt = stmt.order_by(LongTermMemoryEntry.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())
