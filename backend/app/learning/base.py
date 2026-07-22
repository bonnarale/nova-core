"""Abstract base classes and protocol interfaces for the Learning Engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.learning.models import (
    ArtifactType,
    ConsolidationResult,
    ExecutionOutcome,
    ExtractedKnowledge,
    KnowledgeArtifact,
    RankedMemory,
    RetrievalResult,
)


class LearningStore(ABC):
    """Interface for persisting learning artifacts."""

    @abstractmethod
    async def create(self, artifact: KnowledgeArtifact) -> KnowledgeArtifact:
        ...

    @abstractmethod
    async def get(self, artifact_id: str) -> KnowledgeArtifact | None:
        ...

    @abstractmethod
    async def update(self, artifact: KnowledgeArtifact) -> KnowledgeArtifact | None:
        ...

    @abstractmethod
    async def delete(self, artifact_id: str) -> bool:
        ...

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        artifact_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[KnowledgeArtifact]:
        ...

    @abstractmethod
    async def list_by_type(
        self,
        artifact_type: str,
        limit: int = 50,
    ) -> list[KnowledgeArtifact]:
        ...

    @abstractmethod
    async def search_by_tags(
        self,
        tags: list[str],
        artifact_type: str | None = None,
        limit: int = 50,
    ) -> list[KnowledgeArtifact]:
        ...

    @abstractmethod
    async def count(self) -> int:
        ...

    @abstractmethod
    async def count_by_type(self) -> dict[str, int]:
        ...


class KnowledgeExtractor(ABC):
    """Interface for extracting knowledge from completed executions."""

    @abstractmethod
    async def extract(
        self,
        execution_data: dict[str, Any],
        task_data: dict[str, Any] | None = None,
    ) -> ExtractedKnowledge:
        ...


class MemoryRanker(ABC):
    """Interface for ranking knowledge artifacts by relevance."""

    @abstractmethod
    async def rank(
        self,
        artifacts: list[KnowledgeArtifact],
        query: str = "",
        context: dict[str, Any] | None = None,
    ) -> list[RankedMemory]:
        ...


class KnowledgeConsolidator(ABC):
    """Interface for consolidating duplicate knowledge artifacts."""

    @abstractmethod
    async def consolidate(
        self,
        artifacts: list[KnowledgeArtifact],
    ) -> ConsolidationResult:
        ...


class LearningRetriever(ABC):
    """Interface for semantic retrieval of learning artifacts."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        user_id: str | None = None,
        artifact_type: str | None = None,
        limit: int = 10,
    ) -> RetrievalResult:
        ...


class OutcomeStore(ABC):
    """Interface for persisting execution outcomes."""

    @abstractmethod
    async def create(self, outcome: ExecutionOutcome) -> ExecutionOutcome:
        ...

    @abstractmethod
    async def get_by_execution(self, execution_id: str) -> ExecutionOutcome | None:
        ...

    @abstractmethod
    async def list_by_strategy(
        self, strategy: str, limit: int = 500
    ) -> list[ExecutionOutcome]:
        ...

    @abstractmethod
    async def list_by_agent(
        self, agent_id: str, limit: int = 500
    ) -> list[ExecutionOutcome]:
        ...

    @abstractmethod
    async def list_all(self, limit: int = 500) -> list[ExecutionOutcome]:
        ...

    @abstractmethod
    async def list_failures(self, limit: int = 500) -> list[ExecutionOutcome]:
        ...

    @abstractmethod
    async def count(self) -> int:
        ...
