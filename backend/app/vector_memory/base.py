"""Base abstractions for Vector Memory — ABCs for all pluggable components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from app.vector_memory.schemas import (
    MemoryCategory,
    VectorMemoryQuery,
    VectorMemoryResult,
    VectorMemorySearchResult,
    VectorRecord,
)


# ---------------------------------------------------------------------------
# VectorMemoryProvider
# ---------------------------------------------------------------------------

class VectorMemoryProvider(ABC):
    """Top-level ABC for the Vector Memory subsystem."""

    @abstractmethod
    async def store(self, record: VectorRecord) -> VectorMemoryResult:
        ...

    @abstractmethod
    async def update(self, record: VectorRecord) -> VectorMemoryResult:
        ...

    @abstractmethod
    async def delete(self, vector_id: str) -> bool:
        ...

    @abstractmethod
    async def retrieve(self, vector_id: str) -> Optional[VectorRecord]:
        ...

    @abstractmethod
    async def search(self, query: VectorMemoryQuery) -> VectorMemorySearchResult:
        ...

    @abstractmethod
    async def similarity_search(
        self,
        embedding: list[float],
        top_k: int = 10,
        threshold: Optional[float] = None,
        memory_category: Optional[MemoryCategory] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> VectorMemorySearchResult:
        ...

    @abstractmethod
    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 10,
        threshold: Optional[float] = None,
        memory_category: Optional[MemoryCategory] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        semantic_weight: float = 0.7,
    ) -> VectorMemorySearchResult:
        ...

    @abstractmethod
    async def consolidate(self, **kwargs: Any) -> dict[str, Any]:
        ...

    @abstractmethod
    async def reindex(self, vector_ids: Optional[list[str]] = None) -> dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# VectorRepository
# ---------------------------------------------------------------------------

class VectorRepository(ABC):
    """Abstract vector repository — stores and retrieves vector records."""

    @abstractmethod
    async def add(self, records: list[VectorRecord]) -> int:
        ...

    @abstractmethod
    async def update(self, records: list[VectorRecord]) -> int:
        ...

    @abstractmethod
    async def delete(self, vector_ids: list[str]) -> int:
        ...

    @abstractmethod
    async def get(self, vector_id: str) -> Optional[VectorRecord]:
        ...

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        memory_category: Optional[MemoryCategory] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        ...

    @abstractmethod
    async def list_by_session(
        self,
        session_id: str,
        memory_category: Optional[MemoryCategory] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        ...

    @abstractmethod
    async def list_by_category(
        self,
        memory_category: MemoryCategory,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        ...

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> list[VectorRecord]:
        ...

    @abstractmethod
    async def count(self) -> int:
        ...

    @abstractmethod
    async def count_by_category(self) -> dict[str, int]:
        ...

    @abstractmethod
    async def get_all_ids(self) -> list[str]:
        ...

    @abstractmethod
    async def search_by_tags(self, tags: list[str], limit: int = 50) -> list[VectorRecord]:
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# EmbeddingProvider
# ---------------------------------------------------------------------------

class EmbeddingProvider(ABC):
    """Abstract embedding provider — generates vector embeddings from text."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        ...

    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# SimilarityEngine
# ---------------------------------------------------------------------------

class SimilarityEngine(ABC):
    """Abstract similarity engine — computes similarity between vectors."""

    @abstractmethod
    def compute(self, a: list[float], b: list[float]) -> float:
        ...

    @abstractmethod
    def batch_compute(self, query: list[float], candidates: list[list[float]]) -> list[float]:
        ...


# ---------------------------------------------------------------------------
# ConsolidationStrategy
# ---------------------------------------------------------------------------

@dataclass
class ConsolidationReport:
    duplicates_removed: int = 0
    items_merged: int = 0
    stale_removed: int = 0
    items_updated: int = 0
    details: list[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.details is None:
            self.details = []


class ConsolidationStrategy(ABC):
    """Abstract consolidation strategy — deduplicates, merges, and cleans up vectors."""

    @abstractmethod
    async def consolidate(
        self,
        records: list[VectorRecord],
        **kwargs: Any,
    ) -> ConsolidationReport:
        ...

    @abstractmethod
    async def find_duplicates(
        self,
        records: list[VectorRecord],
        threshold: float = 0.95,
    ) -> list[list[VectorRecord]]:
        ...
