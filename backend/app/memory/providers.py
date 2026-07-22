"""Abstract providers for the Semantic Memory (RAG) layer.

Strategy Pattern — concrete implementations can swap ChromaDB for
pgvector, Pinecone, Qdrant, etc. without changing consumers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# EmbeddingProvider
# ---------------------------------------------------------------------------

class EmbeddingProvider(ABC):
    """Generates embedding vectors from text."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Return a dense vector for *text*."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return dense vectors for a batch of texts."""
        ...


# ---------------------------------------------------------------------------
# VectorEntry
# ---------------------------------------------------------------------------

@dataclass
class VectorEntry:
    """A single entry to be stored or returned from a vector store."""

    id: str
    document: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    distance: float = 0.0


# ---------------------------------------------------------------------------
# VectorStoreProvider
# ---------------------------------------------------------------------------

class VectorStoreProvider(ABC):
    """Abstract vector database interface."""

    @abstractmethod
    async def get_or_create_collection(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> Any:
        """Return a collection handle, creating it if it doesn't exist."""
        ...

    @abstractmethod
    async def add(self, collection: Any, entries: list[VectorEntry]) -> None:
        """Insert or upsert entries into the collection."""
        ...

    @abstractmethod
    async def search(
        self,
        collection: Any,
        query_embedding: list[float],
        top_k: int = 5,
        threshold: float | None = None,
    ) -> list[VectorEntry]:
        """Return the top-k entries closest to *query_embedding*.

        If *threshold* is set, only entries with ``distance <= threshold``
        are returned.
        """
        ...

    @abstractmethod
    async def delete(self, collection: Any, ids: list[str]) -> None:
        """Remove entries by their IDs."""
        ...

    @abstractmethod
    async def count(self, collection: Any) -> int:
        """Return the number of entries in the collection."""
        ...

    @abstractmethod
    async def get_all_ids(self, collection: Any) -> list[str]:
        """Return all entry IDs in the collection."""
        ...
