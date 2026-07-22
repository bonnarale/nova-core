"""Long-Term Memory module for NOVA CORE.

Consolidates all persistent knowledge about users, projects, agents,
and the system into durable, retrievable memories.
"""

from app.long_term_memory.base import (
    ConsolidationStrategy,
    DeduplicationEngine,
    ImportanceScorer,
    LifecyclePolicy,
    MemoryRetriever,
    MemoryStore,
    MemorySummarizer,
)
from app.long_term_memory.consolidator import (
    ContentHashDeduplicator,
    DefaultConsolidationStrategy,
)
from app.long_term_memory.importance import (
    FixedImportanceScorer,
    MultiFactorImportanceScorer,
)
from app.long_term_memory.lifecycle import DefaultLifecyclePolicy
from app.long_term_memory.manager import LongTermMemoryManager
from app.long_term_memory.models import (
    ConsolidationResult,
    ConsolidationSource,
    LifecycleResult,
    LongTermMemory,
    MemoryStatus,
    MemoryType,
    RetrievalResult,
)
from app.long_term_memory.retriever import (
    SemanticMemoryRetriever,
    StoreRetriever,
)
from app.long_term_memory.schemas import (
    ConsolidateRequest,
    ConsolidateResponse,
    LifecycleResponse,
    MemoryCreate,
    MemoryResponse,
    MemorySearchResult,
    MemoryUpdate,
    StatsResponse,
)
from app.long_term_memory.summarizer import (
    ExtractiveMemorySummarizer,
    TruncationSummarizer,
)

__all__ = [
    "LongTermMemoryManager",
    "LongTermMemory",
    "MemoryType",
    "MemoryStatus",
    "ConsolidationSource",
    "ConsolidationResult",
    "RetrievalResult",
    "LifecycleResult",
    "MemoryStore",
    "MemoryRetriever",
    "ConsolidationStrategy",
    "ImportanceScorer",
    "MemorySummarizer",
    "DeduplicationEngine",
    "LifecyclePolicy",
    "MultiFactorImportanceScorer",
    "FixedImportanceScorer",
    "DefaultConsolidationStrategy",
    "ContentHashDeduplicator",
    "DefaultLifecyclePolicy",
    "SemanticMemoryRetriever",
    "StoreRetriever",
    "ExtractiveMemorySummarizer",
    "TruncationSummarizer",
    "MemoryCreate",
    "MemoryUpdate",
    "MemoryResponse",
    "MemorySearchResult",
    "ConsolidateRequest",
    "ConsolidateResponse",
    "LifecycleResponse",
    "StatsResponse",
]
