"""Pydantic schemas for the Knowledge Graph API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Entity Schemas ────────────────────────────────────────────────

class EntityCreate(BaseModel):
    type: str
    name: str
    description: str = ""
    aliases: list[str] = []
    tags: list[str] = []
    properties: dict[str, Any] = {}
    source: str = "manual"
    confidence: float = 1.0


class EntityUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    aliases: list[str] | None = None
    tags: list[str] | None = None
    properties: dict[str, Any] | None = None
    confidence: float | None = None


class EntityResponse(BaseModel):
    id: str
    type: str
    name: str
    aliases: list[str] = []
    description: str = ""
    tags: list[str] = []
    status: str = "ACTIVE"
    source: str = "manual"
    confidence: float = 1.0
    properties: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    created_at: str = ""
    updated_at: str = ""


class EntityListResponse(BaseModel):
    entities: list[EntityResponse]
    total: int


# ── Relationship Schemas ──────────────────────────────────────────

class RelationshipCreate(BaseModel):
    source_id: str
    target_id: str
    type: str
    properties: dict[str, Any] = {}
    weight: float = 1.0
    source: str = "manual"
    confidence: float = 1.0


class RelationshipUpdate(BaseModel):
    properties: dict[str, Any] | None = None
    weight: float | None = None
    confidence: float | None = None


class RelationshipResponse(BaseModel):
    id: str
    source_id: str
    target_id: str
    type: str
    weight: float = 1.0
    status: str = "ACTIVE"
    source: str = "manual"
    confidence: float = 1.0
    properties: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    created_at: str = ""
    updated_at: str = ""


class RelationshipListResponse(BaseModel):
    relationships: list[RelationshipResponse]
    total: int


# ── Query / Search Schemas ────────────────────────────────────────

class SearchQuery(BaseModel):
    query: str
    entity_types: list[str] | None = None
    limit: int = 20
    offset: int = 0


class GraphQueryRequest(BaseModel):
    entity_id: str
    relationship_types: list[str] | None = None
    direction: str = "both"
    max_depth: int = 2
    limit: int = 100


class NeighborhoodResponse(BaseModel):
    center: EntityResponse | None = None
    entities: list[EntityResponse] = []
    relationships: list[RelationshipResponse] = []
    depth: int = 1


class PathResponse(BaseModel):
    nodes: list[EntityResponse] = []
    edges: list[RelationshipResponse] = []
    total_cost: float = 0.0


# ── Merge / Validation ────────────────────────────────────────────

class MergeRequest(BaseModel):
    entity_ids: list[str] = Field(..., min_length=2)
    canonical_id: str = ""


class MergeResponse(BaseModel):
    kept_id: str
    merged_ids: list[str] = []
    changes: dict[str, Any] = {}


class ValidationResponse(BaseModel):
    is_valid: bool = True
    issues: list[str] = []
    warnings: list[str] = []


# ── Extraction ────────────────────────────────────────────────────

class ExtractRequest(BaseModel):
    text: str
    source: str = "extraction"


class ExtractResponse(BaseModel):
    entities: list[EntityResponse] = []
    relationships: list[RelationshipResponse] = []


# ── Event ─────────────────────────────────────────────────────────

class EventResponse(BaseModel):
    id: str
    event_type: str
    entity_id: str | None = None
    relationship_id: str | None = None
    payload: dict[str, Any] = {}
    timestamp: str = ""
