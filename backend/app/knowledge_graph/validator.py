"""Graph validation — structural integrity checks."""

from __future__ import annotations

import logging
from typing import Any

from app.knowledge_graph.base import GraphValidator
from app.knowledge_graph.models import (
    Entity,
    EntityStatus,
    EntityType,
    Relationship,
    RelationshipStatus,
    RelationshipType,
    ValidationResult,
)

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS_ENTITY = {"id", "type", "name"}
_REQUIRED_FIELDS_RELATIONSHIP = {"id", "source_id", "target_id", "type"}


class DefaultGraphValidator(GraphValidator):
    """Default graph validator checking structural integrity."""

    def __init__(self) -> None:
        self._entities: list[Entity] = []
        self._relationships: list[Relationship] = []

    def set_data(
        self, entities: list[Entity], relationships: list[Relationship]
    ) -> None:
        self._entities = list(entities)
        self._relationships = list(relationships)

    async def validate(self) -> ValidationResult:
        issues: list[str] = []
        warnings: list[str] = []

        entity_ids = {e.id for e in self._entities if e.status != EntityStatus.DELETED}

        for i, e in enumerate(self._entities):
            vr = await self.validate_entity(e)
            issues.extend(vr.issues)
            warnings.extend(vr.warnings)

        for i, r in enumerate(self._relationships):
            vr = await self.validate_relationship(r)
            issues.extend(vr.issues)
            warnings.extend(vr.warnings)

            if r.status != RelationshipStatus.DELETED:
                if r.source_id not in entity_ids:
                    issues.append(
                        f"Relationship '{r.id}' references non-existent source '{r.source_id}'"
                    )
                if r.target_id not in entity_ids:
                    issues.append(
                        f"Relationship '{r.id}' references non-existent target '{r.target_id}'"
                    )

        if not issues and not warnings:
            return ValidationResult(is_valid=True)

        return ValidationResult(is_valid=len(issues) == 0, issues=issues, warnings=warnings)

    async def validate_entity(self, entity: Entity) -> ValidationResult:
        issues: list[str] = []
        warnings: list[str] = []

        for field in _REQUIRED_FIELDS_ENTITY:
            val = getattr(entity, field, None)
            if val is None or (isinstance(val, str) and not val):
                issues.append(f"Entity missing required field '{field}'")

        if entity.confidence < 0.0 or entity.confidence > 1.0:
            issues.append(f"Entity '{entity.id}' confidence out of range")

        if entity.name and len(entity.name) > 500:
            warnings.append(f"Entity '{entity.id}' name is very long")

        return ValidationResult(is_valid=len(issues) == 0, issues=issues, warnings=warnings)

    async def validate_relationship(
        self, relationship: Relationship
    ) -> ValidationResult:
        issues: list[str] = []
        warnings: list[str] = []

        for field in _REQUIRED_FIELDS_RELATIONSHIP:
            val = getattr(relationship, field, None)
            if val is None or (isinstance(val, str) and not val):
                issues.append(f"Relationship missing required field '{field}'")

        if relationship.weight < 0.0 or relationship.weight > 1.0:
            warnings.append(f"Relationship '{relationship.id}' weight out of range [0, 1]")

        if relationship.confidence < 0.0 or relationship.confidence > 1.0:
            issues.append(f"Relationship '{relationship.id}' confidence out of range")

        if relationship.source_id == relationship.target_id:
            warnings.append(f"Relationship '{relationship.id}' is a self-loop")

        return ValidationResult(is_valid=len(issues) == 0, issues=issues, warnings=warnings)
