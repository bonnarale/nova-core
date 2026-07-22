"""Comprehensive tests for the Knowledge Graph module."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.knowledge_graph.base import (
    EntityDeduplicator,
    EntityExtractor,
    EntityMerger,
    GraphSearcher,
    GraphTraverser,
    GraphValidator,
    RelationshipExtractor,
)
from app.knowledge_graph.engine import KnowledgeGraphEngine
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
    GraphPath,
    MergeResult,
    Neighborhood,
    Relationship,
    RelationshipStatus,
    RelationshipType,
    ValidationResult,
)
from app.knowledge_graph.query import DefaultGraphTraverser
from app.knowledge_graph.registry import EntityTypeRegistry, RelationshipTypeRegistry
from app.knowledge_graph.relationship import RelationshipManager
from app.knowledge_graph.repository import KnowledgeGraphRepository
from app.knowledge_graph.search import DefaultGraphSearcher
from app.knowledge_graph.validator import DefaultGraphValidator

# ======================================================================
# Domain Models
# ======================================================================


class TestEntity:
    def test_default_construction(self):
        e = Entity()
        assert e.id == ""
        assert e.type == EntityType.USER
        assert e.name == ""
        assert e.aliases == []
        assert e.status == EntityStatus.ACTIVE

    def test_to_dict_includes_all_fields(self):
        e = Entity(
            id="e1", type=EntityType.PROJECT, name="Test Project",
            tags=["important"], confidence=0.95,
        )
        d = e.to_dict()
        assert d["id"] == "e1"
        assert d["type"] == "PROJECT"
        assert d["name"] == "Test Project"
        assert d["confidence"] == 0.95

    def test_all_entity_types(self):
        assert len(EntityType) == 13
        assert EntityType.USER.value == "USER"
        assert EntityType.PROJECT.value == "PROJECT"
        assert EntityType.GOAL.value == "GOAL"
        assert EntityType.MEMORY.value == "MEMORY"


class TestRelationship:
    def test_default_construction(self):
        r = Relationship()
        assert r.id == ""
        assert r.type == RelationshipType.RELATED_TO
        assert r.weight == 1.0

    def test_to_dict(self):
        r = Relationship(
            id="r1", source_id="e1", target_id="e2",
            type=RelationshipType.OWNS, weight=0.8,
        )
        d = r.to_dict()
        assert d["source_id"] == "e1"
        assert d["target_id"] == "e2"
        assert d["type"] == "owns"
        assert d["weight"] == 0.8

    def test_all_relationship_types(self):
        assert len(RelationshipType) == 13
        assert RelationshipType.OWNS.value == "owns"
        assert RelationshipType.DEPENDS_ON.value == "depends_on"


class TestMergeResult:
    def test_construction(self):
        r = MergeResult(kept_id="e1", merged_ids=["e2", "e3"], changes={"aliases": ["foo"]})
        assert r.kept_id == "e1"
        assert len(r.merged_ids) == 2
        assert r.changes["aliases"] == ["foo"]


class TestNeighborhood:
    def test_empty(self):
        n = Neighborhood(depth=2)
        assert n.center is None
        assert n.entities == []
        assert n.depth == 2


class TestGraphPath:
    def test_empty(self):
        p = GraphPath()
        assert p.nodes == []
        assert p.total_cost == 0.0


class TestValidationResult:
    def test_valid_default(self):
        v = ValidationResult()
        assert v.is_valid
        assert v.issues == []


class TestGraphEvent:
    def test_construction(self):
        e = GraphEvent(id="ev1", event_type="entity.created", entity_id="e1")
        assert e.event_type == "entity.created"
        assert e.entity_id == "e1"


# ======================================================================
# ABCs (verify they enforce abstract methods)
# ======================================================================


class TestABCs:
    def test_entity_extractor_is_abstract(self):
        with pytest.raises(TypeError):
            EntityExtractor()  # type: ignore[abstract]

    def test_relationship_extractor_abstract(self):
        with pytest.raises(TypeError):
            RelationshipExtractor()  # type: ignore[abstract]

    def test_entity_deduplicator_abstract(self):
        with pytest.raises(TypeError):
            EntityDeduplicator()  # type: ignore[abstract]

    def test_entity_merger_abstract(self):
        with pytest.raises(TypeError):
            EntityMerger()  # type: ignore[abstract]

    def test_graph_traverser_abstract(self):
        with pytest.raises(TypeError):
            GraphTraverser()  # type: ignore[abstract]

    def test_graph_searcher_abstract(self):
        with pytest.raises(TypeError):
            GraphSearcher()  # type: ignore[abstract]

    def test_graph_validator_abstract(self):
        with pytest.raises(TypeError):
            GraphValidator()  # type: ignore[abstract]


# ======================================================================
# EntityManager
# ======================================================================


class TestEntityManager:
    @pytest.mark.asyncio
    async def test_create_entity(self):
        mgr = EntityManager()
        e = await mgr.create_entity(
            entity_type=EntityType.PROJECT,
            name="My Project",
            tags=["ai"],
        )
        assert e.id
        assert e.type == EntityType.PROJECT
        assert "ai" in e.tags
        assert e.status == EntityStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_update_entity(self):
        mgr = EntityManager()
        e = await mgr.create_entity(EntityType.USER, "Alice")
        updated = await mgr.update_entity(e, name="Alice Smith", tags=["admin"])
        assert updated.name == "Alice Smith"
        assert "admin" in updated.tags

    @pytest.mark.asyncio
    async def test_archive_entity(self):
        mgr = EntityManager()
        e = await mgr.create_entity(EntityType.USER, "test")
        archived = await mgr.archive_entity(e)
        assert archived.status == EntityStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_delete_entity(self):
        mgr = EntityManager()
        e = await mgr.create_entity(EntityType.USER, "test")
        deleted = await mgr.delete_entity(e)
        assert deleted.status == EntityStatus.DELETED

    @pytest.mark.asyncio
    async def test_add_alias(self):
        mgr = EntityManager()
        e = await mgr.create_entity(EntityType.USER, "Alice")
        updated = await mgr.add_alias(e, "Ally")
        assert "Ally" in updated.aliases

    @pytest.mark.asyncio
    async def test_add_alias_duplicate(self):
        mgr = EntityManager()
        e = await mgr.create_entity(EntityType.USER, "Alice")
        await mgr.add_alias(e, "Ally")
        updated = await mgr.add_alias(e, "Ally")
        assert len(updated.aliases) == 1

    @pytest.mark.asyncio
    async def test_compute_merge_result(self):
        mgr = EntityManager()
        e1 = await mgr.create_entity(EntityType.TOPIC, "AI", aliases=["artificial intelligence"])
        e2 = await mgr.create_entity(EntityType.TOPIC, "AI", tags=["ml"])
        result = await mgr.compute_merge_result(e1, [e2])
        assert result.kept_id == e1.id
        assert len(result.merged_ids) == 1
        assert "ml" in result.changes["tags"]


# ======================================================================
# RelationshipManager
# ======================================================================


class TestRelationshipManager:
    @pytest.mark.asyncio
    async def test_create_relationship(self):
        mgr = RelationshipManager()
        r = await mgr.create_relationship(
            source_id="e1", target_id="e2",
            rel_type=RelationshipType.OWNS,
        )
        assert r.id
        assert r.source_id == "e1"
        assert r.type == RelationshipType.OWNS
        assert r.status == RelationshipStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_update_relationship(self):
        mgr = RelationshipManager()
        r = await mgr.create_relationship("e1", "e2", RelationshipType.RELATED_TO)
        updated = await mgr.update_relationship(r, weight=0.5, confidence=0.9)
        assert updated.weight == 0.5
        assert updated.confidence == 0.9

    @pytest.mark.asyncio
    async def test_expire_relationship(self):
        mgr = RelationshipManager()
        r = await mgr.create_relationship("e1", "e2", RelationshipType.KNOWS)
        expired = await mgr.expire_relationship(r)
        assert expired.status == RelationshipStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_delete_relationship(self):
        mgr = RelationshipManager()
        r = await mgr.create_relationship("e1", "e2", RelationshipType.MEMBER_OF)
        deleted = await mgr.delete_relationship(r)
        assert deleted.status == RelationshipStatus.DELETED


# ======================================================================
# DefaultEntityExtractor
# ======================================================================


class TestDefaultEntityExtractor:
    @pytest.mark.asyncio
    async def test_extract_from_text(self):
        extractor = DefaultEntityExtractor()
        entities = await extractor.extract(
            "The user created a project with a goal and assigned a task to an agent.",
        )
        types = {e.type for e in entities}
        assert EntityType.USER in types
        assert EntityType.PROJECT in types

    @pytest.mark.asyncio
    async def test_extract_empty_text(self):
        extractor = DefaultEntityExtractor()
        entities = await extractor.extract("")
        assert entities == []

    @pytest.mark.asyncio
    async def test_extract_skip_duplicates(self):
        extractor = DefaultEntityExtractor()
        entities = await extractor.extract("user user user")
        assert len(entities) == 1


# ======================================================================
# DefaultRelationshipExtractor
# ======================================================================


class TestDefaultRelationshipExtractor:
    @pytest.mark.asyncio
    async def test_extract_relationships(self):
        extractor = DefaultRelationshipExtractor()
        entities = [
            Entity(id="e1", type=EntityType.USER, name="Alice"),
            Entity(id="e2", type=EntityType.PROJECT, name="P1"),
        ]
        rels = await extractor.extract("Alice owns the project P1", entities)
        assert len(rels) >= 1
        assert rels[0].source_id == "e1"

    @pytest.mark.asyncio
    async def test_extract_single_entity(self):
        extractor = DefaultRelationshipExtractor()
        rels = await extractor.extract("hello", [Entity(id="e1", type=EntityType.USER, name="A")])
        assert rels == []


# ======================================================================
# DefaultEntityDeduplicator
# ======================================================================


class TestDefaultEntityDeduplicator:
    @pytest.mark.asyncio
    async def test_find_duplicates_by_name(self):
        dedup = DefaultEntityDeduplicator()
        entities = [
            Entity(id="e1", type=EntityType.TOPIC, name="AI"),
            Entity(id="e2", type=EntityType.TOPIC, name="AI"),
            Entity(id="e3", type=EntityType.USER, name="Bob"),
        ]
        groups = await dedup.find_duplicates(entities)
        assert len(groups) == 1
        assert len(groups[0]) == 2

    @pytest.mark.asyncio
    async def test_find_duplicates_by_alias(self):
        dedup = DefaultEntityDeduplicator()
        entities = [
            Entity(id="e1", type=EntityType.TOPIC, name="AI", aliases=["artificial intelligence"]),
            Entity(id="e2", type=EntityType.TOPIC, name="ai", aliases=["artificial intelligence"]),
        ]
        groups = await dedup.find_duplicates(entities)
        assert len(groups) == 1

    @pytest.mark.asyncio
    async def test_no_duplicates(self):
        dedup = DefaultEntityDeduplicator()
        entities = [
            Entity(id="e1", type=EntityType.USER, name="Alice"),
            Entity(id="e2", type=EntityType.PROJECT, name="P1"),
            Entity(id="e3", type=EntityType.TOPIC, name="AI"),
        ]
        groups = await dedup.find_duplicates(entities)
        assert groups == []


# ======================================================================
# DefaultEntityMerger
# ======================================================================


class TestDefaultEntityMerger:
    @pytest.mark.asyncio
    async def test_merge_entities(self):
        merger = DefaultEntityMerger()
        canonical = Entity(id="e1", type=EntityType.TOPIC, name="AI", confidence=0.8)
        dup = Entity(id="e2", type=EntityType.TOPIC, name="AI", aliases=["artificial intelligence"], tags=["ml"], confidence=0.9)
        merged = await merger.merge([canonical, dup], canonical)
        assert merged.id == "e1"
        assert "artificial intelligence" in merged.aliases
        assert "ml" in merged.tags
        assert merged.confidence == 0.9

    @pytest.mark.asyncio
    async def test_merge_no_dupes(self):
        merger = DefaultEntityMerger()
        e = Entity(id="e1", type=EntityType.USER, name="Alice")
        merged = await merger.merge([e], e)
        assert merged.id == "e1"
        assert merged.name == "Alice"


# ======================================================================
# GraphEventBus
# ======================================================================


class TestGraphEventBus:
    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self):
        bus = GraphEventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("entity.created", handler)
        await bus.publish("entity.created", entity_id="e1")
        assert len(received) == 1
        assert received[0].entity_id == "e1"

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = GraphEventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("entity.created", handler)
        bus.unsubscribe("entity.created", handler)
        await bus.publish("entity.created", entity_id="e1")
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_wildcard_handler(self):
        bus = GraphEventBus()
        received = []

        async def handler(event):
            received.append(event.event_type)

        bus.subscribe("*", handler)
        await bus.publish("entity.created")
        await bus.publish("relationship.deleted")
        assert "entity.created" in received
        assert "relationship.deleted" in received

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_crash(self):
        bus = GraphEventBus()

        async def failing_handler(event):
            raise ValueError("oops")

        async def good_handler(event):
            pass

        bus.subscribe("test", failing_handler)
        bus.subscribe("test", good_handler)
        await bus.publish("test")  # should not raise


# ======================================================================
# EntityTypeRegistry
# ======================================================================


class TestEntityTypeRegistry:
    def test_register_and_list(self):
        reg = EntityTypeRegistry()
        reg.register(EntityType.USER, description="User entity")
        meta = reg.get_metadata(EntityType.USER)
        assert meta["description"] == "User entity"
        assert not reg.is_registered(EntityType.PROJECT)

    def test_register_defaults(self):
        reg = EntityTypeRegistry()
        reg.register_defaults()
        assert reg.is_registered(EntityType.USER)
        assert reg.is_registered(EntityType.MEMORY)
        assert len(reg.list_types()) == len(EntityType)


# ======================================================================
# RelationshipTypeRegistry
# ======================================================================


class TestRelationshipTypeRegistry:
    def test_register_and_list(self):
        reg = RelationshipTypeRegistry()
        reg.register(RelationshipType.OWNS, description="Ownership")
        meta = reg.get_metadata(RelationshipType.OWNS)
        assert meta["description"] == "Ownership"

    def test_register_defaults(self):
        reg = RelationshipTypeRegistry()
        reg.register_defaults()
        assert reg.is_registered(RelationshipType.OWNS)
        assert len(reg.list_types()) == len(RelationshipType)


# ======================================================================
# DefaultGraphTraverser
# ======================================================================


class TestDefaultGraphTraverser:
    def _make_traverser(self):
        traverser = DefaultGraphTraverser()
        entities = {
            "e1": Entity(id="e1", type=EntityType.USER, name="Alice"),
            "e2": Entity(id="e2", type=EntityType.PROJECT, name="P1"),
            "e3": Entity(id="e3", type=EntityType.TASK, name="T1"),
        }
        rels = [
            Relationship(id="r1", source_id="e1", target_id="e2", type=RelationshipType.OWNS),
            Relationship(id="r2", source_id="e2", target_id="e3", type=RelationshipType.DEPENDS_ON),
        ]
        outgoing: dict[str, list[Relationship]] = {
            "e1": [rels[0]],
            "e2": [rels[1]],
        }
        incoming: dict[str, list[Relationship]] = {
            "e2": [rels[0]],
            "e3": [rels[1]],
        }
        traverser.set_data(entities, outgoing, incoming)
        return traverser, entities, rels

    @pytest.mark.asyncio
    async def test_find_neighborhood(self):
        traverser, entities, _ = self._make_traverser()
        hood = await traverser.find_neighborhood("e1", depth=2)
        assert hood.center is not None
        assert hood.center.id == "e1"
        assert len(hood.entities) >= 1

    @pytest.mark.asyncio
    async def test_find_neighborhood_unknown(self):
        traverser, _, _ = self._make_traverser()
        hood = await traverser.find_neighborhood("unknown")
        assert hood.center is None

    @pytest.mark.asyncio
    async def test_find_shortest_path(self):
        traverser, _, _ = self._make_traverser()
        path = await traverser.find_shortest_path("e1", "e3")
        assert path is not None
        assert len(path.nodes) >= 2
        assert len(path.edges) >= 1

    @pytest.mark.asyncio
    async def test_shortest_path_same_node(self):
        traverser, _, _ = self._make_traverser()
        path = await traverser.find_shortest_path("e1", "e1")
        assert path is not None
        assert len(path.nodes) == 1
        assert path.total_cost == 0.0

    @pytest.mark.asyncio
    async def test_shortest_path_no_path(self):
        traverser, _, _ = self._make_traverser()
        path = await traverser.find_shortest_path("e1", "unknown")
        assert path is None

    @pytest.mark.asyncio
    async def test_find_connected_entities(self):
        traverser, _, _ = self._make_traverser()
        connected = await traverser.find_connected_entities("e1")
        assert len(connected) >= 1

    @pytest.mark.asyncio
    async def test_find_connected_unknown(self):
        traverser, _, _ = self._make_traverser()
        connected = await traverser.find_connected_entities("unknown")
        assert connected == []


# ======================================================================
# DefaultGraphSearcher
# ======================================================================


class TestDefaultGraphSearcher:
    def _make_searcher(self):
        searcher = DefaultGraphSearcher()
        searcher.set_data([
            Entity(id="e1", type=EntityType.USER, name="Alice", description="A person", tags=["admin"]),
            Entity(id="e2", type=EntityType.PROJECT, name="Project Alpha", description="AI project"),
            Entity(id="e3", type=EntityType.TOPIC, name="AI", description="Artificial Intelligence"),
        ])
        return searcher

    @pytest.mark.asyncio
    async def test_search_by_name(self):
        searcher = self._make_searcher()
        results = await searcher.search("Alice")
        assert len(results) == 1
        assert results[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_search_by_description(self):
        searcher = self._make_searcher()
        results = await searcher.search("project")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_filter_by_type(self):
        searcher = self._make_searcher()
        results = await searcher.search("AI", entity_types=[EntityType.TOPIC])
        assert len(results) == 1
        assert results[0].type == EntityType.TOPIC

    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        searcher = self._make_searcher()
        results = await searcher.search("")
        assert len(results) >= 0

    @pytest.mark.asyncio
    async def test_search_pagination(self):
        searcher = self._make_searcher()
        results = await searcher.search("A", limit=1, offset=0)
        assert len(results) == 1


# ======================================================================
# DefaultGraphValidator
# ======================================================================


class TestDefaultGraphValidator:
    def _make_validator(self):
        validator = DefaultGraphValidator()
        entities = [
            Entity(id="e1", type=EntityType.USER, name="Alice"),
            Entity(id="e2", type=EntityType.PROJECT, name="P1"),
        ]
        rels = [
            Relationship(id="r1", source_id="e1", target_id="e2", type=RelationshipType.OWNS),
        ]
        validator.set_data(entities, rels)
        return validator

    @pytest.mark.asyncio
    async def test_valid_graph(self):
        validator = self._make_validator()
        result = await validator.validate()
        assert result.is_valid
        assert result.issues == []

    @pytest.mark.asyncio
    async def test_missing_entity_field(self):
        validator = DefaultGraphValidator()
        validator.set_data([Entity(id="", type=EntityType.USER, name="")], [])
        result = await validator.validate()
        assert not result.is_valid
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_orphan_relationship(self):
        validator = DefaultGraphValidator()
        validator.set_data(
            [Entity(id="e1", type=EntityType.USER, name="Alice")],
            [Relationship(id="r1", source_id="e1", target_id="ghost", type=RelationshipType.OWNS)],
        )
        result = await validator.validate()
        assert not result.is_valid
        assert any("non-existent" in i for i in result.issues)

    @pytest.mark.asyncio
    async def test_confidence_out_of_range(self):
        validator = DefaultGraphValidator()
        validator.set_data([Entity(id="e1", type=EntityType.USER, name="A", confidence=1.5)], [])
        result = await validator.validate()
        assert not result.is_valid

    @pytest.mark.asyncio
    async def test_self_loop_warning(self):
        validator = DefaultGraphValidator()
        validator.set_data(
            [Entity(id="e1", type=EntityType.USER, name="Alice")],
            [Relationship(id="r1", source_id="e1", target_id="e1", type=RelationshipType.KNOWS)],
        )
        result = await validator.validate()
        assert result.is_valid
        assert any("self-loop" in w for w in result.warnings)


# ======================================================================
# KnowledgeGraphRepository
# ======================================================================


class TestKnowledgeGraphRepository:
    @pytest.fixture
    def repo(self):
        return KnowledgeGraphRepository()

    @pytest.mark.asyncio
    async def test_save_and_get_entity(self, repo):
        e = Entity(id="e1", type=EntityType.USER, name="Alice")
        saved = await repo.save_entity(e)
        assert saved.id == "e1"
        got = await repo.get_entity("e1")
        assert got is not None
        assert got.name == "Alice"

    @pytest.mark.asyncio
    async def test_missing_entity(self, repo):
        got = await repo.get_entity("nonexistent")
        assert got is None

    @pytest.mark.asyncio
    async def test_delete_entity(self, repo):
        await repo.save_entity(Entity(id="e1", type=EntityType.USER, name="A"))
        deleted = await repo.delete_entity("e1")
        assert deleted
        assert await repo.get_entity("e1") is None

    @pytest.mark.asyncio
    async def test_delete_entity_removes_relationships(self, repo):
        await repo.save_entity(Entity(id="e1", type=EntityType.USER, name="A"))
        await repo.save_entity(Entity(id="e2", type=EntityType.PROJECT, name="P"))
        await repo.save_relationship(Relationship(id="r1", source_id="e1", target_id="e2", type=RelationshipType.OWNS))
        await repo.delete_entity("e1")
        rels = await repo.list_relationships()
        assert len(rels) == 0

    @pytest.mark.asyncio
    async def test_list_entities_by_type(self, repo):
        await repo.save_entity(Entity(id="e1", type=EntityType.USER, name="A"))
        await repo.save_entity(Entity(id="e2", type=EntityType.PROJECT, name="P"))
        users = await repo.list_entities(entity_type=EntityType.USER)
        assert len(users) == 1

    @pytest.mark.asyncio
    async def test_save_and_get_relationship(self, repo):
        await repo.save_entity(Entity(id="e1", type=EntityType.USER, name="A"))
        await repo.save_entity(Entity(id="e2", type=EntityType.PROJECT, name="P"))
        r = Relationship(id="r1", source_id="e1", target_id="e2", type=RelationshipType.OWNS)
        await repo.save_relationship(r)
        got = await repo.get_relationship("r1")
        assert got is not None
        assert got.type == RelationshipType.OWNS

    @pytest.mark.asyncio
    async def test_entity_relationships(self, repo):
        await repo.save_entity(Entity(id="e1", type=EntityType.USER, name="A"))
        await repo.save_entity(Entity(id="e2", type=EntityType.PROJECT, name="P"))
        await repo.save_relationship(Relationship(id="r1", source_id="e1", target_id="e2", type=RelationshipType.OWNS))
        rels = await repo.get_entity_relationships("e1")
        assert len(rels) == 1

    @pytest.mark.asyncio
    async def test_clear(self, repo):
        await repo.save_entity(Entity(id="e1", type=EntityType.USER, name="A"))
        await repo.clear()
        assert await repo.count_entities() == 0


# ======================================================================
# KnowledgeGraphEngine
# ======================================================================


class TestKnowledgeGraphEngine:
    @pytest.fixture
    async def engine(self):
        eng = KnowledgeGraphEngine()
        await eng.initialize()
        return eng

    @pytest.mark.asyncio
    async def test_initialize(self, engine):
        assert engine._initialized

    @pytest.mark.asyncio
    async def test_create_entity(self, engine):
        e = await engine.create_entity("USER", "Alice", tags=["admin"])
        assert e.id
        assert e.name == "Alice"
        assert e.type == EntityType.USER

    @pytest.mark.asyncio
    async def test_create_entity_with_aliases(self, engine):
        e = await engine.create_entity("TOPIC", "AI", aliases=["artificial intelligence"])
        assert "artificial intelligence" in e.aliases

    @pytest.mark.asyncio
    async def test_get_entity(self, engine):
        await engine.create_entity("USER", "Alice")
        e = await engine.create_entity("PROJECT", "P1")
        got = await engine.get_entity(e.id)
        assert got is not None
        assert got.name == "P1"

    @pytest.mark.asyncio
    async def test_get_entity_not_found(self, engine):
        got = await engine.get_entity("nonexistent")
        assert got is None

    @pytest.mark.asyncio
    async def test_update_entity(self, engine):
        e = await engine.create_entity("USER", "Alice")
        updated = await engine.update_entity(e.id, name="Alice Smith")
        assert updated is not None
        assert updated.name == "Alice Smith"

    @pytest.mark.asyncio
    async def test_update_entity_not_found(self, engine):
        updated = await engine.update_entity("nonexistent", name="X")
        assert updated is None

    @pytest.mark.asyncio
    async def test_delete_entity(self, engine):
        e = await engine.create_entity("USER", "Alice")
        deleted = await engine.delete_entity(e.id)
        assert deleted
        entity = await engine.get_entity(e.id)
        assert entity is not None
        assert entity.status == EntityStatus.DELETED

    @pytest.mark.asyncio
    async def test_delete_entity_not_found(self, engine):
        deleted = await engine.delete_entity("nonexistent")
        assert not deleted

    @pytest.mark.asyncio
    async def test_list_entities(self, engine):
        await engine.create_entity("USER", "Alice")
        await engine.create_entity("PROJECT", "P1")
        all_entities = await engine.list_entities()
        assert len(all_entities) == 2

    @pytest.mark.asyncio
    async def test_list_entities_by_type(self, engine):
        await engine.create_entity("USER", "Alice")
        await engine.create_entity("PROJECT", "P1")
        users = await engine.list_entities(entity_type="USER")
        assert len(users) == 1

    @pytest.mark.asyncio
    async def test_create_relationship(self, engine):
        alice = await engine.create_entity("USER", "Alice")
        project = await engine.create_entity("PROJECT", "P1")
        rel = await engine.create_relationship(alice.id, project.id, "owns")
        assert rel is not None
        assert rel.source_id == alice.id
        assert rel.type == RelationshipType.OWNS

    @pytest.mark.asyncio
    async def test_create_relationship_missing_source(self, engine):
        project = await engine.create_entity("PROJECT", "P1")
        rel = await engine.create_relationship("ghost", project.id, "owns")
        assert rel is None

    @pytest.mark.asyncio
    async def test_get_relationship(self, engine):
        alice = await engine.create_entity("USER", "Alice")
        project = await engine.create_entity("PROJECT", "P1")
        rel = await engine.create_relationship(alice.id, project.id, "owns")
        got = await engine.get_relationship(rel.id)
        assert got is not None

    @pytest.mark.asyncio
    async def test_list_relationships(self, engine):
        alice = await engine.create_entity("USER", "Alice")
        p1 = await engine.create_entity("PROJECT", "P1")
        p2 = await engine.create_entity("PROJECT", "P2")
        await engine.create_relationship(alice.id, p1.id, "owns")
        await engine.create_relationship(alice.id, p2.id, "owns")
        rels = await engine.list_relationships()
        assert len(rels) == 2

    @pytest.mark.asyncio
    async def test_get_entity_relationships(self, engine):
        alice = await engine.create_entity("USER", "Alice")
        project = await engine.create_entity("PROJECT", "P1")
        await engine.create_relationship(alice.id, project.id, "owns")
        rels = await engine.get_entity_relationships(alice.id)
        assert len(rels) == 1

    @pytest.mark.asyncio
    async def test_delete_relationship(self, engine):
        alice = await engine.create_entity("USER", "Alice")
        project = await engine.create_entity("PROJECT", "P1")
        rel = await engine.create_relationship(alice.id, project.id, "owns")
        deleted = await engine.delete_relationship(rel.id)
        assert deleted
        assert await engine.get_relationship(rel.id) is None

    @pytest.mark.asyncio
    async def test_find_neighborhood(self, engine):
        alice = await engine.create_entity("USER", "Alice")
        project = await engine.create_entity("PROJECT", "P1")
        await engine.create_relationship(alice.id, project.id, "owns")
        hood = await engine.find_neighborhood(alice.id, depth=2)
        assert hood.center is not None
        assert len(hood.entities) >= 1

    @pytest.mark.asyncio
    async def test_find_shortest_path(self, engine):
        alice = await engine.create_entity("USER", "Alice")
        project = await engine.create_entity("PROJECT", "P1")
        await engine.create_relationship(alice.id, project.id, "owns")
        path = await engine.find_shortest_path(alice.id, project.id)
        assert path is not None
        assert len(path.nodes) >= 2

    @pytest.mark.asyncio
    async def test_find_connected_entities(self, engine):
        alice = await engine.create_entity("USER", "Alice")
        project = await engine.create_entity("PROJECT", "P1")
        await engine.create_relationship(alice.id, project.id, "owns")
        connected = await engine.find_connected_entities(alice.id)
        assert len(connected) >= 1

    @pytest.mark.asyncio
    async def test_search(self, engine):
        await engine.create_entity("USER", "Alice", tags=["admin"])
        await engine.create_entity("TOPIC", "AI")
        results = await engine.search("AI")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_filter_by_type(self, engine):
        await engine.create_entity("USER", "Alice")
        await engine.create_entity("TOPIC", "AI")
        results = await engine.search("AI", entity_types=["TOPIC"])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_extract_from_text(self, engine):
        result = await engine.extract_from_text("The user created a project with a tool")
        assert len(result["entities"]) >= 1

    @pytest.mark.asyncio
    async def test_validate(self, engine):
        await engine.create_entity("USER", "Alice")
        result = await engine.validate()
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_count_entities(self, engine):
        await engine.create_entity("USER", "Alice")
        await engine.create_entity("PROJECT", "P1")
        total = await engine.count_entities()
        assert total == 2

    @pytest.mark.asyncio
    async def test_count_by_type(self, engine):
        await engine.create_entity("USER", "Alice")
        await engine.create_entity("USER", "Bob")
        await engine.create_entity("PROJECT", "P1")
        count = await engine.count_entities(entity_type="USER")
        assert count == 2

    @pytest.mark.asyncio
    async def test_find_duplicates(self, engine):
        await engine.create_entity("TOPIC", "AI")
        await engine.create_entity("TOPIC", "AI")
        groups = await engine.find_duplicates()
        assert len(groups) >= 1

    @pytest.mark.asyncio
    async def test_merge_entities(self, engine):
        e1 = await engine.create_entity("TOPIC", "AI", aliases=["artificial intelligence"])
        e2 = await engine.create_entity("TOPIC", "AI", tags=["ml"])
        result = await engine.merge_entities([e1.id, e2.id], canonical_id=e1.id)
        assert result is not None
        assert result.kept_id == e1.id
        assert e2.id in result.merged_ids

    @pytest.mark.asyncio
    async def test_merge_not_enough_entities(self, engine):
        e1 = await engine.create_entity("USER", "Alice")
        result = await engine.merge_entities([e1.id])
        assert result is None

    @pytest.mark.asyncio
    async def test_get_registries(self, engine):
        registries = await engine.get_registries()
        assert "entity_types" in registries
        assert "relationship_types" in registries

    @pytest.mark.asyncio
    async def test_subscribe(self, engine):
        received = []

        async def handler(event):
            received.append(event)

        engine.subscribe("entity.created", handler)
        await engine.create_entity("USER", "Alice")
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_event_on_create(self, engine):
        events = []

        async def collector(event):
            events.append(event.event_type)

        engine.subscribe("entity.created", collector)
        await engine.create_entity("USER", "Alice")
        assert "entity.created" in events

    @pytest.mark.asyncio
    async def test_event_on_merge(self, engine):
        events = []

        async def collector(event):
            events.append(event.event_type)

        engine.subscribe("entities.merged", collector)
        e1 = await engine.create_entity("TOPIC", "AI")
        e2 = await engine.create_entity("TOPIC", "AI")
        await engine.merge_entities([e1.id, e2.id], canonical_id=e1.id)
        assert "entities.merged" in events


# ======================================================================
# Cognitive Integration
# ======================================================================


class TestKnowledgeGraphCognitiveIntegration:
    def test_intent_type_exists(self):
        assert EntityType

    def test_knowledge_graph_intent(self):
        from app.cognitive.context import IntentType as KGIntentType
        assert KGIntentType.KNOWLEDGE_GRAPH.value == "KNOWLEDGE_GRAPH"

    def test_decision_action_exists(self):
        from app.cognitive.decision import DecisionAction
        assert DecisionAction.QUERY_KNOWLEDGE_GRAPH.value == "QUERY_KNOWLEDGE_GRAPH"

    def test_knowledge_graph_handler_registered(self):
        from app.cognitive.decision import KnowledgeGraphHandler
        from app.cognitive.decision import default_handler_registry as kg_default_registry
        from app.cognitive.context import IntentType as KGIntentType2

        handler = KnowledgeGraphHandler()
        assert KGIntentType2.KNOWLEDGE_GRAPH in handler.handled_intents

        registry = kg_default_registry()
        assert KGIntentType2.KNOWLEDGE_GRAPH in registry

    def test_knowledge_graph_patterns_in_detector(self):
        from app.cognitive.router import RuleBasedIntentDetector as KGRuleBasedDetector
        from app.cognitive.context import IntentType as KGIntentType3

        detector = KGRuleBasedDetector()
        assert KGIntentType3.KNOWLEDGE_GRAPH in detector._PATTERNS
        assert "knowledge graph" in detector._PATTERNS[KGIntentType3.KNOWLEDGE_GRAPH]

    @pytest.mark.asyncio
    async def test_knowledge_graph_engine_execution(self):
        from app.cognitive.context import CognitiveContext, IntentType
        from app.cognitive.decision import CognitiveDecision, DecisionAction

        engine = KnowledgeGraphEngine()
        await engine.initialize()
        await engine.create_entity("USER", "Alice")

        from app.cognitive.engine import CognitiveEngine
        from app.orchestrator.task_manager import TaskManager
        from unittest.mock import AsyncMock

        task_manager = AsyncMock(spec=TaskManager)
        task_manager.list_tasks = AsyncMock(return_value=[])

        cog = CognitiveEngine(
            goal_manager=AsyncMock(),
            task_manager=task_manager,
            agent_manager=AsyncMock(),
            profile_memory=AsyncMock(),
            conversation_memory=AsyncMock(),
            knowledge_graph_engine=engine,
        )

        decision = CognitiveDecision(
            action=DecisionAction.QUERY_KNOWLEDGE_GRAPH,
            handler_name="knowledge_graph",
            payload={"query": "Alice"},
            confidence=0.8,
        )

        result = await cog._execute_knowledge_graph(
            decision,
            CognitiveContext(raw_input="Alice"),
        )
        assert result is not None
        assert "results" in result
        assert result["result_count"] >= 1

    @pytest.mark.asyncio
    async def test_knowledge_graph_no_engine(self):
        from app.cognitive.context import CognitiveContext, IntentType
        from app.cognitive.decision import CognitiveDecision, DecisionAction

        engine = KnowledgeGraphEngine()
        from app.cognitive.engine import CognitiveEngine
        from unittest.mock import AsyncMock

        cog = CognitiveEngine(
            goal_manager=AsyncMock(),
            task_manager=AsyncMock(),
            agent_manager=AsyncMock(),
            profile_memory=AsyncMock(),
            conversation_memory=AsyncMock(),
            knowledge_graph_engine=None,
        )

        decision = CognitiveDecision(
            action=DecisionAction.QUERY_KNOWLEDGE_GRAPH,
            handler_name="knowledge_graph",
            payload={"query": "test"},
            confidence=0.8,
        )

        result = await cog._execute_knowledge_graph(
            decision, CognitiveContext(raw_input="test"),
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_detect_knowledge_graph_intent(self):
        from app.cognitive.router import RuleBasedIntentDetector
        from app.cognitive.context import CognitiveContext, IntentType

        detector = RuleBasedIntentDetector()
        intent, conf = await detector.detect(
            CognitiveContext(raw_input="query the knowledge graph for entities")
        )
        assert intent == IntentType.KNOWLEDGE_GRAPH
        assert conf > 0


# ======================================================================
# Edge Cases
# ======================================================================


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_delete_nonexistent_relationship(self):
        engine = KnowledgeGraphEngine()
        await engine.initialize()
        deleted = await engine.delete_relationship("nonexistent")
        assert not deleted

    @pytest.mark.asyncio
    async def test_extract_from_text_empty(self):
        engine = KnowledgeGraphEngine()
        await engine.initialize()
        result = await engine.extract_from_text("")
        assert result["entities"] == []

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        engine = KnowledgeGraphEngine()
        await engine.initialize()
        results = await engine.search("zzzznonexistent")
        assert results == []

    @pytest.mark.asyncio
    async def test_find_neighborhood_no_entity(self):
        traverser = DefaultGraphTraverser()
        traverser.set_data({}, {}, {})
        hood = await traverser.find_neighborhood("nonexistent")
        assert hood.center is None

    @pytest.mark.asyncio
    async def test_merge_entities_fallback_canonical(self):
        engine = KnowledgeGraphEngine()
        await engine.initialize()
        e1 = await engine.create_entity("TOPIC", "AI")
        e2 = await engine.create_entity("TOPIC", "AI")
        result = await engine.merge_entities([e1.id, e2.id])
        assert result is not None
        assert result.kept_id in (e1.id, e2.id)

    @pytest.mark.asyncio
    async def test_create_relationship_with_extra_properties(self):
        engine = KnowledgeGraphEngine()
        await engine.initialize()
        alice = await engine.create_entity("USER", "Alice")
        project = await engine.create_entity("PROJECT", "P1")
        rel = await engine.create_relationship(
            alice.id, project.id, "owns",
            properties={"role": "owner"},
            weight=0.9,
            confidence=0.95,
        )
        assert rel is not None
        assert rel.properties.get("role") == "owner"
        assert rel.weight == 0.9
        assert rel.confidence == 0.95

    @pytest.mark.asyncio
    async def test_initialize_twice(self):
        engine = KnowledgeGraphEngine()
        await engine.initialize()
        await engine.initialize()  # second call should not fail
        assert engine._initialized
