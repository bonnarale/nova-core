"""Vector Memory module — dense vector storage, search, and lifecycle for NOVA CORE."""

from app.vector_memory.base import (
    ConsolidationStrategy,
    EmbeddingProvider,
    SimilarityEngine,
    VectorMemoryProvider,
    VectorRepository,
)
from app.vector_memory.embeddings import (
    GoogleEmbeddingProvider,
    InMemoryEmbeddingProvider,
    LocalEmbeddingProvider,
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
    get_embedding_provider,
)

from app.vector_memory.engine import VectorMemoryEngine
from app.vector_memory.factory import VectorMemoryFactory
from app.vector_memory.index import VectorIndex
from app.vector_memory.lifecycle import VectorMemoryLifecycle, VectorMemoryState
from app.vector_memory.metrics import VectorMetrics, get_vector_metrics
from app.vector_memory.repository import InMemoryRepository, InMemoryVectorRepository
from app.vector_memory.schemas import (
    MemoryCategory,
    VectorMemoryConfig,
    VectorMemoryDocument,
    VectorMemoryQuery,
    VectorMemoryResult,
    VectorMemorySearchResult,
    VectorMemoryStatistics,
    VectorRecord,
)
from app.vector_memory.search import VectorSearchEngine
from app.vector_memory.similarity import CosineSimilarity, DotProductSimilarity, EuclideanSimilarity
from app.vector_memory.storage import ChromaVectorStorage, InMemoryVectorStorage
from app.vector_memory.tracing import VectorTracer, get_vector_tracer

__all__ = [
    "VectorMemoryProvider",
    "VectorRepository",
    "EmbeddingProvider",
    "SimilarityEngine",
    "ConsolidationStrategy",
    "VectorMemoryEngine",
    "VectorMemoryFactory",
    "VectorIndex",
    "VectorMemoryLifecycle",
    "VectorMemoryState",
    "VectorMetrics",
    "get_vector_metrics",
    "InMemoryRepository",
    "InMemoryVectorRepository",
    "VectorRecord",
    "VectorMemoryQuery",
    "VectorMemoryResult",
    "VectorMemorySearchResult",
    "VectorMemoryStatistics",
    "VectorMemoryConfig",
    "VectorMemoryDocument",
    "MemoryCategory",
    "VectorSearchEngine",
    "CosineSimilarity",
    "DotProductSimilarity",
    "EuclideanSimilarity",
    "ChromaVectorStorage",
    "InMemoryVectorStorage",
    "OllamaEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "GoogleEmbeddingProvider",
    "LocalEmbeddingProvider",
    "get_embedding_provider",
    "VectorTracer",
    "get_vector_tracer",
]
