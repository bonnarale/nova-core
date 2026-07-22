"""Relationship management — create, update, get, list relationships."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.knowledge_graph.models import Relationship, RelationshipStatus, RelationshipType

logger = logging.getLogger(__name__)


class RelationshipManager:
    """Manages relationship lifecycle in the knowledge graph."""

    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType,
        properties: dict[str, Any] | None = None,
        weight: float = 1.0,
        source: str = "manual",
        confidence: float = 1.0,
        provenance: dict[str, Any] | None = None,
    ) -> Relationship:
        now = datetime.now(timezone.utc).isoformat()
        return Relationship(
            id=str(uuid4()),
            source_id=source_id,
            target_id=target_id,
            type=rel_type,
            properties=properties or {},
            weight=weight,
            status=RelationshipStatus.ACTIVE,
            source=source,
            confidence=confidence,
            provenance=provenance or {},
            created_at=now,
            updated_at=now,
        )

    async def update_relationship(
        self,
        rel: Relationship,
        properties: dict[str, Any] | None = None,
        weight: float | None = None,
        confidence: float | None = None,
    ) -> Relationship:
        if properties is not None:
            rel.properties = {**rel.properties, **properties}
        if weight is not None:
            rel.weight = weight
        if confidence is not None:
            rel.confidence = confidence
        rel.updated_at = datetime.now(timezone.utc).isoformat()
        return rel

    async def expire_relationship(self, rel: Relationship) -> Relationship:
        rel.status = RelationshipStatus.EXPIRED
        rel.updated_at = datetime.now(timezone.utc).isoformat()
        return rel

    async def delete_relationship(self, rel: Relationship) -> Relationship:
        rel.status = RelationshipStatus.DELETED
        rel.updated_at = datetime.now(timezone.utc).isoformat()
        return rel
