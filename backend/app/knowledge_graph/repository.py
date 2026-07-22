"""In-memory repository for knowledge graph persistence."""

from __future__ import annotations

import logging
from typing import Any

from app.knowledge_graph.models import Entity, EntityType, Relationship, RelationshipType

logger = logging.getLogger(__name__)


class KnowledgeGraphRepository:
    """In-memory repository storing entities and relationships.

    Will be backed by a database implementation in v2.
    """

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}
        self._entity_index: dict[EntityType, set[str]] = {}
        self._relationship_type_index: dict[RelationshipType, set[str]] = {}
        self._outgoing: dict[str, set[str]] = {}
        self._incoming: dict[str, set[str]] = {}

    # ── Entity CRUD ───────────────────────────────────────────────

    async def save_entity(self, entity: Entity) -> Entity:
        was_new = entity.id not in self._entities
        self._entities[entity.id] = entity
        self._entity_index.setdefault(entity.type, set()).add(entity.id)
        if was_new:
            logger.debug("Saved entity: %s (%s)", entity.id, entity.type.value)
        return entity

    async def get_entity(self, entity_id: str) -> Entity | None:
        return self._entities.get(entity_id)

    async def delete_entity(self, entity_id: str) -> bool:
        entity = self._entities.pop(entity_id, None)
        if entity is None:
            return False
        idx_set = self._entity_index.get(entity.type)
        if idx_set:
            idx_set.discard(entity_id)
        for rel_id in list(self._outgoing.get(entity_id, set())):
            await self.delete_relationship(rel_id)
        for rel_id in list(self._incoming.get(entity_id, set())):
            await self.delete_relationship(rel_id)
        self._outgoing.pop(entity_id, None)
        self._incoming.pop(entity_id, None)
        logger.debug("Deleted entity: %s", entity_id)
        return True

    async def list_entities(
        self,
        entity_type: EntityType | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Entity]:
        ids: set[str] = set(self._entities.keys())
        if entity_type:
            ids &= self._entity_index.get(entity_type, set())
        result: list[Entity] = []
        for eid in sorted(ids):
            e = self._entities[eid]
            if tags and not any(t in e.tags for t in tags):
                continue
            result.append(e)
        return result[offset: offset + limit]

    async def count_entities(
        self, entity_type: EntityType | None = None,
    ) -> int:
        if entity_type:
            return len(self._entity_index.get(entity_type, set()))
        return len(self._entities)

    async def search_entities(
        self, query: str, limit: int = 20, offset: int = 0,
    ) -> list[Entity]:
        q = query.lower()
        results: list[Entity] = []
        for e in self._entities.values():
            if q in e.name.lower() or q in e.description.lower():
                results.append(e)
                continue
            for alias in e.aliases:
                if q in alias.lower():
                    results.append(e)
                    break
        return results[offset: offset + limit]

    # ── Relationship CRUD ─────────────────────────────────────────

    async def save_relationship(self, rel: Relationship) -> Relationship:
        was_new = rel.id not in self._relationships
        self._relationships[rel.id] = rel
        self._relationship_type_index.setdefault(rel.type, set()).add(rel.id)
        self._outgoing.setdefault(rel.source_id, set()).add(rel.id)
        self._incoming.setdefault(rel.target_id, set()).add(rel.id)
        if was_new:
            logger.debug("Saved relationship: %s (%s)", rel.id, rel.type.value)
        return rel

    async def get_relationship(self, rel_id: str) -> Relationship | None:
        return self._relationships.get(rel_id)

    async def delete_relationship(self, rel_id: str) -> bool:
        rel = self._relationships.pop(rel_id, None)
        if rel is None:
            return False
        self._relationship_type_index.get(rel.type, set()).discard(rel_id)
        self._outgoing.get(rel.source_id, set()).discard(rel_id)
        self._incoming.get(rel.target_id, set()).discard(rel_id)
        logger.debug("Deleted relationship: %s", rel_id)
        return True

    async def list_relationships(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        rel_type: RelationshipType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Relationship]:
        ids: set[str] = set(self._relationships.keys())
        if source_id:
            ids &= self._outgoing.get(source_id, set())
        if target_id:
            ids &= self._incoming.get(target_id, set())
        if rel_type:
            ids &= self._relationship_type_index.get(rel_type, set())
        result = [self._relationships[rid] for rid in sorted(ids)]
        return result[offset: offset + limit]

    async def get_entity_relationships(
        self, entity_id: str, direction: str = "both",
    ) -> list[Relationship]:
        rel_ids: set[str] = set()
        if direction in ("outgoing", "both"):
            rel_ids |= self._outgoing.get(entity_id, set())
        if direction in ("incoming", "both"):
            rel_ids |= self._incoming.get(entity_id, set())
        return [self._relationships[rid] for rid in sorted(rel_ids) if rid in self._relationships]

    # ── Bulk operations ───────────────────────────────────────────

    async def get_all_entities(self) -> list[Entity]:
        return list(self._entities.values())

    async def get_all_relationships(self) -> list[Relationship]:
        return list(self._relationships.values())

    async def clear(self) -> None:
        self._entities.clear()
        self._relationships.clear()
        self._entity_index.clear()
        self._relationship_type_index.clear()
        self._outgoing.clear()
        self._incoming.clear()

    # ── Internal for traverser ────────────────────────────────────

    def get_outgoing_map(self) -> dict[str, list[Relationship]]:
        result: dict[str, list[Relationship]] = {}
        for sid, rel_ids in self._outgoing.items():
            result[sid] = [self._relationships[rid] for rid in rel_ids if rid in self._relationships]
        return result

    def get_incoming_map(self) -> dict[str, list[Relationship]]:
        result: dict[str, list[Relationship]] = {}
        for tid, rel_ids in self._incoming.items():
            result[tid] = [self._relationships[rid] for rid in rel_ids if rid in self._relationships]
        return result

    def get_entity_dict(self) -> dict[str, Entity]:
        return dict(self._entities)
