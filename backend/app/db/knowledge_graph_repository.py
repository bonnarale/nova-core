"""SQLAlchemy-based repository for Knowledge Graph ORM models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import KnowledgeGraphEntityModel, KnowledgeGraphRelationshipModel
from app.knowledge_graph.models import (
    Entity,
    EntityStatus,
    EntityType,
    Relationship,
    RelationshipStatus,
    RelationshipType,
)
from app.knowledge_graph.repository import KnowledgeGraphRepository


def _entity_to_orm(entity: Entity) -> KnowledgeGraphEntityModel:
    return KnowledgeGraphEntityModel(
        id=UUID(entity.id),
        entity_type=entity.type.value,
        name=entity.name,
        aliases=entity.aliases,
        description=entity.description,
        tags=entity.tags,
        properties=entity.properties,
        status=entity.status.value,
        source=entity.source,
        confidence=entity.confidence,
        provenance=entity.provenance,
    )


def _orm_to_entity(orm: KnowledgeGraphEntityModel) -> Entity:
    return Entity(
        id=str(orm.id),
        type=EntityType(orm.entity_type),
        name=orm.name,
        aliases=list(orm.aliases or []),
        description=orm.description or "",
        tags=list(orm.tags or []),
        properties=dict(orm.properties or {}),
        status=EntityStatus(orm.status),
        source=orm.source or "manual",
        confidence=float(orm.confidence or 1.0),
        provenance=dict(orm.provenance or {}),
        created_at=orm.created_at.isoformat() if orm.created_at else "",
        updated_at=orm.updated_at.isoformat() if orm.updated_at else "",
    )


def _rel_to_orm(rel: Relationship) -> KnowledgeGraphRelationshipModel:
    return KnowledgeGraphRelationshipModel(
        id=UUID(rel.id),
        source_id=UUID(rel.source_id),
        target_id=UUID(rel.target_id),
        relationship_type=rel.type.value,
        properties=rel.properties,
        weight=rel.weight,
        status=rel.status.value,
        source=rel.source,
        confidence=rel.confidence,
        provenance=rel.provenance,
    )


def _orm_to_rel(orm: KnowledgeGraphRelationshipModel) -> Relationship:
    return Relationship(
        id=str(orm.id),
        source_id=str(orm.source_id),
        target_id=str(orm.target_id),
        type=RelationshipType(orm.relationship_type),
        properties=dict(orm.properties or {}),
        weight=float(orm.weight or 1.0),
        status=RelationshipStatus(orm.status),
        source=orm.source or "manual",
        confidence=float(orm.confidence or 1.0),
        provenance=dict(orm.provenance or {}),
        created_at=orm.created_at.isoformat() if orm.created_at else "",
        updated_at=orm.updated_at.isoformat() if orm.updated_at else "",
    )


class KnowledgeGraphDbRepository(KnowledgeGraphRepository):
    """Postgres-backed persistence for the knowledge graph."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__()
        self._session_factory = session_factory

    async def save_entity(self, entity: Entity) -> Entity:
        orm = _entity_to_orm(entity)
        async with self._session_factory() as session:
            existing = await session.get(KnowledgeGraphEntityModel, UUID(entity.id))
            if existing:
                for key, value in orm.__dict__.items():
                    if key != "_sa_instance_state" and key != "id":
                        setattr(existing, key, value)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                session.add(orm)
            await session.commit()
        await super().save_entity(entity)
        return entity

    async def get_entity(self, entity_id: str) -> Entity | None:
        async with self._session_factory() as session:
            orm = await session.get(KnowledgeGraphEntityModel, UUID(entity_id))
            if orm is None:
                return await super().get_entity(entity_id)
            return _orm_to_entity(orm)

    async def delete_entity(self, entity_id: str) -> bool:
        async with self._session_factory() as session:
            orm = await session.get(KnowledgeGraphEntityModel, UUID(entity_id))
            if orm:
                await session.delete(orm)
                await session.commit()
        return await super().delete_entity(entity_id)

    async def list_entities(
        self,
        entity_type: EntityType | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Entity]:
        async with self._session_factory() as session:
            stmt = select(KnowledgeGraphEntityModel)
            if entity_type:
                stmt = stmt.where(KnowledgeGraphEntityModel.entity_type == entity_type.value)
            stmt = stmt.offset(offset).limit(limit)
            result = await session.execute(stmt)
            orms = result.scalars().all()
            entities = [_orm_to_entity(o) for o in orms]
        if tags:
            entities = [e for e in entities if any(t in e.tags for t in tags)]
        return entities

    async def save_relationship(self, rel: Relationship) -> Relationship:
        orm = _rel_to_orm(rel)
        async with self._session_factory() as session:
            existing = await session.get(KnowledgeGraphRelationshipModel, UUID(rel.id))
            if existing:
                for key, value in orm.__dict__.items():
                    if key != "_sa_instance_state" and key != "id":
                        setattr(existing, key, value)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                session.add(orm)
            await session.commit()
        await super().save_relationship(rel)
        return rel

    async def get_relationship(self, rel_id: str) -> Relationship | None:
        async with self._session_factory() as session:
            orm = await session.get(KnowledgeGraphRelationshipModel, UUID(rel_id))
            if orm is None:
                return await super().get_relationship(rel_id)
            return _orm_to_rel(orm)

    async def delete_relationship(self, rel_id: str) -> bool:
        async with self._session_factory() as session:
            orm = await session.get(KnowledgeGraphRelationshipModel, UUID(rel_id))
            if orm:
                await session.delete(orm)
                await session.commit()
        return await super().delete_relationship(rel_id)

    async def list_relationships(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        rel_type: RelationshipType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Relationship]:
        async with self._session_factory() as session:
            stmt = select(KnowledgeGraphRelationshipModel)
            if source_id:
                stmt = stmt.where(KnowledgeGraphRelationshipModel.source_id == UUID(source_id))
            if target_id:
                stmt = stmt.where(KnowledgeGraphRelationshipModel.target_id == UUID(target_id))
            if rel_type:
                stmt = stmt.where(KnowledgeGraphRelationshipModel.relationship_type == rel_type.value)
            stmt = stmt.offset(offset).limit(limit)
            result = await session.execute(stmt)
            orms = result.scalars().all()
            return [_orm_to_rel(o) for o in orms]
