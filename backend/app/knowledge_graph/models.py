"""Domain dataclasses for the Knowledge Graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EntityType(str, Enum):
    USER = "USER"
    PROJECT = "PROJECT"
    GOAL = "GOAL"
    TASK = "TASK"
    AGENT = "AGENT"
    CONVERSATION = "CONVERSATION"
    DOCUMENT = "DOCUMENT"
    ORGANIZATION = "ORGANIZATION"
    PERSON = "PERSON"
    TOOL = "TOOL"
    SKILL = "SKILL"
    TOPIC = "TOPIC"
    MEMORY = "MEMORY"


class RelationshipType(str, Enum):
    OWNS = "owns"
    CREATED = "created"
    ASSIGNED_TO = "assigned_to"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    REMEMBERS = "remembers"
    KNOWS = "knows"
    MEMBER_OF = "member_of"
    USES = "uses"
    LEARNED_FROM = "learned_from"
    REFERENCES = "references"
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"


class EntityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class RelationshipStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INFERRED = "INFERRED"
    EXPIRED = "EXPIRED"
    DELETED = "DELETED"


@dataclass
class Entity:
    id: str = ""
    type: EntityType = EntityType.USER
    name: str = ""
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    status: EntityStatus = EntityStatus.ACTIVE
    source: str = "manual"
    confidence: float = 1.0
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "aliases": self.aliases,
            "description": self.description,
            "tags": self.tags,
            "status": self.status.value,
            "source": self.source,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Relationship:
    id: str = ""
    source_id: str = ""
    target_id: str = ""
    type: RelationshipType = RelationshipType.RELATED_TO
    properties: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    status: RelationshipStatus = RelationshipStatus.ACTIVE
    source: str = "manual"
    confidence: float = 1.0
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type.value,
            "weight": self.weight,
            "status": self.status.value,
            "source": self.source,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


@dataclass
class GraphQuery:
    entity_id: str = ""
    relationship_types: list[RelationshipType] | None = None
    direction: str = "both"
    max_depth: int = 2
    limit: int = 100
    offset: int = 0


@dataclass
class GraphPath:
    nodes: list[Entity] = field(default_factory=list)
    edges: list[Relationship] = field(default_factory=list)
    total_cost: float = 0.0


@dataclass
class Neighborhood:
    center: Entity | None = None
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    depth: int = 1


@dataclass
class MergeResult:
    kept_id: str = ""
    merged_ids: list[str] = field(default_factory=list)
    updated_relationships: int = 0
    changes: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    is_valid: bool = True
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class GraphEvent:
    id: str = ""
    event_type: str = ""
    entity_id: str | None = None
    relationship_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
