"""KnowledgeGraphEngine — main orchestrator for the Knowledge Graph."""

from __future__ import annotations

import logging
from typing import Any

from app.knowledge_graph.entity import EntityManager
from app.knowledge_graph.events import GraphEventBus
from app.knowledge_graph.extractor import (
    DefaultEntityExtractor,
    DefaultRelationshipExtractor,
)
from app.knowledge_graph.merge import DefaultEntityDeduplicator, DefaultEntityMerger
from app.knowledge_graph.models import (
    Entity,
    EntityStatus,
    EntityType,
    GraphEvent,
    MergeResult,
    Neighborhood,
    Relationship,
    RelationshipType,
    ValidationResult,
)
from app.knowledge_graph.query import DefaultGraphTraverser
from app.knowledge_graph.registry import EntityTypeRegistry, RelationshipTypeRegistry
from app.knowledge_graph.relationship import RelationshipManager
from app.knowledge_graph.repository import KnowledgeGraphRepository
from app.knowledge_graph.search import DefaultGraphSearcher
from app.knowledge_graph.validator import DefaultGraphValidator

logger = logging.getLogger(__name__)


class KnowledgeGraphEngine:
    """Main orchestrator for knowledge graph operations."""

    def __init__(
        self,
        repository: KnowledgeGraphRepository | None = None,
        entity_manager: EntityManager | None = None,
        relationship_manager: RelationshipManager | None = None,
        entity_extractor: DefaultEntityExtractor | None = None,
        relationship_extractor: DefaultRelationshipExtractor | None = None,
        deduplicator: DefaultEntityDeduplicator | None = None,
        merger: DefaultEntityMerger | None = None,
        traverser: DefaultGraphTraverser | None = None,
        searcher: DefaultGraphSearcher | None = None,
        validator: DefaultGraphValidator | None = None,
        entity_type_registry: EntityTypeRegistry | None = None,
        relationship_type_registry: RelationshipTypeRegistry | None = None,
        event_bus: GraphEventBus | None = None,
    ) -> None:
        self._repository = repository or KnowledgeGraphRepository()
        self._entity_manager = entity_manager or EntityManager()
        self._relationship_manager = relationship_manager or RelationshipManager()
        self._entity_extractor = entity_extractor or DefaultEntityExtractor()
        self._relationship_extractor = relationship_extractor or DefaultRelationshipExtractor()
        self._deduplicator = deduplicator or DefaultEntityDeduplicator()
        self._merger = merger or DefaultEntityMerger()
        self._traverser = traverser or DefaultGraphTraverser()
        self._searcher = searcher or DefaultGraphSearcher()
        self._validator = validator or DefaultGraphValidator()
        self._entity_type_registry = entity_type_registry or EntityTypeRegistry()
        self._relationship_type_registry = relationship_type_registry or RelationshipTypeRegistry()
        self._event_bus = event_bus or GraphEventBus()
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._entity_type_registry.register_defaults()
        self._relationship_type_registry.register_defaults()
        await self._sync_data()
        self._initialized = True
        logger.info("KnowledgeGraphEngine initialized")

    async def _sync_data(self) -> None:
        entities = await self._repository.get_all_entities()
        rels = await self._repository.get_all_relationships()
        outgoing = self._repository.get_outgoing_map()
        incoming = self._repository.get_incoming_map()
        self._traverser.set_data(
            self._repository.get_entity_dict(), outgoing, incoming
        )
        self._searcher.set_data(entities)
        self._validator.set_data(entities, rels)

    # ── Entity operations ─────────────────────────────────────────

    async def create_entity(
        self,
        entity_type: str,
        name: str,
        description: str = "",
        aliases: list[str] | None = None,
        tags: list[str] | None = None,
        properties: dict[str, Any] | None = None,
        source: str = "manual",
        confidence: float = 1.0,
        provenance: dict[str, Any] | None = None,
    ) -> Entity:
        etype = EntityType(entity_type.upper())
        entity = await self._entity_manager.create_entity(
            entity_type=etype,
            name=name,
            description=description,
            aliases=aliases,
            tags=tags,
            properties=properties,
            source=source,
            confidence=confidence,
            provenance=provenance,
        )
        await self._repository.save_entity(entity)
        await self._event_bus.publish(
            "entity.created", entity_id=entity.id,
            payload={"type": etype.value, "name": name},
        )
        await self._sync_data()
        logger.info("Created entity: %s (%s)", entity.id, name)
        return entity

    async def get_entity(self, entity_id: str) -> Entity | None:
        return await self._repository.get_entity(entity_id)

    async def update_entity(
        self,
        entity_id: str,
        name: str | None = None,
        description: str | None = None,
        aliases: list[str] | None = None,
        tags: list[str] | None = None,
        properties: dict[str, Any] | None = None,
        confidence: float | None = None,
    ) -> Entity | None:
        entity = await self._repository.get_entity(entity_id)
        if not entity:
            return None
        updated = await self._entity_manager.update_entity(
            entity, name=name, description=description,
            aliases=aliases, tags=tags, properties=properties,
            confidence=confidence,
        )
        await self._repository.save_entity(updated)
        await self._event_bus.publish(
            "entity.updated", entity_id=entity_id,
        )
        await self._sync_data()
        return updated

    async def delete_entity(self, entity_id: str) -> bool:
        entity = await self._repository.get_entity(entity_id)
        if not entity:
            return False
        entity.status = EntityStatus.DELETED
        await self._repository.save_entity(entity)
        await self._event_bus.publish(
            "entity.deleted", entity_id=entity_id,
        )
        await self._sync_data()
        return True

    async def list_entities(
        self,
        entity_type: str | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Entity]:
        etype = EntityType(entity_type.upper()) if entity_type else None
        return await self._repository.list_entities(
            entity_type=etype, tags=tags, limit=limit, offset=offset,
        )

    # ── Relationship operations ───────────────────────────────────

    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
        weight: float = 1.0,
        source: str = "manual",
        confidence: float = 1.0,
        provenance: dict[str, Any] | None = None,
    ) -> Relationship | None:
        source_entity = await self._repository.get_entity(source_id)
        target_entity = await self._repository.get_entity(target_id)
        if not source_entity or not target_entity:
            logger.warning(
                "Cannot create relationship: source=%s target=%s", source_id, target_id
            )
            return None
        rtype = RelationshipType(rel_type.lower())
        rel = await self._relationship_manager.create_relationship(
            source_id=source_id,
            target_id=target_id,
            rel_type=rtype,
            properties=properties,
            weight=weight,
            source=source,
            confidence=confidence,
            provenance=provenance,
        )
        await self._repository.save_relationship(rel)
        await self._event_bus.publish(
            "relationship.created",
            relationship_id=rel.id,
            payload={"source_id": source_id, "target_id": target_id, "type": rtype.value},
        )
        await self._sync_data()
        logger.info("Created relationship: %s -> %s", source_id, target_id)
        return rel

    async def get_relationship(self, rel_id: str) -> Relationship | None:
        return await self._repository.get_relationship(rel_id)

    async def delete_relationship(self, rel_id: str) -> bool:
        rel = await self._repository.get_relationship(rel_id)
        if not rel:
            return False
        await self._repository.delete_relationship(rel_id)
        await self._event_bus.publish(
            "relationship.deleted", relationship_id=rel_id,
        )
        await self._sync_data()
        return True

    async def list_relationships(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        rel_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Relationship]:
        rtype = RelationshipType(rel_type.lower()) if rel_type else None
        return await self._repository.list_relationships(
            source_id=source_id, target_id=target_id,
            rel_type=rtype, limit=limit, offset=offset,
        )

    # ── Entity relationships ──────────────────────────────────────

    async def get_entity_relationships(
        self, entity_id: str, direction: str = "both",
    ) -> list[Relationship]:
        return await self._repository.get_entity_relationships(entity_id, direction)

    # ── Graph queries ─────────────────────────────────────────────

    async def find_neighborhood(
        self, entity_id: str, depth: int = 1, max_entities: int = 100
    ) -> Neighborhood:
        return await self._traverser.find_neighborhood(entity_id, depth, max_entities)

    async def find_shortest_path(
        self, source_id: str, target_id: str, max_depth: int = 5
    ) -> Any:
        return await self._traverser.find_shortest_path(source_id, target_id, max_depth)

    async def find_connected_entities(
        self,
        entity_id: str,
        relationship_types: list[str] | None = None,
        direction: str = "both",
        max_depth: int = 2,
        limit: int = 100,
    ) -> list[Entity]:
        rtypes = (
            [RelationshipType(rt.lower()) for rt in relationship_types]
            if relationship_types
            else None
        )
        return await self._traverser.find_connected_entities(
            entity_id, rtypes, direction, max_depth, limit,
        )

    # ── Search ────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Entity]:
        etypes = (
            [EntityType(et.upper()) for et in entity_types]
            if entity_types
            else None
        )
        return await self._searcher.search(query, etypes, limit, offset)

    # ── Extraction ────────────────────────────────────────────────

    async def extract_from_text(
        self, text: str, source: str = "extraction",
    ) -> dict[str, list[Entity] | list[Relationship]]:
        entities = await self._entity_extractor.extract(text, source)
        saved_entities: list[Entity] = []
        for entity in entities:
            saved = await self._repository.save_entity(entity)
            saved_entities.append(saved)

        relationships = await self._relationship_extractor.extract(text, saved_entities, source)
        saved_rels: list[Relationship] = []
        for rel in relationships:
            saved = await self._repository.save_relationship(rel)
            saved_rels.append(saved)

        await self._event_bus.publish(
            "graph.extracted",
            payload={
                "entities": len(saved_entities),
                "relationships": len(saved_rels),
                "source": source,
            },
        )
        await self._sync_data()
        logger.info(
            "Extracted %d entities and %d relationships",
            len(saved_entities), len(saved_rels),
        )
        return {"entities": saved_entities, "relationships": saved_rels}

    # ── Merge / Deduplication ─────────────────────────────────────

    async def find_duplicates(self) -> list[list[Entity]]:
        entities = await self._repository.get_all_entities()
        return await self._deduplicator.find_duplicates(entities)

    async def merge_entities(
        self, entity_ids: list[str], canonical_id: str | None = None,
    ) -> MergeResult | None:
        entities: list[Entity] = []
        for eid in entity_ids:
            e = await self._repository.get_entity(eid)
            if e:
                entities.append(e)

        if len(entities) < 2:
            return None

        canonical: Entity | None = None
        if canonical_id:
            canonical = await self._repository.get_entity(canonical_id)
        if not canonical:
            canonical = entities[0]

        merged: list[Entity] = [e for e in entities if e.id != canonical.id]

        updated = await self._merger.merge([canonical] + merged, canonical)
        await self._repository.save_entity(updated)

        # Redirect existing relationships to the canonical entity
        rel_count = 0
        for e in merged:
            rels = await self._repository.get_entity_relationships(e.id, "both")
            for rel in rels:
                if rel.source_id == e.id:
                    rel.source_id = canonical.id
                if rel.target_id == e.id:
                    rel.target_id = canonical.id
                await self._repository.save_relationship(rel)
                rel_count += 1
            await self._repository.delete_entity(e.id)

        result = await self._entity_manager.compute_merge_result(canonical, merged)
        result.updated_relationships = rel_count

        await self._event_bus.publish(
            "entities.merged",
            payload={
                "kept_id": result.kept_id,
                "merged_ids": result.merged_ids,
                "updated_relationships": rel_count,
            },
        )
        await self._sync_data()
        logger.info(
            "Merged %d entities into %s (%d relationships updated)",
            len(merged), canonical.id, rel_count,
        )
        return result

    # ── Validation ────────────────────────────────────────────────

    async def validate(self) -> ValidationResult:
        return await self._validator.validate()

    # ── Events ────────────────────────────────────────────────────

    def subscribe(self, event_type: str, handler: Any) -> None:
        self._event_bus.subscribe(event_type, handler)

    def unsubscribe(self, event_type: str, handler: Any) -> None:
        self._event_bus.unsubscribe(event_type, handler)

    # ── Counts ────────────────────────────────────────────────────

    async def count_entities(self, entity_type: str | None = None) -> int:
        etype = EntityType(entity_type.upper()) if entity_type else None
        return await self._repository.count_entities(entity_type=etype)

    async def get_registries(self) -> dict[str, Any]:
        return {
            "entity_types": self._entity_type_registry.list_types(),
            "relationship_types": self._relationship_type_registry.list_types(),
        }
