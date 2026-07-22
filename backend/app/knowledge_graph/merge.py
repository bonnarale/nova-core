"""Entity deduplication and merging logic."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.knowledge_graph.base import EntityDeduplicator, EntityMerger
from app.knowledge_graph.models import Entity, EntityStatus, EntityType, MergeResult

logger = logging.getLogger(__name__)


class DefaultEntityDeduplicator(EntityDeduplicator):
    """Finds duplicate entities by name, aliases, or property overlap."""

    def __init__(self, name_threshold: float = 0.85, alias_threshold: float = 0.9):
        self._name_threshold = name_threshold
        self._alias_threshold = alias_threshold

    async def find_duplicates(self, entities: list[Entity]) -> list[list[Entity]]:
        groups: list[list[Entity]] = []
        used: set[str] = set()

        for i, a in enumerate(entities):
            if a.id in used:
                continue
            group: list[Entity] = [a]
            used.add(a.id)
            for j, b in enumerate(entities):
                if j <= i or b.id in used:
                    continue
                if self._is_duplicate(a, b):
                    group.append(b)
                    used.add(b.id)
            if len(group) > 1:
                groups.append(group)
        return groups

    def _is_duplicate(self, a: Entity, b: Entity) -> bool:
        if a.type != b.type:
            return False
        if a.name.lower() == b.name.lower():
            return True
        for alias in a.aliases:
            if alias.lower() in [aa.lower() for aa in b.aliases]:
                return True
            if alias.lower() == b.name.lower():
                return True
        return False


class DefaultEntityMerger(EntityMerger):
    """Merges a list of entities into one canonical entity."""

    async def merge(self, entities: list[Entity], canonical: Entity) -> Entity:
        now = datetime.now(timezone.utc).isoformat()

        merged_aliases: list[str] = []
        merged_tags: list[str] = []
        merged_properties: dict[str, Any] = {}
        max_confidence = canonical.confidence
        merged_descriptions: list[str] = []

        for e in entities:
            if e.id == canonical.id:
                continue
            for alias in e.aliases:
                if alias not in merged_aliases and alias != canonical.name:
                    merged_aliases.append(alias)
            for tag in e.tags:
                if tag not in merged_tags:
                    merged_tags.append(tag)
            merged_properties.update(e.properties)
            if e.confidence > max_confidence:
                max_confidence = e.confidence
            if e.description and e.description != canonical.description:
                merged_descriptions.append(e.description)

        canonical.aliases = list(set(canonical.aliases + merged_aliases))
        canonical.tags = list(set(canonical.tags + merged_tags))
        canonical.properties = {**canonical.properties, **merged_properties}
        canonical.confidence = max_confidence
        if merged_descriptions:
            canonical.description = canonical.description or merged_descriptions[0]
        canonical.updated_at = now

        logger.info(
            "Merged %d entities into '%s' (id=%s)",
            len(entities), canonical.name, canonical.id,
        )
        return canonical
