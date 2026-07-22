"""Abstract base classes and protocol interfaces for Long-Term Memory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol

from app.long_term_memory.models import (
    ConsolidationResult,
    ConsolidationSource,
    LifecycleResult,
    LongTermMemory,
    MemoryType,
    RetrievalResult,
)


class MemoryStore(ABC):
    """Interface for persisting LongTermMemory entries."""

    @abstractmethod
    async def create(self, memory: LongTermMemory) -> LongTermMemory:
        ...

    @abstractmethod
    async def get(self, memory_id: str) -> LongTermMemory | None:
        ...

    @abstractmethod
    async def update(self, memory: LongTermMemory) -> LongTermMemory | None:
        ...

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        ...

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        memory_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LongTermMemory]:
        ...

    @abstractmethod
    async def list_by_type(
        self,
        memory_type: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[LongTermMemory]:
        ...

    @abstractmethod
    async def search_by_tags(
        self,
        tags: list[str],
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[LongTermMemory]:
        ...

    @abstractmethod
    async def search_by_entity(
        self, entity: str, limit: int = 50
    ) -> list[LongTermMemory]:
        ...

    @abstractmethod
    async def get_related(
        self, memory_id: str, limit: int = 20
    ) -> list[LongTermMemory]:
        ...


class MemoryRetriever(ABC):
    """Interface for retrieving memories by various criteria."""

    @abstractmethod
    async def search(
        self,
        query: str,
        memory_type: str | None = None,
        user_id: str | None = None,
        limit: int = 10,
    ) -> RetrievalResult:
        ...

    @abstractmethod
    async def search_similar(
        self,
        content: str,
        memory_type: str | None = None,
        limit: int = 10,
        threshold: float = 0.75,
    ) -> RetrievalResult:
        ...


class ConsolidationStrategy(ABC):
    """Interface for consolidation strategies."""

    @abstractmethod
    async def consolidate(
        self, source: ConsolidationSource
    ) -> list[LongTermMemory]:
        ...


class ImportanceScorer(ABC):
    """Interface for computing memory importance scores."""

    @abstractmethod
    async def score(
        self,
        content: str,
        source: str,
        access_count: int = 0,
        entities: list[str] | None = None,
        recency_hours: float | None = None,
    ) -> float:
        ...


class MemorySummarizer(ABC):
    """Interface for generating memory summaries."""

    @abstractmethod
    async def summarize(self, content: str, max_length: int = 200) -> str:
        ...


class LifecyclePolicy(ABC):
    """Interface for memory lifecycle policies."""

    @abstractmethod
    async def age_memories(self) -> int:
        ...

    @abstractmethod
    async def archive_memories(self) -> int:
        ...

    @abstractmethod
    async def purge_deleted(self) -> int:
        ...


class EntityLinker(Protocol):
    """Protocol for linking entities in memory content."""

    async def extract_entities(self, content: str) -> list[str]:
        ...

    async def link_memories(
        self, memory: LongTermMemory, candidates: list[LongTermMemory]
    ) -> list[str]:
        ...


class DeduplicationEngine(ABC):
    """Interface for deduplication logic."""

    @abstractmethod
    async def find_duplicates(
        self,
        content: str,
        memory_type: str | None = None,
        threshold: float = 0.9,
    ) -> list[LongTermMemory]:
        ...
