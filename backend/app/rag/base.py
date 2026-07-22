"""RAG base abstractions — ABCs for all pluggable components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional

from app.rag.schemas import (
    Chunk,
    ChunkMetadata,
    Citation,
    ContextPackage,
    FilterCondition,
    IndexDocument,
    IndexResult,
    QueryRewrite,
    RetrievedChunk,
    RetrievalMethod,
    RetrievalQuery,
    RetrievalResult,
)


class Retriever(ABC):
    """Abstract retriever — fetches candidate chunks from a data source."""

    @property
    @abstractmethod
    def retriever_id(self) -> str:
        ...

    @property
    @abstractmethod
    def retrieval_method(self) -> RetrievalMethod:
        ...

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.0,
        filters: Optional[list[FilterCondition]] = None,
        **kwargs: Any,
    ) -> list[RetrievedChunk]:
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        ...


class Reranker(ABC):
    """Abstract reranker — re-scores retrieved chunks for relevance."""

    @property
    @abstractmethod
    def reranker_id(self) -> str:
        ...

    @abstractmethod
    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = 10,
        **kwargs: Any,
    ) -> list[RetrievedChunk]:
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        ...


class Chunker(ABC):
    """Abstract chunker — splits documents into chunks."""

    @property
    @abstractmethod
    def chunker_id(self) -> str:
        ...

    @abstractmethod
    async def chunk(
        self,
        content: str,
        metadata: Optional[ChunkMetadata] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        **kwargs: Any,
    ) -> list[Chunk]:
        ...


class EmbeddingProvider(ABC):
    """Abstract embedding provider — generates vector embeddings."""

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


class QueryRewriter(ABC):
    """Abstract query rewriter — transforms queries for better retrieval."""

    @property
    @abstractmethod
    def rewriter_id(self) -> str:
        ...

    @abstractmethod
    async def rewrite(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> QueryRewrite:
        ...


class ContextBuilder(ABC):
    """Abstract context builder — assembles retrieval results into prompts."""

    @property
    @abstractmethod
    def builder_id(self) -> str:
        ...

    @abstractmethod
    async def build(
        self,
        query: str,
        retrieved_chunks: list[RetrievedChunk],
        user_context: Optional[dict[str, Any]] = None,
        conversation_history: Optional[list[dict[str, str]]] = None,
        goal_context: Optional[list[dict[str, Any]]] = None,
        task_context: Optional[list[dict[str, Any]]] = None,
        knowledge_context: Optional[list[dict[str, Any]]] = None,
        execution_context: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ContextPackage:
        ...


class CitationProvider(ABC):
    """Abstract citation provider — generates citations for retrieved chunks."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        ...

    @abstractmethod
    async def generate_citations(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        retrieval_method: RetrievalMethod = RetrievalMethod.VECTOR,
        **kwargs: Any,
    ) -> list[Citation]:
        ...


class VectorRepository(ABC):
    """Abstract vector repository — stores and retrieves vector embeddings."""

    @property
    @abstractmethod
    def repository_id(self) -> str:
        ...

    @abstractmethod
    async def add(
        self,
        collection: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> int:
        ...

    @abstractmethod
    async def search(
        self,
        collection: str,
        embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.0,
        filters: Optional[list[FilterCondition]] = None,
    ) -> list[RetrievedChunk]:
        ...

    @abstractmethod
    async def delete(self, collection: str, ids: list[str]) -> int:
        ...

    @abstractmethod
    async def count(self, collection: str) -> int:
        ...

    @abstractmethod
    async def get_all_ids(self, collection: str) -> list[str]:
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        ...
