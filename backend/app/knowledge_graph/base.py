"""Abstract base classes for the Knowledge Graph."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.knowledge_graph.models import Entity, EntityType, GraphPath, Neighborhood, Relationship, RelationshipType


class EntityExtractor(ABC):
    """Extracts entities from unstructured text."""

    @abstractmethod
    async def extract(self, text: str, source: str = "manual") -> list[Entity]:
        ...


class RelationshipExtractor(ABC):
    """Extracts relationships between entities from text."""

    @abstractmethod
    async def extract(
        self, text: str, entities: list[Entity], source: str = "manual"
    ) -> list[Relationship]:
        ...


class EntityDeduplicator(ABC):
    """Finds duplicate entities and suggests merges."""

    @abstractmethod
    async def find_duplicates(self, entities: list[Entity]) -> list[list[Entity]]:
        ...


class EntityMerger(ABC):
    """Merges duplicate entities into a single canonical entity."""

    @abstractmethod
    async def merge(self, entities: list[Entity], canonical: Entity) -> Entity:
        ...


class GraphTraverser(ABC):
    """Traverses the graph to find paths, neighborhoods, and connections."""

    @abstractmethod
    async def find_neighborhood(
        self, entity_id: str, depth: int = 1, max_entities: int = 100
    ) -> Neighborhood:
        ...

    @abstractmethod
    async def find_shortest_path(
        self, source_id: str, target_id: str, max_depth: int = 5
    ) -> GraphPath | None:
        ...

    @abstractmethod
    async def find_connected_entities(
        self, entity_id: str, relationship_types: list[RelationshipType] | None = None,
        direction: str = "both", max_depth: int = 2, limit: int = 100,
    ) -> list[Entity]:
        ...


class GraphSearcher(ABC):
    """Performs semantic and keyword search over the graph."""

    @abstractmethod
    async def search(
        self, query: str, entity_types: list[EntityType] | None = None,
        limit: int = 20, offset: int = 0,
    ) -> list[Entity]:
        ...


class GraphValidator(ABC):
    """Validates the graph's structural integrity."""

    @abstractmethod
    async def validate(self) -> ValidationResult:
        ...

    @abstractmethod
    async def validate_entity(self, entity: Entity) -> ValidationResult:
        ...

    @abstractmethod
    async def validate_relationship(self, relationship: Relationship) -> ValidationResult:
        ...


from app.knowledge_graph.models import ValidationResult
