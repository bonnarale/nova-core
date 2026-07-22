"""Memory lifecycle management — aging, archiving, and purging.

Implements configurable policies for:
- Aging: decrease importance of active memories over time
- Archiving: move low-importance, old memories to ARCHIVED status
- Purging: permanently delete DELETED memories past a threshold
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from app.long_term_memory.base import LifecyclePolicy
from app.long_term_memory.importance import MultiFactorImportanceScorer
from app.long_term_memory.models import LifecycleResult, MemoryStatus

logger = logging.getLogger(__name__)


class DefaultLifecyclePolicy(LifecyclePolicy):
    """Default lifecycle policy with configurable thresholds.

    Aging decreases importance by 5% per week for inactive memories.
    Archiving moves memories to ARCHIVED when importance < 15 and age > 90 days.
    Purging deletes memories that have been DELETED for more than 30 days.
    """

    def __init__(
        self,
        store: Any,
        age_decay_rate: float = 0.05,
        age_interval_days: int = 7,
        archive_importance_threshold: float = 15.0,
        archive_age_days: int = 90,
        purge_age_days: int = 30,
        batch_size: int = 100,
    ) -> None:
        self._store = store
        self._age_decay_rate = age_decay_rate
        self._age_interval_days = age_interval_days
        self._archive_importance_threshold = archive_importance_threshold
        self._archive_age_days = archive_age_days
        self._purge_age_days = purge_age_days
        self._batch_size = batch_size

    async def age_memories(self) -> int:
        """Decrease importance of active memories last accessed over N days ago."""
        aged_count = 0
        candidates = await self._store.list_aging(
            age_days=self._age_interval_days,
            limit=self._batch_size,
        )
        for mem in candidates:
            if mem.importance_score is None:
                continue
            decay = mem.importance_score * self._age_decay_rate
            new_score = max(0.0, mem.importance_score - decay)
            mem.importance_score = round(new_score, 1)
            mem.updated_at = datetime.now(tz=timezone.utc).isoformat()
            try:
                await self._store.update(mem)
                aged_count += 1
            except Exception:
                logger.exception("Failed to age memory %s", mem.id)
        if aged_count:
            logger.info("Aged %d memories (decay=%.0f%%)", aged_count, self._age_decay_rate * 100)
        return aged_count

    async def archive_memories(self) -> int:
        """Archive active memories below importance threshold and past age threshold."""
        archived_count = 0
        candidates = await self._store.list_archivable(
            min_age_days=self._archive_age_days,
            importance_below=int(self._archive_importance_threshold),
            limit=self._batch_size,
        )
        for mem in candidates:
            mem.status = MemoryStatus.ARCHIVED.value
            mem.archived_at = datetime.now(tz=timezone.utc).isoformat()
            mem.updated_at = mem.archived_at
            try:
                await self._store.update(mem)
                archived_count += 1
            except Exception:
                logger.exception("Failed to archive memory %s", mem.id)
        if archived_count:
            logger.info("Archived %d memories", archived_count)
        return archived_count

    async def purge_deleted(self) -> int:
        """Permanently delete memories in DELETED status past the purge threshold."""
        purged_count = 0
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=self._purge_age_days)
        cutoff_str = cutoff.isoformat()

        deleted = await self._store.list_by_type(
            MemoryStatus.DELETED.value, limit=self._batch_size
        )
        for mem in deleted:
            deleted_at = mem.updated_at or mem.archived_at or mem.created_at
            if deleted_at and deleted_at < cutoff_str:
                try:
                    await self._store.delete(mem.id)
                    purged_count += 1
                except Exception:
                    logger.exception("Failed to purge memory %s", mem.id)
        if purged_count:
            logger.info("Purged %d deleted memories", purged_count)
        return purged_count
