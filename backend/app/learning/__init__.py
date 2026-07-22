"""Learning Engine module for NOVA CORE.

Automatically learns from every completed execution by extracting
knowledge, storing artifacts, consolidating duplicates, and providing
semantic retrieval.
"""

from app.learning.base import (
    KnowledgeConsolidator,
    KnowledgeExtractor,
    LearningRetriever,
    LearningStore,
    MemoryRanker,
)
from app.learning.consolidator import DefaultConsolidator
from app.learning.engine import LearningEngine
from app.learning.events import (
    artifact_consolidated_event,
    artifact_stored_event,
    execution_learned_event,
    knowledge_extracted_event,
    memory_ranked_event,
    retrieval_performed_event,
)
from app.learning.extractor import DefaultKnowledgeExtractor
from app.learning.factory import LearningEngineFactory
from app.learning.models import (
    ArtifactType,
    ConsolidationResult,
    ExtractedKnowledge,
    KnowledgeArtifact,
    LearningEvent,
    LearningEventType,
    LearningSession,
    MemoryRankSource,
    RankedMemory,
    RetrievalResult,
)
from app.learning.ranker import MultiFactorRanker
from app.learning.repository import LearningRepository
from app.learning.retriever import SemanticRetriever
from app.learning.schemas import (
    ArtifactListResponse,
    ArtifactResponse,
    ArtifactUpdateRequest,
    ConsolidateRequest,
    ExtractKnowledgeRequest,
    LearningEventResponse,
    LearningSessionResponse,
    LearningStatsResponse,
    SearchLearningRequest,
)

__all__ = [
    "KnowledgeConsolidator",
    "KnowledgeExtractor",
    "LearningRetriever",
    "LearningStore",
    "MemoryRanker",
    "DefaultConsolidator",
    "DefaultKnowledgeExtractor",
    "LearningEngine",
    "LearningEngineFactory",
    "MultiFactorRanker",
    "LearningRepository",
    "SemanticRetriever",
    "ArtifactType",
    "MemoryRankSource",
    "LearningEventType",
    "ConsolidationResult",
    "ExtractedKnowledge",
    "KnowledgeArtifact",
    "LearningEvent",
    "LearningSession",
    "RankedMemory",
    "RetrievalResult",
    "artifact_consolidated_event",
    "artifact_stored_event",
    "execution_learned_event",
    "knowledge_extracted_event",
    "memory_ranked_event",
    "retrieval_performed_event",
    "ArtifactListResponse",
    "ArtifactResponse",
    "ArtifactUpdateRequest",
    "ConsolidateRequest",
    "ExtractKnowledgeRequest",
    "LearningEventResponse",
    "LearningSessionResponse",
    "LearningStatsResponse",
    "SearchLearningRequest",
]
