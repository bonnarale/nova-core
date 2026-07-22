"""LearningEngine — the main orchestrator for the Learning Engine module.

Automatically learns from every completed execution by:
  1. Extracting knowledge from execution data.
  2. Storing artifacts via the LearningStore.
  3. Running consolidation to merge duplicates.
  4. Emitting learning events on the shared EventBus.
  5. Providing semantic retrieval for past learnings.
"""

from __future__ import annotations

import logging
from typing import Any

from app.learning.base import (
    KnowledgeConsolidator,
    KnowledgeExtractor,
    LearningRetriever,
    LearningStore,
    MemoryRanker,
)
from app.learning.consolidator import DefaultConsolidator
from app.learning.events import (
    artifact_consolidated_event,
    artifact_stored_event,
    execution_learned_event,
    knowledge_extracted_event,
    retrieval_performed_event,
)
from app.learning.extractor import DefaultKnowledgeExtractor
from app.learning.models import (
    ConsolidationResult,
    ExtractedKnowledge,
    KnowledgeArtifact,
    LearningEvent,
    LearningSession,
    RankedMemory,
    RetrievalResult,
)
from app.learning.ranker import MultiFactorRanker
from app.learning.repository import LearningRepository
from app.learning.retriever import SemanticRetriever

logger = logging.getLogger(__name__)


class LearningEngine:
    """Main orchestrator — coordinates extraction, storage, consolidation,
    ranking, and retrieval of knowledge artifacts.

    Pluggable via constructor-injected strategies:
      - extractor (KnowledgeExtractor)
      - ranker (MemoryRanker)
      - consolidator (KnowledgeConsolidator)
      - retriever (LearningRetriever)
      - store (LearningStore)

    Integrates with the shared EventBus to emit learning lifecycle events.
    """

    def __init__(
        self,
        store: LearningStore | None = None,
        extractor: KnowledgeExtractor | None = None,
        ranker: MemoryRanker | None = None,
        consolidator: KnowledgeConsolidator | None = None,
        retriever: LearningRetriever | None = None,
        event_bus: Any | None = None,
        embedder: Any | None = None,
        vector_store: Any | None = None,
        auto_consolidate: bool = True,
        consolidation_interval: int = 10,
    ) -> None:
        self._store = store or LearningRepository()
        self._extractor = extractor or DefaultKnowledgeExtractor()
        self._ranker = ranker or MultiFactorRanker(embedder=embedder)
        self._consolidator = consolidator or DefaultConsolidator()
        self._retriever = retriever or SemanticRetriever(
            store=self._store,
            embedder=embedder,
            vector_store=vector_store,
        )
        self._event_bus = event_bus
        self._auto_consolidate = auto_consolidate
        self._consolidation_interval = consolidation_interval
        self._session_counter = 0
        self._sessions: dict[str, LearningSession] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def store(self) -> LearningStore:
        return self._store

    @property
    def extractor(self) -> KnowledgeExtractor:
        return self._extractor

    @property
    def ranker(self) -> MemoryRanker:
        return self._ranker

    @property
    def consolidator(self) -> KnowledgeConsolidator:
        return self._consolidator

    @property
    def retriever(self) -> LearningRetriever:
        return self._retriever

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    async def learn_from_execution(
        self,
        execution_data: dict[str, Any],
        task_data: dict[str, Any] | None = None,
    ) -> LearningSession:
        """Full learning cycle: extract → store → consolidate → emit events.

        This is the primary entry point called automatically when a task
        execution completes.
        """
        session = self._create_session(execution_data, task_data)

        try:
            session.status = "extracting"
            extracted = await self._extractor.extract(execution_data, task_data)
            session.artifacts_extracted = len(extracted.artifacts)

            if extracted.artifacts:
                await self._emit(
                    knowledge_extracted_event(
                        execution_id=extracted.execution_id,
                        artifact_count=len(extracted.artifacts),
                        task_id=extracted.task_id,
                        user_id=extracted.artifacts[0].user_id if extracted.artifacts else None,
                    )
                )

            session.status = "storing"
            stored_ids: list[str] = []
            for artifact in extracted.artifacts:
                created = await self._store.create(artifact)
                stored_ids.append(created.id)
                session.artifacts_stored += 1
                await self._emit(
                    artifact_stored_event(
                        artifact_id=created.id,
                        artifact_type=created.artifact_type,
                        source_execution_id=created.source_execution_id,
                    )
                )

            if self._auto_consolidate and session.artifacts_stored > 0:
                self._session_counter += 1
                if self._session_counter % self._consolidation_interval == 0:
                    session.status = "consolidating"
                    result = await self.run_consolidation()
                    session.consolidations_run += 1
                    if result.duplicates_removed > 0:
                        await self._emit(
                            artifact_consolidated_event(
                                merged_count=result.merged_count,
                                duplicates_removed=result.duplicates_removed,
                                artifacts_affected=result.artifacts_affected,
                            )
                        )

            session.status = "completed"
            await self._emit(
                execution_learned_event(
                    execution_id=extracted.execution_id,
                    session_id=session.session_id,
                    artifacts_extracted=session.artifacts_extracted,
                    artifacts_stored=session.artifacts_stored,
                )
            )

        except Exception as exc:
            logger.exception("LearningEngine.learn_from_execution failed: %s", exc)
            session.status = "failed"
            session.error = str(exc)

        self._sessions[session.session_id] = session
        return session

    async def search(
        self,
        query: str,
        user_id: str | None = None,
        artifact_type: str | None = None,
        limit: int = 10,
    ) -> RetrievalResult:
        """Search for learned knowledge using semantic retrieval."""
        result = await self._retriever.retrieve(
            query=query,
            user_id=user_id,
            artifact_type=artifact_type,
            limit=limit,
        )
        await self._emit(
            retrieval_performed_event(
                query=query,
                result_count=result.total,
                user_id=user_id,
            )
        )
        return result

    async def rank(
        self,
        artifacts: list[KnowledgeArtifact] | None = None,
        query: str = "",
        user_id: str | None = None,
    ) -> list[RankedMemory]:
        """Rank artifacts by multi-factor relevance."""
        if artifacts is None:
            if user_id:
                artifacts = await self._store.list_by_user(user_id)
            else:
                artifacts = await self._store.list_all()

        return await self._ranker.rank(artifacts, query=query)

    async def run_consolidation(
        self,
        user_id: str | None = None,
        artifact_type: str | None = None,
    ) -> ConsolidationResult:
        """Run consolidation on all (or filtered) artifacts."""
        if user_id:
            artifacts = await self._store.list_by_user(user_id, artifact_type=artifact_type, limit=500)
        else:
            artifacts = await self._store.list_all(limit=500)

        return await self._consolidator.consolidate(artifacts)

    async def get_artifact(self, artifact_id: str) -> KnowledgeArtifact | None:
        """Retrieve a single artifact by ID."""
        return await self._store.get(artifact_id)

    async def list_artifacts(
        self,
        user_id: str | None = None,
        artifact_type: str | None = None,
        limit: int = 50,
    ) -> list[KnowledgeArtifact]:
        """List artifacts with optional filters."""
        if user_id:
            return await self._store.list_by_user(user_id, artifact_type=artifact_type, limit=limit)
        if artifact_type:
            return await self._store.list_by_type(artifact_type, limit=limit)
        return await self._store.list_all(limit=limit)

    async def delete_artifact(self, artifact_id: str) -> bool:
        """Delete a single artifact."""
        return await self._store.delete(artifact_id)

    async def stats(self) -> dict[str, Any]:
        """Return learning statistics."""
        return {
            "total_artifacts": await self._store.count(),
            "artifacts_by_type": await self._store.count_by_type(),
            "total_sessions": len(self._sessions),
        }

    def get_session(self, session_id: str) -> LearningSession | None:
        """Retrieve a learning session by ID."""
        return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _create_session(
        self,
        execution_data: dict[str, Any],
        task_data: dict[str, Any] | None,
    ) -> LearningSession:
        import uuid
        session_id = str(uuid.uuid4())
        return LearningSession(
            session_id=session_id,
            execution_id=execution_data.get("id"),
            task_id=(task_data or {}).get("id"),
            user_id=(task_data or {}).get("user_id") or execution_data.get("user_id"),
        )

    async def _emit(self, event: LearningEvent) -> None:
        if self._event_bus is not None:
            try:
                await self._event_bus.emit(event.event_type, event.payload)
            except Exception:
                logger.debug("Failed to emit learning event: %s", event.event_type)
