"""Registries for entity types and relationship types."""

from __future__ import annotations

import logging
from typing import Any

from app.knowledge_graph.models import EntityType, RelationshipType

logger = logging.getLogger(__name__)


class EntityTypeRegistry:
    """Registry for available entity types with metadata."""

    def __init__(self) -> None:
        self._metadata: dict[EntityType, dict[str, Any]] = {}

    def register(
        self,
        entity_type: EntityType,
        description: str = "",
        required_properties: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self._metadata[entity_type] = {
            "description": description,
            "required_properties": required_properties or [],
            "tags": tags or [],
        }
        logger.debug("Registered entity type: %s", entity_type.value)

    def get_metadata(self, entity_type: EntityType) -> dict[str, Any]:
        return self._metadata.get(entity_type, {})

    def list_types(self) -> list[dict[str, Any]]:
        return [
            {"type": et.value, **meta}
            for et, meta in self._metadata.items()
        ]

    def is_registered(self, entity_type: EntityType) -> bool:
        return entity_type in self._metadata

    def register_defaults(self) -> None:
        for et in EntityType:
            self.register(et, description=f"{et.value} entity type")


class RelationshipTypeRegistry:
    """Registry for available relationship types with metadata."""

    def __init__(self) -> None:
        self._metadata: dict[RelationshipType, dict[str, Any]] = {}

    def register(
        self,
        rel_type: RelationshipType,
        description: str = "",
        allowed_source_types: list[EntityType] | None = None,
        allowed_target_types: list[EntityType] | None = None,
        is_directional: bool = True,
    ) -> None:
        self._metadata[rel_type] = {
            "description": description,
            "allowed_source_types": allowed_source_types or [],
            "allowed_target_types": allowed_target_types or [],
            "is_directional": is_directional,
        }
        logger.debug("Registered relationship type: %s", rel_type.value)

    def get_metadata(self, rel_type: RelationshipType) -> dict[str, Any]:
        return self._metadata.get(rel_type, {})

    def list_types(self) -> list[dict[str, Any]]:
        return [
            {"type": rt.value, **meta}
            for rt, meta in self._metadata.items()
        ]

    def is_registered(self, rel_type: RelationshipType) -> bool:
        return rel_type in self._metadata

    def register_defaults(self) -> None:
        for rt in RelationshipType:
            self.register(rt, description=f"{rt.value} relationship type", is_directional=True)
