"""In-memory repository for learning artifacts.

Follows the same dict-based repository pattern used by KnowledgeGraphRepository
and WorkflowRepository. Designed to be swapped for a DB-backed implementation
via the LearningStore ABC.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.learning.base import LearningStore
from app.learning.models import KnowledgeArtifact

logger = logging.getLogger(__name__)


class LearningRepository(LearningStore):
    """In-memory store for KnowledgeArtifacts."""

    def __init__(self) -> None:
        self._store: dict[str, KnowledgeArtifact] = {}

    async def create(self, artifact: KnowledgeArtifact) -> KnowledgeArtifact:
        now = datetime.now(tz=timezone.utc).isoformat()
        if not artifact.created_at:
            artifact.created_at = now
        if not artifact.updated_at:
            artifact.updated_at = now
        self._store[artifact.id] = artifact
        logger.debug("LearningRepository: created artifact %s", artifact.id)
        return artifact

    async def get(self, artifact_id: str) -> KnowledgeArtifact | None:
        return self._store.get(artifact_id)

    async def update(self, artifact: KnowledgeArtifact) -> KnowledgeArtifact | None:
        if artifact.id not in self._store:
            return None
        artifact.updated_at = datetime.now(tz=timezone.utc).isoformat()
        self._store[artifact.id] = artifact
        return artifact

    async def delete(self, artifact_id: str) -> bool:
        if artifact_id in self._store:
            del self._store[artifact_id]
            return True
        return False

    async def list_by_user(
        self,
        user_id: str,
        artifact_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[KnowledgeArtifact]:
        results = []
        for artifact in self._store.values():
            if artifact.user_id != user_id:
                continue
            if artifact_type and artifact.artifact_type != artifact_type:
                continue
            results.append(artifact)
        return results[offset : offset + limit]

    async def list_by_type(
        self,
        artifact_type: str,
        limit: int = 50,
    ) -> list[KnowledgeArtifact]:
        results = [
            a for a in self._store.values()
            if a.artifact_type == artifact_type
        ]
        return results[:limit]

    async def search_by_tags(
        self,
        tags: list[str],
        artifact_type: str | None = None,
        limit: int = 50,
    ) -> list[KnowledgeArtifact]:
        tag_set = set(tags)
        results = []
        for artifact in self._store.values():
            if artifact_type and artifact.artifact_type != artifact_type:
                continue
            if tag_set.intersection(artifact.tags):
                results.append(artifact)
        return results[:limit]

    async def list_all(self, limit: int = 500) -> list[KnowledgeArtifact]:
        return list(self._store.values())[:limit]

    async def count(self) -> int:
        return len(self._store)

    async def count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for artifact in self._store.values():
            counts[artifact.artifact_type] = counts.get(artifact.artifact_type, 0) + 1
        return counts
