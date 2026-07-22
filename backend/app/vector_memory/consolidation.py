"""Consolidation strategies — deduplication, merge, and stale cleanup."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.vector_memory.base import ConsolidationReport, ConsolidationStrategy
from app.vector_memory.schemas import VectorRecord
from app.vector_memory.similarity import CosineSimilarity

logger = logging.getLogger(__name__)


class DefaultConsolidationStrategy(ConsolidationStrategy):
    """Default consolidation strategy with duplicate detection, merging, and stale cleanup."""

    def __init__(
        self,
        similarity_engine: CosineSimilarity | None = None,
        duplicate_threshold: float = 0.95,
        stale_days: int = 90,
        importance_threshold: float = 0.1,
    ) -> None:
        self._similarity = similarity_engine or CosineSimilarity()
        self._duplicate_threshold = duplicate_threshold
        self._stale_days = stale_days
        self._importance_threshold = importance_threshold

    async def consolidate(
        self,
        records: list[VectorRecord],
        **kwargs: Any,
    ) -> ConsolidationReport:
        report = ConsolidationReport()

        duplicates = await self.find_duplicates(records, self._duplicate_threshold)
        for group in duplicates:
            if len(group) < 2:
                continue
            keeper = max(group, key=lambda r: (r.confidence, r.importance, r.timestamp))
            merged_tags: set[str] = set()
            merged_metadata: dict[str, Any] = {}
            for rec in group:
                if rec.vector_id != keeper.vector_id:
                    merged_tags.update(rec.tags)
                    merged_metadata.update(rec.metadata)
                    report.duplicates_removed += 1
            keeper.tags = list(set(keeper.tags) | merged_tags)
            keeper.metadata.update(merged_metadata)
            keeper.importance = max(keeper.importance, *[r.importance for r in group])
            report.items_merged += 1
            report.details.append({
                "action": "merged",
                "keeper_id": keeper.vector_id,
                "merged_ids": [r.vector_id for r in group if r.vector_id != keeper.vector_id],
            })

        stale = self._find_stale(records)
        for rec in stale:
            report.stale_removed += 1
            report.details.append({
                "action": "stale_removed",
                "vector_id": rec.vector_id,
                "timestamp": rec.timestamp.isoformat(),
            })

        logger.info(
            "Consolidation complete: %d duplicates removed, %d items merged, %d stale removed",
            report.duplicates_removed, report.items_merged, report.stale_removed,
        )
        return report

    async def find_duplicates(
        self,
        records: list[VectorRecord],
        threshold: float = 0.95,
    ) -> list[list[VectorRecord]]:
        groups: list[list[VectorRecord]] = []
        assigned: set[str] = set()

        for i, rec_a in enumerate(records):
            if rec_a.vector_id in assigned or not rec_a.embedding:
                continue
            group = [rec_a]
            assigned.add(rec_a.vector_id)

            for rec_b in records[i + 1:]:
                if rec_b.vector_id in assigned or not rec_b.embedding:
                    continue
                if rec_b.content == rec_a.content:
                    sim = 1.0
                else:
                    sim = self._similarity.compute(rec_a.embedding, rec_b.embedding)

                if sim >= threshold:
                    group.append(rec_b)
                    assigned.add(rec_b.vector_id)

            if len(group) > 1:
                groups.append(group)

        return groups

    def _find_stale(self, records: list[VectorRecord]) -> list[VectorRecord]:
        now = datetime.now(timezone.utc)
        stale: list[VectorRecord] = []
        for rec in records:
            age = (now - rec.timestamp).days
            if age >= self._stale_days and rec.importance < self._importance_threshold:
                stale.append(rec)
        return stale
