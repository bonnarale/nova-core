"""Importance scoring for Long-Term Memory.

Uses a multi-factor scoring model:
- Recency: newer content scores higher
- Access frequency: frequently accessed content scores higher
- Entity richness: more entities = more important
- Source weight: different sources have different base importance
- Content length: very short or very long content may be deprioritized
"""

from __future__ import annotations

import math
import logging
from datetime import datetime, timezone

from app.long_term_memory.base import ImportanceScorer

logger = logging.getLogger(__name__)

SOURCE_WEIGHTS: dict[str, float] = {
    "conversation": 5.0,
    "profile": 8.0,
    "goal": 7.0,
    "task": 6.0,
    "semantic": 4.0,
    "system": 3.0,
    "project": 6.0,
    "agent": 5.0,
    "knowledge": 7.0,
}


class MultiFactorImportanceScorer(ImportanceScorer):
    """Scores memory importance using recency, access count, entities, and source.

    Score range: 0-100 (normalized).
    """

    def __init__(
        self,
        recency_weight: float = 0.3,
        access_weight: float = 0.2,
        entity_weight: float = 0.15,
        source_weight: float = 0.25,
        length_weight: float = 0.1,
    ) -> None:
        self._recency_weight = recency_weight
        self._access_weight = access_weight
        self._entity_weight = entity_weight
        self._source_weight = source_weight
        self._length_weight = length_weight

    async def score(
        self,
        content: str,
        source: str,
        access_count: int = 0,
        entities: list[str] | None = None,
        recency_hours: float | None = None,
    ) -> float:
        recency_score = self._compute_recency(recency_hours)
        access_score = self._compute_access(access_count)
        entity_score = self._compute_entities(entities or [])
        src_score = self._compute_source(source)
        length_score = self._compute_length(content)

        raw = (
            self._recency_weight * recency_score
            + self._access_weight * access_score
            + self._entity_weight * entity_score
            + self._source_weight * src_score
            + self._length_weight * length_score
        )

        normalized = max(0.0, min(100.0, raw * 10.0))
        logger.debug(
            "Importance score=%.1f (recency=%.1f access=%.1f entity=%.1f source=%.1f length=%.1f) for source=%s",
            normalized, recency_score, access_score, entity_score, src_score, length_score, source,
        )
        return round(normalized, 1)

    @staticmethod
    def _compute_recency(recency_hours: float | None) -> float:
        if recency_hours is None:
            return 5.0
        if recency_hours <= 1:
            return 10.0
        if recency_hours <= 24:
            return 8.0
        if recency_hours <= 168:
            return 6.0
        if recency_hours <= 720:
            return 4.0
        return max(1.0, 10.0 - math.log2(recency_hours / 24 + 1) * 2)

    @staticmethod
    def _compute_access(count: int) -> float:
        if count <= 0:
            return 1.0
        return min(10.0, 1.0 + math.log2(count + 1) * 2)

    @staticmethod
    def _compute_entities(entities: list[str]) -> float:
        count = len(entities)
        if count == 0:
            return 1.0
        if count <= 2:
            return 4.0
        if count <= 5:
            return 7.0
        return 10.0

    @staticmethod
    def _compute_source(source: str) -> float:
        return SOURCE_WEIGHTS.get(source, 3.0)

    @staticmethod
    def _compute_length(content: str) -> float:
        length = len(content)
        if length < 20:
            return 2.0
        if length < 100:
            return 5.0
        if length < 500:
            return 8.0
        if length < 2000:
            return 10.0
        return 7.0


class FixedImportanceScorer(ImportanceScorer):
    """Simple scorer that returns a fixed importance value."""

    def __init__(self, fixed_score: float = 50.0) -> None:
        self._fixed = fixed_score

    async def score(
        self,
        content: str,
        source: str,
        access_count: int = 0,
        entities: list[str] | None = None,
        recency_hours: float | None = None,
    ) -> float:
        return self._fixed
