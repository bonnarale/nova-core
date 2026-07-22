"""Entity management — create, update, get, list, and archive entities."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.knowledge_graph.models import Entity, EntityStatus, EntityType, MergeResult

logger = logging.getLogger(__name__)


class EntityManager:
    """Manages entity lifecycle in the knowledge graph."""

    async def create_entity(
        self,
        entity_type: EntityType,
        name: str,
        description: str = "",
        aliases: list[str] | None = None,
        tags: list[str] | None = None,
        properties: dict[str, Any] | None = None,
        source: str = "manual",
        confidence: float = 1.0,
        provenance: dict[str, Any] | None = None,
    ) -> Entity:
        now = datetime.now(timezone.utc).isoformat()
        return Entity(
            id=str(uuid4()),
            type=entity_type,
            name=name,
            aliases=aliases or [],
            description=description,
            tags=tags or [],
            properties=properties or {},
            status=EntityStatus.ACTIVE,
            source=source,
            confidence=confidence,
            provenance=provenance or {},
            created_at=now,
            updated_at=now,
        )

    async def update_entity(
        self,
        entity: Entity,
        name: str | None = None,
        description: str | None = None,
        aliases: list[str] | None = None,
        tags: list[str] | None = None,
        properties: dict[str, Any] | None = None,
        confidence: float | None = None,
    ) -> Entity:
        if name is not None:
            entity.name = name
        if description is not None:
            entity.description = description
        if aliases is not None:
            entity.aliases = aliases
        if tags is not None:
            entity.tags = tags
        if properties is not None:
            entity.properties = {**entity.properties, **properties}
        if confidence is not None:
            entity.confidence = confidence
        entity.updated_at = datetime.now(timezone.utc).isoformat()
        return entity

    async def archive_entity(self, entity: Entity) -> Entity:
        entity.status = EntityStatus.ARCHIVED
        entity.updated_at = datetime.now(timezone.utc).isoformat()
        return entity

    async def delete_entity(self, entity: Entity) -> Entity:
        entity.status = EntityStatus.DELETED
        entity.updated_at = datetime.now(timezone.utc).isoformat()
        return entity

    async def add_alias(self, entity: Entity, alias: str) -> Entity:
        if alias not in entity.aliases:
            entity.aliases.append(alias)
            entity.updated_at = datetime.now(timezone.utc).isoformat()
        return entity

    async def compute_merge_result(
        self, kept: Entity, merged: list[Entity]
    ) -> MergeResult:
        return MergeResult(
            kept_id=kept.id,
            merged_ids=[e.id for e in merged],
            changes={
                "aliases": list(set(kept.aliases + [a for e in merged for a in e.aliases])),
                "tags": list(set(kept.tags + [t for e in merged for t in e.tags])),
            },
        )
