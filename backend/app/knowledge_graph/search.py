"""Semantic and keyword search over the knowledge graph."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.knowledge_graph.base import GraphSearcher
from app.knowledge_graph.models import Entity, EntityStatus, EntityType

logger = logging.getLogger(__name__)


class DefaultGraphSearcher(GraphSearcher):
    """Keyword and fuzzy search over graph entities."""

    def __init__(self) -> None:
        self._entities: list[Entity] = []

    def set_data(self, entities: list[Entity]) -> None:
        self._entities = list(entities)

    async def search(
        self,
        query: str,
        entity_types: list[EntityType] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Entity]:
        query_lower = query.lower()
        tokens = query_lower.split()
        results: list[tuple[Entity, float]] = []

        for entity in self._entities:
            if entity.status == EntityStatus.DELETED:
                continue
            if entity_types and entity.type not in entity_types:
                continue

            score = self._score_entity(entity, query_lower, tokens)
            if score > 0:
                results.append((entity, score))

        results.sort(key=lambda x: x[1], reverse=True)
        sliced = results[offset: offset + limit]
        return [e for e, _ in sliced]

    def _score_entity(self, entity: Entity, query_lower: str, tokens: list[str]) -> float:
        score = 0.0

        if query_lower in entity.name.lower():
            score += 10.0
        if entity.name.lower().startswith(query_lower):
            score += 5.0

        if query_lower in entity.description.lower():
            score += 3.0

        for token in tokens:
            for alias in entity.aliases:
                if token in alias.lower():
                    score += 4.0
                    break

            for tag in entity.tags:
                if token in tag.lower():
                    score += 2.0
                    break

        for prop_val in entity.properties.values():
            if isinstance(prop_val, str) and query_lower in prop_val.lower():
                score += 1.0

        if entity.confidence > 0:
            score *= entity.confidence

        return score
