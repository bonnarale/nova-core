"""Knowledge consolidator — merges and deduplicates knowledge artifacts.

Analyses pairs of artifacts for content similarity and merges them when
they are sufficiently overlapping, preserving the higher-quality data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from app.learning.base import KnowledgeConsolidator
from app.learning.models import ConsolidationResult, KnowledgeArtifact

logger = logging.getLogger(__name__)

_DEFAULT_SIMILARITY_THRESHOLD = 0.70


class DefaultConsolidator(KnowledgeConsolidator):
    """Merges duplicate knowledge artifacts based on content similarity.

    Algorithm:
      1. Pairwise similarity comparison using ``SequenceMatcher``.
      2. Union of tags from both artifacts.
      3. The artifact with the higher ``importance_score`` survives.
      4. Merged artifact receives combined content (shorter one appended
         if meaningfully different).
    """

    def __init__(
        self,
        threshold: float = _DEFAULT_SIMILARITY_THRESHOLD,
    ) -> None:
        self._threshold = threshold

    async def consolidate(
        self,
        artifacts: list[KnowledgeArtifact],
    ) -> ConsolidationResult:
        if len(artifacts) < 2:
            return ConsolidationResult(consolidation_method="default_pairwise")

        merge_groups: list[list[int]] = []
        merged_indices: set[int] = set()

        for i in range(len(artifacts)):
            if i in merged_indices:
                continue
            group = [i]
            for j in range(i + 1, len(artifacts)):
                if j in merged_indices:
                    continue
                sim = self._similarity(
                    artifacts[i].content, artifacts[j].content
                )
                if sim >= self._threshold:
                    group.append(j)
                    merged_indices.add(j)
            if len(group) > 1:
                merge_groups.append(group)
                merged_indices.update(group)

        affected_ids: list[str] = []
        total_merged = 0
        total_removed = 0

        for group in merge_groups:
            surviving_idx = min(group, key=lambda idx: -artifacts[idx].importance_score)
            surviving = artifacts[surviving_idx]

            all_tags: list[str] = list(surviving.tags)
            all_content_parts: list[str] = [surviving.content]

            for idx in group:
                if idx == surviving_idx:
                    continue
                other = artifacts[idx]
                other_content = other.content
                if not self._is_substring(other_content, surviving.content):
                    all_content_parts.append(other_content)
                for tag in other.tags:
                    if tag not in all_tags:
                        all_tags.append(tag)
                total_merged += 1
                affected_ids.append(other.id)

            surviving.tags = all_tags
            surviving.content = " | ".join(all_content_parts)
            surviving.updated_at = datetime.now(tz=timezone.utc).isoformat()
            surviving.importance_score = min(
                surviving.importance_score + 0.05 * total_merged, 1.0
            )

        total_removed = len(affected_ids)

        logger.debug(
            "Consolidation complete: %d groups, %d duplicates removed",
            len(merge_groups), total_removed,
        )

        return ConsolidationResult(
            merged_count=len(merge_groups),
            duplicates_removed=total_removed,
            artifacts_affected=affected_ids,
            consolidation_method="default_pairwise",
        )

    def _similarity(self, text_a: str, text_b: str) -> float:
        if not text_a or not text_b:
            return 0.0
        return SequenceMatcher(None, text_a.lower(), text_b.lower()).ratio()

    @staticmethod
    def _is_substring(short: str, long: str) -> bool:
        if not short or not long:
            return False
        return short.lower() in long.lower()
