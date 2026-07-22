"""Memory ranker — scores and ranks knowledge artifacts by multiple factors.

Implements a weighted multi-factor scoring strategy:
  - Recency: how recently the artifact was created
  - Importance: the artifact's intrinsic importance score
  - Relevance: textual similarity to the query
  - Frequency: how often the artifact has been accessed
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

from app.learning.base import MemoryRanker
from app.learning.models import KnowledgeArtifact, MemoryRankSource, RankedMemory

logger = logging.getLogger(__name__)

_DEFAULT_WEIGHTS: dict[str, float] = {
    MemoryRankSource.RECENCY.value: 0.25,
    MemoryRankSource.IMPORTANCE.value: 0.35,
    MemoryRankSource.RELEVANCE.value: 0.30,
    MemoryRankSource.FREQUENCY.value: 0.10,
}


class MultiFactorRanker(MemoryRanker):
    """Ranks artifacts using a configurable weighted multi-factor model.

    Weights can be overridden via the constructor. Each factor is normalised
    to [0, 1] before weighting.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        embedder: Any | None = None,
    ) -> None:
        self._weights = weights or dict(_DEFAULT_WEIGHTS)
        self._embedder = embedder

    async def rank(
        self,
        artifacts: list[KnowledgeArtifact],
        query: str = "",
        context: dict[str, Any] | None = None,
    ) -> list[RankedMemory]:
        if not artifacts:
            return []

        scored: list[RankedMemory] = []
        for artifact in artifacts:
            factors = await self._compute_factors(artifact, query)
            score = sum(
                factors.get(k, 0.0) * self._weights.get(k, 0.0)
                for k in self._weights
            )
            scored.append(RankedMemory(
                artifact=artifact,
                score=round(score, 4),
                rank_factors=factors,
            ))

        scored.sort(key=lambda rm: rm.score, reverse=True)
        logger.debug("Ranked %d artifacts, top score=%.3f", len(scored), scored[0].score if scored else 0.0)
        return scored

    async def _compute_factors(
        self,
        artifact: KnowledgeArtifact,
        query: str,
    ) -> dict[str, float]:
        recency = self._recency_score(artifact)
        importance = self._importance_score(artifact)
        relevance = await self._relevance_score(artifact, query)
        frequency = self._frequency_score(artifact)

        return {
            MemoryRankSource.RECENCY.value: recency,
            MemoryRankSource.IMPORTANCE.value: importance,
            MemoryRankSource.RELEVANCE.value: relevance,
            MemoryRankSource.FREQUENCY.value: frequency,
        }

    @staticmethod
    def _recency_score(artifact: KnowledgeArtifact) -> float:
        if not artifact.created_at:
            return 0.5
        try:
            created = datetime.fromisoformat(artifact.created_at)
            now = datetime.now(tz=timezone.utc)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            hours = max((now - created).total_seconds() / 3600, 0)
            return max(1.0 - math.log1p(hours) / 10, 0.0)
        except (ValueError, TypeError):
            return 0.5

    @staticmethod
    def _importance_score(artifact: KnowledgeArtifact) -> float:
        return min(max(artifact.importance_score, 0.0), 1.0)

    @staticmethod
    def _frequency_score(artifact: KnowledgeArtifact) -> float:
        return min(math.log1p(artifact.access_count) / 5, 1.0)

    async def _relevance_score(
        self,
        artifact: KnowledgeArtifact,
        query: str,
    ) -> float:
        if not query:
            return 0.5

        query_lower = query.lower()
        content_lower = artifact.content.lower()
        summary_lower = artifact.summary.lower() if artifact.summary else ""

        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        summary_words = set(summary_lower.split())

        overlap_content = query_words & content_words
        overlap_summary = query_words & summary_words

        if query_words:
            content_sim = len(overlap_content) / len(query_words)
            summary_sim = len(overlap_summary) / len(query_words)
        else:
            content_sim = 0.0
            summary_sim = 0.0

        tag_overlap = len(
            set(query_lower.split()) & set(t.lower() for t in artifact.tags)
        )
        tag_sim = min(tag_overlap / max(len(query_words), 1), 1.0)

        return min((content_sim * 0.5 + summary_sim * 0.3 + tag_sim * 0.2), 1.0)
