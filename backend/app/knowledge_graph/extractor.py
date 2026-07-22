"""Default entity and relationship extractors using pattern matching."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.knowledge_graph.base import EntityExtractor, RelationshipExtractor
from app.knowledge_graph.models import Entity, EntityStatus, EntityType, Relationship, RelationshipType

logger = logging.getLogger(__name__)

ENTITY_PATTERNS: list[tuple[str, EntityType]] = [
    (r'\buser\b', EntityType.USER),
    (r'\bproject\b', EntityType.PROJECT),
    (r'\bgoal\b', EntityType.GOAL),
    (r'\btask\b', EntityType.TASK),
    (r'\bagent\b', EntityType.AGENT),
    (r'\bconversation\b', EntityType.CONVERSATION),
    (r'\bdocument\b', EntityType.DOCUMENT),
    (r'\borganization\b', EntityType.ORGANIZATION),
    (r'\bperson\b', EntityType.PERSON),
    (r'\btool\b', EntityType.TOOL),
    (r'\bskill\b', EntityType.SKILL),
    (r'\btopic\b', EntityType.TOPIC),
    (r'\bknowledge\b', EntityType.MEMORY),
]

RELATIONSHIP_PATTERNS: list[tuple[re.Pattern, RelationshipType, int, int]] = [
    (re.compile(r'\b(owns?|owned)\b', re.IGNORECASE), RelationshipType.OWNS, 0, 1),
    (re.compile(r'\b(create[d]?)\b', re.IGNORECASE), RelationshipType.CREATED, 0, 1),
    (re.compile(r'\b(assign[s]?|assigned)\b', re.IGNORECASE), RelationshipType.ASSIGNED_TO, 0, 1),
    (re.compile(r'\bdepends?\b', re.IGNORECASE), RelationshipType.DEPENDS_ON, 0, 1),
    (re.compile(r'\brelat[es]\b', re.IGNORECASE), RelationshipType.RELATED_TO, 0, 1),
    (re.compile(r'\bremembers?\b', re.IGNORECASE), RelationshipType.REMEMBERS, 0, 1),
    (re.compile(r'\bknow[s]?\b', re.IGNORECASE), RelationshipType.KNOWS, 0, 1),
    (re.compile(r'\b(member|belongs?)\b', re.IGNORECASE), RelationshipType.MEMBER_OF, 0, 1),
    (re.compile(r'\buse[sd]?\b', re.IGNORECASE), RelationshipType.USES, 0, 1),
    (re.compile(r'\blearn[s]?\b', re.IGNORECASE), RelationshipType.LEARNED_FROM, 0, 1),
    (re.compile(r'\brefer[s]?\b', re.IGNORECASE), RelationshipType.REFERENCES, 0, 1),
    (re.compile(r'\b(parent|father|mother)\b', re.IGNORECASE), RelationshipType.PARENT_OF, 0, 1),
    (re.compile(r'\b(child|children)\b', re.IGNORECASE), RelationshipType.CHILD_OF, 0, 1),
]

_ENTITY_NAME_RE = re.compile(r'\b[A-Z][a-zA-Z]+\b')


def _extract_simple_name(text: str, keyword: str, idx: int) -> str:
    words = text.split()
    for offset in range(idx + 1, min(idx + 4, len(words))):
        if words[offset] and words[offset][0].isupper():
            return words[offset].strip(".,;:!?")
    return keyword.capitalize()


class DefaultEntityExtractor(EntityExtractor):
    """Extracts entities by matching known entity type keywords."""

    def __init__(self, min_confidence: float = 0.6):
        self._min_confidence = min_confidence

    async def extract(self, text: str, source: str = "manual") -> list[Entity]:
        now = datetime.now(timezone.utc).isoformat()
        entities: list[Entity] = []
        seen: set[str] = set()
        words = text.split()

        for i, word in enumerate(words):
            clean = word.strip(".,;:!?").lower()
            for pattern, etype in ENTITY_PATTERNS:
                m = re.search(pattern, word.lower())
                if m and clean not in seen:
                    seen.add(clean)
                    name = _extract_simple_name(text, clean, i)
                    entities.append(Entity(
                        id=str(uuid4()),
                        type=etype,
                        name=name,
                        description=f"Extracted from text as {etype.value}",
                        tags=[etype.value.lower(), source],
                        status=EntityStatus.ACTIVE,
                        source=source,
                        confidence=self._min_confidence,
                        created_at=now,
                        updated_at=now,
                    ))
                    break
        return entities


class DefaultRelationshipExtractor(RelationshipExtractor):
    """Extracts simple relationships between entities based on keyword patterns."""

    def __init__(self, min_confidence: float = 0.5):
        self._min_confidence = min_confidence

    async def extract(
        self, text: str, entities: list[Entity], source: str = "manual"
    ) -> list[Relationship]:
        if len(entities) < 2:
            return []

        now = datetime.now(timezone.utc).isoformat()
        relationships: list[Relationship] = []
        seen: set[tuple[str, str, str]] = set()

        for i, entity_a in enumerate(entities):
            for entity_b in entities[i + 1:]:
                for pattern, rtype, _, _ in RELATIONSHIP_PATTERNS:
                    if pattern.search(text):
                        key = (entity_a.id, entity_b.id, rtype.value)
                        if key not in seen:
                            seen.add(key)
                            relationships.append(Relationship(
                                id=str(uuid4()),
                                source_id=entity_a.id,
                                target_id=entity_b.id,
                                type=rtype,
                                weight=0.7,
                                source=source,
                                confidence=self._min_confidence,
                                created_at=now,
                                updated_at=now,
                            ))
                        break
        return relationships
