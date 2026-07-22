"""Factory for constructing a fully-wired LearningEngine instance.

Follows the same DI/factory pattern used across NOVA CORE modules.
"""

from __future__ import annotations

import logging
from typing import Any

from app.learning.consolidator import DefaultConsolidator
from app.learning.engine import LearningEngine
from app.learning.extractor import DefaultKnowledgeExtractor
from app.learning.ranker import MultiFactorRanker
from app.learning.repository import LearningRepository
from app.learning.retriever import SemanticRetriever

logger = logging.getLogger(__name__)


class LearningEngineFactory:
    """Creates LearningEngine instances with appropriate default strategies.

    Usage::

        engine = LearningEngineFactory.create(event_bus=bus, embedder=emb)
    """

    @staticmethod
    def create(
        event_bus: Any | None = None,
        embedder: Any | None = None,
        vector_store: Any | None = None,
        store: Any | None = None,
        extractor: Any | None = None,
        ranker: Any | None = None,
        consolidator: Any | None = None,
        retriever: Any | None = None,
        auto_consolidate: bool = True,
        consolidation_interval: int = 10,
    ) -> LearningEngine:
        """Build and return a fully configured LearningEngine."""
        _store = store or LearningRepository()
        _extractor = extractor or DefaultKnowledgeExtractor()
        _ranker = ranker or MultiFactorRanker(embedder=embedder)
        _consolidator = consolidator or DefaultConsolidator()
        _retriever = retriever or SemanticRetriever(
            store=_store,
            embedder=embedder,
            vector_store=vector_store,
        )

        engine = LearningEngine(
            store=_store,
            extractor=_extractor,
            ranker=_ranker,
            consolidator=_consolidator,
            retriever=_retriever,
            event_bus=event_bus,
            embedder=embedder,
            vector_store=vector_store,
            auto_consolidate=auto_consolidate,
            consolidation_interval=consolidation_interval,
        )

        logger.info("LearningEngine created via factory")
        return engine
