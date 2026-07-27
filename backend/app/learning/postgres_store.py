"""PostgreSQL-backed store for learning artifacts.

Implements the LearningStore ABC using async SQLAlchemy sessions.
Replaces the in-memory LearningRepository for production persistence.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table, Text, delete, func, select, update
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.sql import func as sqlfunc

from app.learning.base import LearningStore
from app.learning.models import KnowledgeArtifact

logger = logging.getLogger(__name__)

# Module-level table definition (reflects learning_artifacts schema)
_metadata = MetaData()
_learning_artifacts = Table(
    "learning_artifacts",
    _metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True),
    Column("artifact_type", String(30), nullable=False),
    Column("content", Text(), nullable=False),
    Column("summary", Text(), nullable=True, default=""),
    Column("tags", JSONB, nullable=True, default=list),
    Column("source_execution_id", String(255), nullable=True),
    Column("source_task_id", String(255), nullable=True),
    Column("user_id", PG_UUID(as_uuid=True), nullable=True),
    Column("agent_id", String(100), nullable=True),
    Column("confidence", Float(), nullable=True, default=0.0),
    Column("importance_score", Float(), nullable=True, default=0.0),
    Column("access_count", Integer(), nullable=False, default=0),
    Column("metadata_", JSONB, nullable=True, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=sqlfunc.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=sqlfunc.now(), nullable=False),
)


class PostgresLearningStore(LearningStore):
    """PostgreSQL-backed implementation of LearningStore.

    Uses async SQLAlchemy sessions to persist KnowledgeArtifacts
    in the ``learning_artifacts`` table.
    """

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _table() -> Table:
        return _learning_artifacts

    async def create(self, artifact: KnowledgeArtifact) -> KnowledgeArtifact:
        now = datetime.now(tz=timezone.utc)
        if not artifact.created_at:
            artifact.created_at = now.isoformat()
        if not artifact.updated_at:
            artifact.updated_at = now.isoformat()

        table = self._table()
        async with self._session_factory() as session:
            stmt = table.insert().values(
                id=UUID(artifact.id) if isinstance(artifact.id, str) else artifact.id,
                artifact_type=artifact.artifact_type,
                content=artifact.content,
                summary=artifact.summary or "",
                tags=artifact.tags or [],
                source_execution_id=artifact.source_execution_id,
                source_task_id=artifact.source_task_id,
                user_id=UUID(artifact.user_id) if artifact.user_id else None,
                agent_id=artifact.agent_id,
                confidence=artifact.confidence,
                importance_score=artifact.importance_score,
                access_count=artifact.access_count,
                metadata_=artifact.metadata or {},
                created_at=artifact.created_at,
                updated_at=artifact.updated_at,
            )
            await session.execute(stmt)
            await session.commit()

        logger.debug("PostgresLearningStore: created artifact %s", artifact.id)
        return artifact

    async def get(self, artifact_id: str) -> KnowledgeArtifact | None:
        table = self._table()
        async with self._session_factory() as session:
            stmt = select(table).where(
                table.c.id == UUID(artifact_id) if isinstance(artifact_id, str) else artifact_id
            )
            result = await session.execute(stmt)
            row = result.mappings().first()
            if row is None:
                return None
            return self._row_to_artifact(row)

    async def update(self, artifact: KnowledgeArtifact) -> KnowledgeArtifact | None:
        artifact.updated_at = datetime.now(tz=timezone.utc).isoformat()
        table = self._table()
        async with self._session_factory() as session:
            stmt = (
                update(table)
                .where(table.c.id == UUID(artifact.id) if isinstance(artifact.id, str) else artifact.id)
                .values(
                    artifact_type=artifact.artifact_type,
                    content=artifact.content,
                    summary=artifact.summary or "",
                    tags=artifact.tags or [],
                    confidence=artifact.confidence,
                    importance_score=artifact.importance_score,
                    access_count=artifact.access_count,
                    metadata_=artifact.metadata or {},
                    updated_at=artifact.updated_at,
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            if result.rowcount == 0:
                return None
        return artifact

    async def delete(self, artifact_id: str) -> bool:
        table = self._table()
        async with self._session_factory() as session:
            stmt = delete(table).where(
                table.c.id == UUID(artifact_id) if isinstance(artifact_id, str) else artifact_id
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def list_by_user(
        self,
        user_id: str,
        artifact_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[KnowledgeArtifact]:
        table = self._table()
        async with self._session_factory() as session:
            stmt = select(table).where(table.c.user_id == UUID(user_id))
            if artifact_type:
                stmt = stmt.where(table.c.artifact_type == artifact_type)
            stmt = stmt.order_by(table.c.created_at.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)
            return [self._row_to_artifact(row) for row in result.mappings().all()]

    async def list_by_type(
        self,
        artifact_type: str,
        limit: int = 50,
    ) -> list[KnowledgeArtifact]:
        table = self._table()
        async with self._session_factory() as session:
            stmt = (
                select(table)
                .where(table.c.artifact_type == artifact_type)
                .order_by(table.c.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [self._row_to_artifact(row) for row in result.mappings().all()]

    async def list_all(self, limit: int = 500) -> list[KnowledgeArtifact]:
        table = self._table()
        async with self._session_factory() as session:
            stmt = select(table).order_by(table.c.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            return [self._row_to_artifact(row) for row in result.mappings().all()]

    async def search_by_tags(
        self,
        tags: list[str],
        artifact_type: str | None = None,
        limit: int = 50,
    ) -> list[KnowledgeArtifact]:
        table = self._table()
        async with self._session_factory() as session:
            # Use JSONB overlap operator for tag matching
            stmt = select(table).where(table.c.tags.op("@>")(tags))
            if artifact_type:
                stmt = stmt.where(table.c.artifact_type == artifact_type)
            stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            return [self._row_to_artifact(row) for row in result.mappings().all()]

    async def count(self) -> int:
        table = self._table()
        async with self._session_factory() as session:
            stmt = select(func.count()).select_from(table)
            result = await session.execute(stmt)
            return result.scalar() or 0

    async def count_by_type(self) -> dict[str, int]:
        table = self._table()
        async with self._session_factory() as session:
            stmt = select(
                table.c.artifact_type,
                func.count(),
            ).group_by(table.c.artifact_type)
            result = await session.execute(stmt)
            return {row[0]: row[1] for row in result.all()}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_artifact(row: Any) -> KnowledgeArtifact:
        """Convert a database row to a KnowledgeArtifact."""
        user_id = row.get("user_id")
        return KnowledgeArtifact(
            id=str(row["id"]),
            artifact_type=row["artifact_type"],
            content=row["content"],
            summary=row.get("summary", ""),
            tags=list(row.get("tags") or []),
            source_execution_id=row.get("source_execution_id"),
            source_task_id=row.get("source_task_id"),
            user_id=str(user_id) if user_id else None,
            agent_id=row.get("agent_id"),
            confidence=float(row.get("confidence") or 0.0),
            importance_score=float(row.get("importance_score") or 0.0),
            access_count=int(row.get("access_count") or 0),
            metadata=dict(row.get("metadata_") or {}),
            created_at=row["created_at"].isoformat() if row.get("created_at") else "",
            updated_at=row["updated_at"].isoformat() if row.get("updated_at") else "",
        )
