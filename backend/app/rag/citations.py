"""RAG citations — generate source citations for retrieved chunks."""

from __future__ import annotations

from typing import Any

from app.rag.base import CitationProvider
from app.rag.schemas import Citation, RetrievedChunk, RetrievalMethod


class DefaultCitationProvider(CitationProvider):
    """Default citation provider — generates citations from chunk metadata."""

    @property
    def provider_id(self) -> str:
        return "default"

    async def generate_citations(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        retrieval_method: RetrievalMethod = RetrievalMethod.VECTOR,
        **kwargs: Any,
    ) -> list[Citation]:
        citations: list[Citation] = []
        for rc in chunks:
            meta = rc.chunk.metadata
            citation = Citation(
                source_id=meta.source_id or meta.document_id,
                document_id=meta.document_id,
                title=meta.title,
                chunk_id=rc.chunk.id,
                relevance_score=rc.rerank_score if rc.rerank_score is not None else rc.score,
                retrieval_method=retrieval_method,
                snippet=rc.chunk.content[:200],
                metadata={
                    "chunk_index": meta.chunk_index,
                    "token_count": meta.token_count,
                    "strategy": meta.strategy.value if meta.strategy else "unknown",
                    "tags": meta.tags,
                    "category": meta.category,
                    "language": meta.language,
                },
            )
            citations.append(citation)
        return citations


class EnhancedCitationProvider(CitationProvider):
    """Enhanced citation provider with deduplication and ranking."""

    @property
    def provider_id(self) -> str:
        return "enhanced"

    async def generate_citations(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        retrieval_method: RetrievalMethod = RetrievalMethod.VECTOR,
        **kwargs: Any,
    ) -> list[Citation]:
        citations: list[Citation] = []
        seen_docs: set[str] = set()
        for rc in chunks:
            meta = rc.chunk.metadata
            doc_id = meta.document_id
            citation = Citation(
                source_id=meta.source_id or doc_id,
                document_id=doc_id,
                title=meta.title,
                chunk_id=rc.chunk.id,
                relevance_score=rc.rerank_score if rc.rerank_score is not None else rc.score,
                retrieval_method=retrieval_method,
                snippet=rc.chunk.content[:300],
                metadata={
                    "chunk_index": meta.chunk_index,
                    "token_count": meta.token_count,
                    "is_first_citation_for_doc": doc_id not in seen_docs,
                },
            )
            citations.append(citation)
            seen_docs.add(doc_id)
        citations.sort(key=lambda c: c.relevance_score, reverse=True)
        return citations


def get_citation_provider(provider_type: str = "default") -> CitationProvider:
    if provider_type == "enhanced":
        return EnhancedCitationProvider()
    return DefaultCitationProvider()
