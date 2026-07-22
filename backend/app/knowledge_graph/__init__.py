"""Knowledge Graph — structured entity-relationship knowledge layer."""

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

__all__ = [
    "KnowledgeGraphEngine",
    "EntityManager",
    "RelationshipManager",
    "KnowledgeGraphRepository",
    "GraphEventBus",
    "EntityTypeRegistry",
    "RelationshipTypeRegistry",
    "DefaultEntityExtractor",
    "DefaultRelationshipExtractor",
    "DefaultEntityDeduplicator",
    "DefaultEntityMerger",
    "DefaultGraphTraverser",
    "DefaultGraphSearcher",
    "DefaultGraphValidator",
    "Entity",
    "Relationship",
    "EntityType",
    "RelationshipType",
    "EntityStatus",
    "RelationshipStatus",
    "GraphEvent",
    "GraphPath",
    "Neighborhood",
    "MergeResult",
    "ValidationResult",
    "EntityExtractor",
    "RelationshipExtractor",
    "EntityDeduplicator",
    "EntityMerger",
    "GraphTraverser",
    "GraphSearcher",
    "GraphValidator",
]
