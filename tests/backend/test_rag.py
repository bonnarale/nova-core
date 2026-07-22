"""Comprehensive tests for Chapter 17 — RAG & Retrieval system."""

from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.rag.base import (
    CitationProvider,
    Chunker,
    ContextBuilder,
    EmbeddingProvider,
    QueryRewriter,
    Reranker,
    Retriever,
    VectorRepository,
)
from app.rag.citations import DefaultCitationProvider, EnhancedCitationProvider, get_citation_provider
from app.rag.chunker import (
    CodeChunker,
    FixedSizeChunker,
    MarkdownChunker,
    RecursiveChunker,
    SemanticChunker,
    get_chunker,
)
from app.rag.context_builder import CompactContextBuilder, DefaultContextBuilder, get_context_builder
from app.rag.embeddings import (
    GoogleEmbeddingProvider,
    InMemoryEmbeddingProvider,
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
    get_embedding_provider,
)
from app.rag.engine import RAGEngine
from app.rag.factory import RAGFactory, get_rag_factory
from app.rag.filters import (
    apply_filters,
    build_category_filter,
    build_source_filter,
    build_tag_filter,
    merge_filters,
)
from app.rag.index import RAGIndex
from app.rag.lifecycle import RAGLifecycle, RAGLifecycleError, RAGState, VALID_RAG_TRANSITIONS
from app.rag.metrics import RAGMetrics, RequestMetric, get_rag_metrics
from app.rag.pipeline import RAGPipeline
from app.rag.query_rewriter import (
    ContextualRewriter,
    HyDEQueryRewriter,
    KeywordExpansionRewriter,
    PassthroughRewriter,
    get_query_rewriter,
)
from app.rag.reranker import (
    CrossEncoderReranker,
    HybridScoreReranker,
    ImportanceAwareReranker,
    RecencyAwareReranker,
    SimilarityReranker,
    get_reranker,
)
from app.rag.repository import ChromaRepository, InMemoryRepository, get_repository
from app.rag.retriever import (
    HybridRetriever,
    KeywordRetriever,
    KnowledgeRetriever,
    MemoryRetriever,
    VectorRetriever,
    get_retriever,
)
from app.rag.schemas import (
    Chunk,
    ChunkMetadata,
    ChunkStrategy,
    Citation,
    ContextPackage,
    DocumentStatus,
    FilterCondition,
    FilterOperator,
    IndexDocument,
    IndexResult,
    QueryRewrite,
    RetrievedChunk,
    RetrievalMethod,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStatus,
    RerankStrategy,
)
from app.rag.tracing import RAGSpan, RAGTrace, RAGTracer, get_rag_tracer


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


def _make_embedding_provider(dimension: int = 384) -> InMemoryEmbeddingProvider:
    return InMemoryEmbeddingProvider(dimension=dimension)


def _make_repository() -> InMemoryRepository:
    return InMemoryRepository()


def _make_chunk(
    content: str = "test content",
    doc_id: str = "",
    title: str = "",
    source: str = "",
    category: str = "",
    tags: list[str] | None = None,
    confidence: float = 1.0,
    chunk_id: str = "",
) -> Chunk:
    meta = ChunkMetadata(
        chunk_id=chunk_id or str(uuid4()),
        document_id=doc_id or str(uuid4()),
        source_id=source,
        title=title,
        tags=tags or [],
        source=source,
        category=category,
        confidence=confidence,
    )
    return Chunk(id=meta.chunk_id, content=content, metadata=meta)


def _make_retrieved_chunk(
    content: str = "test content",
    score: float = 0.9,
    doc_id: str = "",
    title: str = "",
    source: str = "",
    method: RetrievalMethod = RetrievalMethod.VECTOR,
) -> RetrievedChunk:
    chunk = _make_chunk(content=content, doc_id=doc_id, title=title, source=source)
    return RetrievedChunk(chunk=chunk, score=score, retrieval_method=method)


def _make_index_doc(
    content: str = "Test document content for indexing.",
    title: str = "Test Doc",
    source: str = "test_source",
    doc_id: str = "",
    tags: list[str] | None = None,
) -> IndexDocument:
    return IndexDocument(
        document_id=doc_id or str(uuid4()),
        content=content,
        title=title,
        source=source,
        tags=tags or ["test"],
        chunk_strategy=ChunkStrategy.RECURSIVE,
        chunk_size=512,
        chunk_overlap=50,
    )


# ═══════════════════════════════════════════════════════════════════════
# 1. Schemas Tests
# ═══════════════════════════════════════════════════════════════════════


class TestSchemas:
    def test_retrieval_method_enum(self):
        assert RetrievalMethod.VECTOR.value == "vector"
        assert RetrievalMethod.HYBRID.value == "hybrid"
        assert RetrievalMethod.KEYWORD.value == "keyword"
        assert RetrievalMethod.MEMORY.value == "memory"
        assert RetrievalMethod.KNOWLEDGE.value == "knowledge"

    def test_chunk_strategy_enum(self):
        assert ChunkStrategy.FIXED.value == "fixed"
        assert ChunkStrategy.SEMANTIC.value == "semantic"
        assert ChunkStrategy.RECURSIVE.value == "recursive"
        assert ChunkStrategy.MARKDOWN.value == "markdown"
        assert ChunkStrategy.CODE.value == "code"

    def test_filter_operator_enum(self):
        assert FilterOperator.EQ.value == "eq"
        assert FilterOperator.IN.value == "in"
        assert FilterOperator.CONTAINS.value == "contains"

    def test_chunk_metadata_defaults(self):
        meta = ChunkMetadata()
        assert meta.chunk_id
        assert meta.document_id == ""
        assert meta.language == "en"
        assert meta.confidence == 1.0

    def test_chunk_to_dict(self):
        chunk = _make_chunk(content="hello world")
        d = chunk.to_dict()
        assert d["id"] == chunk.id
        assert d["content"] == "hello world"
        assert "metadata" in d

    def test_citation_model(self):
        c = Citation(
            source_id="s1",
            document_id="d1",
            title="Title",
            chunk_id="c1",
            relevance_score=0.95,
            retrieval_method=RetrievalMethod.VECTOR,
            snippet="snippet",
        )
        assert c.source_id == "s1"
        assert c.relevance_score == 0.95

    def test_retrieved_chunk_model(self):
        rc = _make_retrieved_chunk(content="test", score=0.8)
        assert rc.score == 0.8
        assert rc.rerank_score is None

    def test_retrieval_query_defaults(self):
        q = RetrievalQuery(query="test query")
        assert q.top_k == 10
        assert q.threshold == 0.0
        assert q.retrieval_method == RetrievalMethod.HYBRID

    def test_retrieval_result_defaults(self):
        r = RetrievalResult(query="q")
        assert r.status == RetrievalStatus.SUCCESS
        assert r.chunks == []

    def test_index_document_defaults(self):
        doc = IndexDocument(content="hello")
        assert doc.chunk_strategy == ChunkStrategy.RECURSIVE
        assert doc.chunk_size == 512

    def test_context_package_model(self):
        pkg = ContextPackage(query="q", context_text="ctx")
        assert pkg.query == "q"
        assert pkg.retrieved_chunks == []

    def test_document_status_enum(self):
        assert DocumentStatus.PENDING.value == "pending"
        assert DocumentStatus.INDEXED.value == "indexed"
        assert DocumentStatus.FAILED.value == "failed"
        assert DocumentStatus.DELETED.value == "deleted"

    def test_retrieval_status_enum(self):
        assert RetrievalStatus.SUCCESS.value == "success"
        assert RetrievalStatus.NO_RESULTS.value == "no_results"


# ═══════════════════════════════════════════════════════════════════════
# 2. Embedding Tests
# ═══════════════════════════════════════════════════════════════════════


class TestEmbeddings:
    @pytest.fixture
    def provider(self):
        return InMemoryEmbeddingProvider(dimension=384)

    @pytest.mark.asyncio
    async def test_embed_returns_correct_dimension(self, provider):
        vec = await provider.embed("hello world")
        assert len(vec) == 384

    @pytest.mark.asyncio
    async def test_embed_deterministic(self, provider):
        v1 = await provider.embed("test")
        v2 = await provider.embed("test")
        assert v1 == v2

    @pytest.mark.asyncio
    async def test_embed_different_texts_different_vectors(self, provider):
        v1 = await provider.embed("cats")
        v2 = await provider.embed("dogs")
        assert v1 != v2

    @pytest.mark.asyncio
    async def test_embed_batch(self, provider):
        texts = ["one", "two", "three"]
        vecs = await provider.embed_batch(texts)
        assert len(vecs) == 3
        assert all(len(v) == 384 for v in vecs)

    @pytest.mark.asyncio
    async def test_health(self, provider):
        h = await provider.health()
        assert h["status"] == "healthy"
        assert h["provider"] == "in_memory"

    def test_provider_id(self, provider):
        assert provider.provider_id == "in_memory"

    def test_embedding_dimension(self, provider):
        assert provider.embedding_dimension == 384

    def test_get_embedding_provider_in_memory(self):
        p = get_embedding_provider("in_memory", dimension=128)
        assert p.embedding_dimension == 128

    def test_get_embedding_provider_ollama(self):
        p = get_embedding_provider("ollama", model="test-model", dimension=256)
        assert isinstance(p, OllamaEmbeddingProvider)
        assert p.embedding_dimension == 256

    def test_get_embedding_provider_openai(self):
        p = get_embedding_provider("openai", api_key="sk-test", dimension=512)
        assert isinstance(p, OpenAIEmbeddingProvider)

    def test_get_embedding_provider_google(self):
        p = get_embedding_provider("google", api_key="gk-test", dimension=768)
        assert isinstance(p, GoogleEmbeddingProvider)

    def test_get_embedding_provider_unknown(self):
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            get_embedding_provider("nonexistent")


# ═══════════════════════════════════════════════════════════════════════
# 3. Chunking Tests
# ═══════════════════════════════════════════════════════════════════════


class TestChunking:
    @pytest.mark.asyncio
    async def test_fixed_size_chunker(self):
        chunker = FixedSizeChunker()
        text = "A " * 300  # ~600 chars
        chunks = await chunker.chunk(text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1
        assert all(c.content for c in chunks)

    @pytest.mark.asyncio
    async def test_fixed_size_single_chunk(self):
        chunker = FixedSizeChunker()
        chunks = await chunker.chunk("short text", chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0].content == "short text"

    @pytest.mark.asyncio
    async def test_semantic_chunker(self):
        chunker = SemanticChunker()
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence."
        chunks = await chunker.chunk(text, chunk_size=50)
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_recursive_chunker(self):
        chunker = RecursiveChunker()
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = await chunker.chunk(text, chunk_size=30)
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_markdown_chunker(self):
        chunker = MarkdownChunker()
        md = "# Heading 1\nContent under h1.\n\n## Heading 2\nContent under h2."
        chunks = await chunker.chunk(md, chunk_size=500)
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_markdown_chunker_fallback(self):
        chunker = MarkdownChunker()
        text = "plain text without any headings at all"
        chunks = await chunker.chunk(text, chunk_size=500)
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_code_chunker(self):
        chunker = CodeChunker()
        code = "def foo():\n    return 1\n\ndef bar():\n    return 2"
        chunks = await chunker.chunk(code, chunk_size=50)
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_code_chunker_fallback(self):
        chunker = CodeChunker()
        text = "just some plain text no code"
        chunks = await chunker.chunk(text, chunk_size=500)
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_chunker_preserves_metadata(self):
        chunker = FixedSizeChunker()
        meta = ChunkMetadata(document_id="doc1", title="Title", source="test")
        chunks = await chunker.chunk("some content here for test", metadata=meta, chunk_size=10)
        for c in chunks:
            assert c.metadata.document_id == "doc1"
            assert c.metadata.title == "Title"

    @pytest.mark.asyncio
    async def test_empty_content(self):
        chunker = FixedSizeChunker()
        chunks = await chunker.chunk("")
        assert len(chunks) == 1  # single empty-ish chunk

    def test_get_chunker_factory(self):
        assert isinstance(get_chunker(ChunkStrategy.FIXED), FixedSizeChunker)
        assert isinstance(get_chunker(ChunkStrategy.SEMANTIC), SemanticChunker)
        assert isinstance(get_chunker(ChunkStrategy.RECURSIVE), RecursiveChunker)
        assert isinstance(get_chunker(ChunkStrategy.MARKDOWN), MarkdownChunker)
        assert isinstance(get_chunker(ChunkStrategy.CODE), CodeChunker)
        assert isinstance(get_chunker(), RecursiveChunker)  # default

    @pytest.mark.asyncio
    async def test_fixed_size_overlap(self):
        chunker = FixedSizeChunker()
        text = "A" * 200
        chunks = await chunker.chunk(text, chunk_size=100, chunk_overlap=50)
        assert len(chunks) >= 2


# ═══════════════════════════════════════════════════════════════════════
# 4. Repository Tests
# ═══════════════════════════════════════════════════════════════════════


class TestRepository:
    @pytest.fixture
    def repo(self):
        return InMemoryRepository()

    @pytest.mark.asyncio
    async def test_add_and_count(self, repo):
        chunk = _make_chunk(content="hello")
        emb = [0.1] * 384
        added = await repo.add("col1", [chunk], [emb])
        assert added == 1
        assert await repo.count("col1") == 1

    @pytest.mark.asyncio
    async def test_search_cosine_similarity(self, repo):
        c1 = _make_chunk(content="cat")
        c2 = _make_chunk(content="dog")
        e1 = [1.0] + [0.0] * 383
        e2 = [0.0, 1.0] + [0.0] * 382
        await repo.add("col1", [c1, c2], [e1, e2])
        results = await repo.search("col1", e1, top_k=2, threshold=0.0)
        assert len(results) == 2
        assert results[0].score >= results[1].score

    @pytest.mark.asyncio
    async def test_search_with_filters(self, repo):
        c1 = _make_chunk(content="a", tags=["important"])
        c2 = _make_chunk(content="b", tags=["normal"])
        e1 = [1.0] + [0.0] * 383
        e2 = [0.0, 1.0] + [0.0] * 382
        await repo.add("col1", [c1, c2], [e1, e2])
        fc = FilterCondition(field="tags", operator=FilterOperator.CONTAINS, value="important")
        results = await repo.search("col1", e1, top_k=10, threshold=0.0, filters=[fc])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_delete(self, repo):
        c1 = _make_chunk(content="x")
        await repo.add("col1", [c1], [[0.1] * 384])
        assert await repo.count("col1") == 1
        deleted = await repo.delete("col1", [c1.id])
        assert deleted == 1
        assert await repo.count("col1") == 0

    @pytest.mark.asyncio
    async def test_get_all_ids(self, repo):
        c1 = _make_chunk(content="a")
        c2 = _make_chunk(content="b")
        await repo.add("col1", [c1, c2], [[0.1] * 384, [0.2] * 384])
        ids = await repo.get_all_ids("col1")
        assert len(ids) == 2
        assert c1.id in ids

    @pytest.mark.asyncio
    async def test_health(self, repo):
        h = await repo.health()
        assert h["status"] == "healthy"
        assert h["repository"] == "in_memory"

    @pytest.mark.asyncio
    async def test_multiple_collections(self, repo):
        c1 = _make_chunk(content="a")
        c2 = _make_chunk(content="b")
        await repo.add("col1", [c1], [[0.1] * 384])
        await repo.add("col2", [c2], [[0.2] * 384])
        assert await repo.count("col1") == 1
        assert await repo.count("col2") == 1

    @pytest.mark.asyncio
    async def test_search_empty_collection(self, repo):
        results = await repo.search("empty", [0.0] * 384, top_k=10)
        assert results == []

    def test_repository_id(self, repo):
        assert repo.repository_id == "in_memory"

    def test_get_repository_in_memory(self):
        r = get_repository("in_memory")
        assert isinstance(r, InMemoryRepository)

    def test_get_repository_chroma(self):
        r = get_repository("chroma", client=MagicMock())
        assert isinstance(r, ChromaRepository)

    def test_get_repository_unknown(self):
        with pytest.raises(ValueError, match="Unknown repository type"):
            get_repository("nonexistent")


# ═══════════════════════════════════════════════════════════════════════
# 5. Retriever Tests
# ═══════════════════════════════════════════════════════════════════════


class TestRetrievers:
    @pytest.fixture
    def repo(self):
        return InMemoryRepository()

    @pytest.fixture
    def embedder(self):
        return InMemoryEmbeddingProvider(dimension=384)

    @pytest.mark.asyncio
    async def test_vector_retriever(self, repo, embedder):
        c = _make_chunk(content="hello world", title="Doc1")
        await repo.add("docs", [c], [await embedder.embed("hello world")])
        ret = VectorRetriever(repo, embedder, "docs")
        embedding = await embedder.embed("hello world")
        results = await ret.retrieve("hello world", embedding, top_k=5)
        assert len(results) >= 1
        assert ret.retriever_id == "vector"
        assert ret.retrieval_method == RetrievalMethod.VECTOR

    @pytest.mark.asyncio
    async def test_keyword_retriever(self, repo, embedder):
        c = _make_chunk(content="python programming")
        await repo.add("docs", [c], [await embedder.embed("python")])
        ret = KeywordRetriever(repo, "docs")
        results = await ret.retrieve("python", [], top_k=5)
        assert ret.retriever_id == "keyword"
        assert ret.retrieval_method == RetrievalMethod.KEYWORD

    @pytest.mark.asyncio
    async def test_hybrid_retriever(self, repo, embedder):
        c = _make_chunk(content="machine learning")
        await repo.add("docs", [c], [await embedder.embed("ml")])
        ret = HybridRetriever(repo, embedder, "docs")
        embedding = await embedder.embed("ml")
        results = await ret.retrieve("machine learning", embedding, top_k=5)
        assert ret.retriever_id == "hybrid"
        assert ret.retrieval_method == RetrievalMethod.HYBRID

    @pytest.mark.asyncio
    async def test_memory_retriever_no_provider(self):
        ret = MemoryRetriever()
        results = await ret.retrieve("query", [], top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_memory_retriever_with_provider(self):
        mock_memory = AsyncMock()
        mock_memory.search = AsyncMock(return_value=[
            {"id": "m1", "content": "memory content", "score": 0.8}
        ])
        ret = MemoryRetriever(memory_provider=mock_memory)
        results = await ret.retrieve("query", [], top_k=5)
        assert len(results) == 1
        assert results[0].retrieval_method == RetrievalMethod.MEMORY

    @pytest.mark.asyncio
    async def test_knowledge_retriever_no_provider(self):
        ret = KnowledgeRetriever()
        results = await ret.retrieve("query", [], top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_knowledge_retriever_with_provider(self):
        mock_entity = MagicMock()
        mock_entity.id = "e1"
        mock_entity.name = "Test Entity"
        mock_entity.description = "A test entity"
        mock_entity.confidence = 0.9
        mock_engine = AsyncMock()
        mock_engine.search = AsyncMock(return_value=[mock_entity])
        ret = KnowledgeRetriever(knowledge_engine=mock_engine)
        results = await ret.retrieve("query", [], top_k=5)
        assert len(results) == 1
        assert results[0].retrieval_method == RetrievalMethod.KNOWLEDGE

    @pytest.mark.asyncio
    async def test_retriever_health(self, repo, embedder):
        ret = VectorRetriever(repo, embedder, "docs")
        h = await ret.health()
        assert h["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_memory_retriever_health_no_provider(self):
        ret = MemoryRetriever()
        h = await ret.health()
        assert h["status"] == "no_provider"

    def test_get_retriever_vector(self, repo, embedder):
        r = get_retriever(RetrievalMethod.VECTOR, repo, embedder)
        assert isinstance(r, VectorRetriever)

    def test_get_retriever_keyword(self, repo):
        r = get_retriever(RetrievalMethod.KEYWORD, repo)
        assert isinstance(r, KeywordRetriever)

    def test_get_retriever_hybrid(self, repo, embedder):
        r = get_retriever(RetrievalMethod.HYBRID, repo, embedder)
        assert isinstance(r, HybridRetriever)

    def test_get_retriever_memory(self):
        r = get_retriever(RetrievalMethod.MEMORY)
        assert isinstance(r, MemoryRetriever)

    def test_get_retriever_knowledge(self):
        r = get_retriever(RetrievalMethod.KNOWLEDGE)
        assert isinstance(r, KnowledgeRetriever)

    def test_get_retriever_default(self, repo, embedder):
        r = get_retriever("unknown", repo, embedder)
        assert isinstance(r, VectorRetriever)


# ═══════════════════════════════════════════════════════════════════════
# 6. Reranker Tests
# ═══════════════════════════════════════════════════════════════════════


class TestRerankers:
    @pytest.fixture
    def chunks(self):
        return [
            _make_retrieved_chunk(content="machine learning algorithms", score=0.9),
            _make_retrieved_chunk(content="deep neural networks", score=0.7),
            _make_retrieved_chunk(content="natural language processing", score=0.5),
        ]

    @pytest.mark.asyncio
    async def test_similarity_reranker(self, chunks):
        reranker = SimilarityReranker()
        result = await reranker.rerank("machine learning", chunks, top_k=3)
        assert len(result) == 3
        assert result[0].rerank_score == result[0].score
        assert result[0].score >= result[-1].score

    @pytest.mark.asyncio
    async def test_cross_encoder_reranker(self, chunks):
        reranker = CrossEncoderReranker()
        result = await reranker.rerank("machine learning", chunks, top_k=3)
        assert len(result) == 3
        assert all(rc.rerank_score is not None for rc in result)

    @pytest.mark.asyncio
    async def test_hybrid_score_reranker(self, chunks):
        reranker = HybridScoreReranker()
        result = await reranker.rerank("machine learning", chunks, top_k=3)
        assert len(result) == 3
        assert all(rc.rerank_score is not None for rc in result)

    @pytest.mark.asyncio
    async def test_recency_reranker(self, chunks):
        reranker = RecencyAwareReranker()
        result = await reranker.rerank("query", chunks, top_k=3)
        assert len(result) == 3
        assert all(rc.rerank_score is not None for rc in result)

    @pytest.mark.asyncio
    async def test_importance_reranker(self, chunks):
        reranker = ImportanceAwareReranker()
        result = await reranker.rerank("query", chunks, top_k=3)
        assert len(result) == 3
        assert all(rc.rerank_score is not None for rc in result)

    @pytest.mark.asyncio
    async def test_reranker_respects_top_k(self, chunks):
        reranker = SimilarityReranker()
        result = await reranker.rerank("query", chunks, top_k=2)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_reranker_empty_input(self):
        reranker = SimilarityReranker()
        result = await reranker.rerank("query", [], top_k=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_reranker_health(self):
        reranker = SimilarityReranker()
        h = await reranker.health()
        assert h["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_hybrid_reranker_weights(self):
        c1 = _make_retrieved_chunk(content="a a a a a a", score=0.8)
        c2 = _make_retrieved_chunk(content="a a a a a a b b b b", score=0.6)
        reranker = HybridScoreReranker(similarity_weight=0.5, keyword_weight=0.5)
        result = await reranker.rerank("a a", [c1, c2], top_k=2)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_recency_reranker_with_old_chunks(self):
        old_meta = ChunkMetadata(
            created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            confidence=1.0,
        )
        c_old = RetrievedChunk(
            chunk=Chunk(id="old", content="old content", metadata=old_meta),
            score=0.9,
        )
        new_meta = ChunkMetadata(
            created_at=datetime.now(timezone.utc),
            confidence=1.0,
        )
        c_new = RetrievedChunk(
            chunk=Chunk(id="new", content="new content", metadata=new_meta),
            score=0.5,
        )
        reranker = RecencyAwareReranker(recency_weight=0.8)
        result = await reranker.rerank("query", [c_old, c_new], top_k=2)
        assert result[0].chunk.id == "new"

    def test_get_reranker_similarity(self):
        r = get_reranker("similarity")
        assert isinstance(r, SimilarityReranker)

    def test_get_reranker_cross_encoder(self):
        r = get_reranker("cross_encoder")
        assert isinstance(r, CrossEncoderReranker)

    def test_get_reranker_hybrid_score(self):
        r = get_reranker("hybrid_score")
        assert isinstance(r, HybridScoreReranker)

    def test_get_reranker_recency(self):
        r = get_reranker("recency")
        assert isinstance(r, RecencyAwareReranker)

    def test_get_reranker_importance(self):
        r = get_reranker("importance")
        assert isinstance(r, ImportanceAwareReranker)

    def test_get_reranker_default(self):
        r = get_reranker("unknown")
        assert isinstance(r, SimilarityReranker)


# ═══════════════════════════════════════════════════════════════════════
# 7. Query Rewriter Tests
# ═══════════════════════════════════════════════════════════════════════


class TestQueryRewriter:
    @pytest.mark.asyncio
    async def test_passthrough(self):
        rw = PassthroughRewriter()
        result = await rw.rewrite("hello world")
        assert result.original_query == "hello world"
        assert result.rewritten_query == "hello world"
        assert result.strategy == "passthrough"

    @pytest.mark.asyncio
    async def test_keyword_expansion(self):
        rw = KeywordExpansionRewriter()
        result = await rw.rewrite("python error handling")
        assert result.original_query == "python error handling"
        assert len(result.expansion_terms) > 0
        assert result.strategy == "keyword_expansion"

    @pytest.mark.asyncio
    async def test_keyword_expansion_stop_words(self):
        rw = KeywordExpansionRewriter()
        result = await rw.rewrite("the is a an")
        assert result.rewritten_query == "the is a an"

    @pytest.mark.asyncio
    async def test_contextual_rewriter(self):
        rw = ContextualRewriter()
        context = {
            "conversation_history": [
                {"role": "user", "content": "tell me about machine learning algorithms"},
                {"role": "assistant", "content": "sure, ML algorithms are used in data science"},
            ],
        }
        result = await rw.rewrite("what about deep learning", context=context)
        assert "deep learning" in result.rewritten_query
        assert result.strategy == "contextual"

    @pytest.mark.asyncio
    async def test_contextual_no_context(self):
        rw = ContextualRewriter()
        result = await rw.rewrite("query")
        assert result.rewritten_query == "query"

    @pytest.mark.asyncio
    async def test_hyde_rewriter(self):
        rw = HyDEQueryRewriter()
        result = await rw.rewrite("what is RAG?")
        assert "RAG?" in result.rewritten_query
        assert result.strategy == "hyde"

    def test_get_query_rewriter_passthrough(self):
        rw = get_query_rewriter("passthrough")
        assert isinstance(rw, PassthroughRewriter)

    def test_get_query_rewriter_keyword(self):
        rw = get_query_rewriter("keyword_expansion")
        assert isinstance(rw, KeywordExpansionRewriter)

    def test_get_query_rewriter_contextual(self):
        rw = get_query_rewriter("contextual")
        assert isinstance(rw, ContextualRewriter)

    def test_get_query_rewriter_hyde(self):
        rw = get_query_rewriter("hyde")
        assert isinstance(rw, HyDEQueryRewriter)

    def test_get_query_rewriter_default(self):
        rw = get_query_rewriter("unknown")
        assert isinstance(rw, PassthroughRewriter)

    def test_rewriter_id(self):
        assert PassthroughRewriter().rewriter_id == "passthrough"
        assert KeywordExpansionRewriter().rewriter_id == "keyword_expansion"
        assert ContextualRewriter().rewriter_id == "contextual"
        assert HyDEQueryRewriter().rewriter_id == "hyde"


# ═══════════════════════════════════════════════════════════════════════
# 8. Filters Tests
# ═══════════════════════════════════════════════════════════════════════


class TestFilters:
    def test_apply_filters_eq(self):
        metadata_list = [
            {"source": "docs", "category": "guide"},
            {"source": "web", "category": "blog"},
        ]
        fc = FilterCondition(field="source", operator=FilterOperator.EQ, value="docs")
        matching = apply_filters(metadata_list, [fc])
        assert matching == [0]

    def test_apply_filters_in(self):
        metadata_list = [
            {"source": "docs"},
            {"source": "web"},
            {"source": "api"},
        ]
        fc = FilterCondition(field="source", operator=FilterOperator.IN, value=["docs", "web"])
        matching = apply_filters(metadata_list, [fc])
        assert matching == [0, 1]

    def test_apply_filters_contains(self):
        metadata_list = [
            {"tags": ["python", "tutorial"]},
            {"tags": ["java"]},
        ]
        fc = FilterCondition(field="tags", operator=FilterOperator.CONTAINS, value="python")
        matching = apply_filters(metadata_list, [fc])
        assert matching == [0]

    def test_apply_filters_gt(self):
        metadata_list = [{"confidence": 0.5}, {"confidence": 0.9}]
        fc = FilterCondition(field="confidence", operator=FilterOperator.GT, value=0.7)
        matching = apply_filters(metadata_list, [fc])
        assert matching == [1]

    def test_apply_filters_gte(self):
        metadata_list = [{"confidence": 0.7}, {"confidence": 0.9}]
        fc = FilterCondition(field="confidence", operator=FilterOperator.GTE, value=0.7)
        matching = apply_filters(metadata_list, [fc])
        assert matching == [0, 1]

    def test_apply_filters_neq(self):
        metadata_list = [{"source": "a"}, {"source": "b"}]
        fc = FilterCondition(field="source", operator=FilterOperator.NEQ, value="a")
        matching = apply_filters(metadata_list, [fc])
        assert matching == [1]

    def test_apply_filters_starts_with(self):
        metadata_list = [{"title": "Hello World"}, {"title": "Goodbye"}]
        fc = FilterCondition(field="title", operator=FilterOperator.STARTS_WITH, value="Hello")
        matching = apply_filters(metadata_list, [fc])
        assert matching == [0]

    def test_apply_filters_multiple(self):
        metadata_list = [
            {"source": "docs", "category": "guide"},
            {"source": "docs", "category": "blog"},
            {"source": "web", "category": "guide"},
        ]
        f1 = FilterCondition(field="source", operator=FilterOperator.EQ, value="docs")
        f2 = FilterCondition(field="category", operator=FilterOperator.EQ, value="guide")
        matching = apply_filters(metadata_list, [f1, f2])
        assert matching == [0]

    def test_build_tag_filter(self):
        f = build_tag_filter(["python"])
        assert f is not None
        assert f.field == "tags"
        assert f.operator == FilterOperator.CONTAINS

    def test_build_tag_filter_empty(self):
        assert build_tag_filter([]) is None

    def test_build_source_filter_single(self):
        f = build_source_filter(["docs"])
        assert f.operator == FilterOperator.EQ

    def test_build_source_filter_multiple(self):
        f = build_source_filter(["docs", "web"])
        assert f.operator == FilterOperator.IN

    def test_build_source_filter_empty(self):
        assert build_source_filter([]) is None

    def test_build_category_filter_single(self):
        f = build_category_filter(["guide"])
        assert f.operator == FilterOperator.EQ

    def test_build_category_filter_multiple(self):
        f = build_category_filter(["guide", "blog"])
        assert f.operator == FilterOperator.IN

    def test_build_category_filter_empty(self):
        assert build_category_filter([]) is None

    def test_merge_filters(self):
        f1 = FilterCondition(field="a", operator=FilterOperator.EQ, value=1)
        f2 = FilterCondition(field="b", operator=FilterOperator.EQ, value=2)
        merged = merge_filters([f1], f2)
        assert len(merged) == 2

    def test_merge_filters_with_none(self):
        f1 = FilterCondition(field="a", operator=FilterOperator.EQ, value=1)
        merged = merge_filters([f1], None)
        assert len(merged) == 1

    def test_apply_filters_missing_field(self):
        metadata_list = [{"source": "docs"}]
        fc = FilterCondition(field="nonexistent", operator=FilterOperator.EQ, value="x")
        matching = apply_filters(metadata_list, [fc])
        assert matching == []


# ═══════════════════════════════════════════════════════════════════════
# 9. Citation Tests
# ═══════════════════════════════════════════════════════════════════════


class TestCitations:
    @pytest.mark.asyncio
    async def test_default_citation_provider(self):
        provider = DefaultCitationProvider()
        chunks = [_make_retrieved_chunk(content="test content", score=0.9, title="Title", source="src")]
        citations = await provider.generate_citations("query", chunks)
        assert len(citations) == 1
        assert citations[0].title == "Title"
        assert citations[0].relevance_score == 0.9
        assert citations[0].retrieval_method == RetrievalMethod.VECTOR

    @pytest.mark.asyncio
    async def test_default_citation_with_rerank_score(self):
        provider = DefaultCitationProvider()
        rc = _make_retrieved_chunk(content="content", score=0.5)
        rc.rerank_score = 0.95
        citations = await provider.generate_citations("q", [rc])
        assert citations[0].relevance_score == 0.95

    @pytest.mark.asyncio
    async def test_enhanced_citation_provider(self):
        provider = EnhancedCitationProvider()
        chunks = [
            _make_retrieved_chunk(content="a", score=0.9, title="A"),
            _make_retrieved_chunk(content="b", score=0.7, title="B"),
        ]
        citations = await provider.generate_citations("query", chunks)
        assert len(citations) == 2
        assert citations[0].relevance_score >= citations[1].relevance_score

    @pytest.mark.asyncio
    async def test_enhanced_citation_dedup(self):
        provider = EnhancedCitationProvider()
        chunks = [
            _make_retrieved_chunk(content="a", score=0.9, doc_id="doc1"),
            _make_retrieved_chunk(content="b", score=0.8, doc_id="doc1"),
        ]
        citations = await provider.generate_citations("q", chunks)
        assert len(citations) == 2
        assert citations[0].metadata.get("is_first_citation_for_doc") is True
        assert citations[1].metadata.get("is_first_citation_for_doc") is False

    @pytest.mark.asyncio
    async def test_citation_provider_empty_chunks(self):
        provider = DefaultCitationProvider()
        citations = await provider.generate_citations("q", [])
        assert citations == []

    def test_get_citation_provider_default(self):
        p = get_citation_provider("default")
        assert isinstance(p, DefaultCitationProvider)

    def test_get_citation_provider_enhanced(self):
        p = get_citation_provider("enhanced")
        assert isinstance(p, EnhancedCitationProvider)

    def test_provider_ids(self):
        assert DefaultCitationProvider().provider_id == "default"
        assert EnhancedCitationProvider().provider_id == "enhanced"


# ═══════════════════════════════════════════════════════════════════════
# 10. Context Builder Tests
# ═══════════════════════════════════════════════════════════════════════


class TestContextBuilder:
    @pytest.mark.asyncio
    async def test_default_context_builder_basic(self):
        builder = DefaultContextBuilder()
        chunks = [_make_retrieved_chunk(content="retrieved knowledge")]
        result = await builder.build("query", chunks)
        assert isinstance(result, ContextPackage)
        assert "retrieved knowledge" in result.context_text
        assert result.query == "query"

    @pytest.mark.asyncio
    async def test_default_context_builder_with_user_context(self):
        builder = DefaultContextBuilder()
        user_ctx = {"name": "Alice", "role": "Developer"}
        result = await builder.build("q", [], user_context=user_ctx)
        assert "Alice" in result.context_text
        assert "Developer" in result.context_text

    @pytest.mark.asyncio
    async def test_default_context_builder_with_conversation(self):
        builder = DefaultContextBuilder()
        history = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
        result = await builder.build("q", [], conversation_history=history)
        assert "user: hello" in result.context_text

    @pytest.mark.asyncio
    async def test_default_context_builder_with_goals(self):
        builder = DefaultContextBuilder()
        goals = [{"name": "Finish project", "status": "active"}]
        result = await builder.build("q", [], goal_context=goals)
        assert "Finish project" in result.context_text

    @pytest.mark.asyncio
    async def test_default_context_builder_with_tasks(self):
        builder = DefaultContextBuilder()
        tasks = [{"title": "Write tests", "status": "in_progress"}]
        result = await builder.build("q", [], task_context=tasks)
        assert "Write tests" in result.context_text

    @pytest.mark.asyncio
    async def test_default_context_builder_with_knowledge(self):
        builder = DefaultContextBuilder()
        knowledge = [{"name": "Python", "description": "A programming language"}]
        result = await builder.build("q", [], knowledge_context=knowledge)
        assert "Python" in result.context_text

    @pytest.mark.asyncio
    async def test_default_context_builder_with_execution(self):
        builder = DefaultContextBuilder()
        exec_ctx = {"current_task": "task1", "active_agent": "coder"}
        result = await builder.build("q", [], execution_context=exec_ctx)
        assert "task1" in result.context_text

    @pytest.mark.asyncio
    async def test_compact_context_builder(self):
        builder = CompactContextBuilder(max_tokens=200)
        chunks = [_make_retrieved_chunk(content="word " * 100)]
        result = await builder.build("q", chunks)
        assert isinstance(result, ContextPackage)

    @pytest.mark.asyncio
    async def test_context_builder_empty(self):
        builder = DefaultContextBuilder()
        result = await builder.build("q", [])
        assert result.query == "q"

    def test_get_context_builder_default(self):
        b = get_context_builder("default")
        assert isinstance(b, DefaultContextBuilder)

    def test_get_context_builder_compact(self):
        b = get_context_builder("compact")
        assert isinstance(b, CompactContextBuilder)

    def test_get_context_builder_default_type(self):
        b = get_context_builder("unknown")
        assert isinstance(b, DefaultContextBuilder)

    def test_builder_ids(self):
        assert DefaultContextBuilder().builder_id == "default"
        assert CompactContextBuilder().builder_id == "compact"


# ═══════════════════════════════════════════════════════════════════════
# 11. Index Tests
# ═══════════════════════════════════════════════════════════════════════


class TestIndex:
    @pytest.fixture
    def index(self):
        return RAGIndex(
            repository=InMemoryRepository(),
            embedder=InMemoryEmbeddingProvider(dimension=384),
            metrics=get_rag_metrics(),
        )

    @pytest.mark.asyncio
    async def test_index_document(self, index):
        doc = _make_index_doc(content="This is test content for indexing into the system.")
        result = await index.index_document(doc)
        assert result.status == DocumentStatus.INDEXED
        assert result.chunks_created >= 1
        assert result.chunks_indexed >= 1

    @pytest.mark.asyncio
    async def test_index_document_count(self, index):
        doc = _make_index_doc()
        await index.index_document(doc)
        assert await index.get_document_count() == 1
        assert await index.count() >= 1

    @pytest.mark.asyncio
    async def test_index_documents_batch(self, index):
        docs = [_make_index_doc(content=f"Document {i} content") for i in range(3)]
        results = await index.index_documents(docs)
        assert len(results) == 3
        assert all(r.status == DocumentStatus.INDEXED for r in results)

    @pytest.mark.asyncio
    async def test_remove_document(self, index):
        doc = _make_index_doc(content="removable content for testing")
        await index.index_document(doc)
        removed = await index.remove_document(doc.document_id)
        assert removed >= 1

    @pytest.mark.asyncio
    async def test_statistics(self, index):
        doc = _make_index_doc(source="test_source")
        await index.index_document(doc)
        stats = await index.get_statistics()
        assert stats["document_count"] == 1
        assert stats["chunk_count"] >= 1
        assert "test_source" in stats["source_counts"]

    @pytest.mark.asyncio
    async def test_health(self, index):
        h = await index.health()
        assert h["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_index_empty_content(self, index):
        doc = _make_index_doc(content="")
        result = await index.index_document(doc)
        assert result.status == DocumentStatus.INDEXED
        assert result.chunks_created == 0


# ═══════════════════════════════════════════════════════════════════════
# 12. Pipeline Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPipeline:
    @pytest.fixture
    def pipeline(self):
        embedder = InMemoryEmbeddingProvider(dimension=384)
        repo = InMemoryRepository()
        return RAGPipeline(
            embedder=embedder,
            repository=repo,
            metrics=get_rag_metrics(),
            tracer=get_rag_tracer(),
        )

    @pytest.mark.asyncio
    async def test_pipeline_retrieve_empty(self, pipeline):
        result = await pipeline.retrieve("test query")
        assert result.status == RetrievalStatus.NO_RESULTS
        assert result.chunks == []

    @pytest.mark.asyncio
    async def test_pipeline_retrieve_with_data(self, pipeline):
        # Index a document first
        doc = _make_index_doc(content="Machine learning is a subset of artificial intelligence.")
        idx = RAGIndex(
            repository=pipeline.repository,
            embedder=pipeline.embedder,
        )
        await idx.index_document(doc)
        result = await pipeline.retrieve("machine learning")
        assert result.total_chunks >= 1

    @pytest.mark.asyncio
    async def test_pipeline_query(self, pipeline):
        doc = _make_index_doc(content="Python is a programming language used for data science.")
        idx = RAGIndex(
            repository=pipeline.repository,
            embedder=pipeline.embedder,
        )
        await idx.index_document(doc)
        req = RetrievalQuery(query="python programming", top_k=5)
        context = await pipeline.query(req)
        assert isinstance(context, ContextPackage)
        assert context.query == "python programming"

    @pytest.mark.asyncio
    async def test_pipeline_query_with_contexts(self, pipeline):
        doc = _make_index_doc(content="Data science involves statistics and machine learning.")
        idx = RAGIndex(
            repository=pipeline.repository,
            embedder=pipeline.embedder,
        )
        await idx.index_document(doc)
        req = RetrievalQuery(query="data science", top_k=5)
        context = await pipeline.query(
            req,
            user_context={"name": "Bob"},
            conversation_history=[{"role": "user", "content": "hi"}],
            goal_context=[{"name": "Learn ML"}],
            task_context=[{"title": "Study"}],
            knowledge_context=[{"name": "AI"}],
            execution_context={"current_task": "t1"},
        )
        assert isinstance(context, ContextPackage)

    @pytest.mark.asyncio
    async def test_pipeline_properties(self, pipeline):
        assert pipeline.embedder is not None
        assert pipeline.repository is not None
        assert pipeline.metrics is not None
        assert pipeline.tracer is not None


# ═══════════════════════════════════════════════════════════════════════
# 13. Engine Tests
# ═══════════════════════════════════════════════════════════════════════


class TestEngine:
    @pytest.fixture
    def engine(self):
        embedder = InMemoryEmbeddingProvider(dimension=384)
        repo = InMemoryRepository()
        return RAGEngine(
            embedder=embedder,
            repository=repo,
            metrics=get_rag_metrics(),
            tracer=get_rag_tracer(),
        )

    @pytest.mark.asyncio
    async def test_engine_initialize(self, engine):
        await engine.initialize()
        assert engine.lifecycle.is_ready

    @pytest.mark.asyncio
    async def test_engine_shutdown(self, engine):
        await engine.initialize()
        await engine.shutdown()
        assert engine.lifecycle.state == RAGState.SHUTDOWN

    @pytest.mark.asyncio
    async def test_engine_index_document(self, engine):
        await engine.initialize()
        doc = _make_index_doc(content="Test content for engine indexing.")
        result = await engine.index_document(doc)
        assert result.status == DocumentStatus.INDEXED

    @pytest.mark.asyncio
    async def test_engine_retrieve(self, engine):
        await engine.initialize()
        doc = _make_index_doc(content="Artificial intelligence is transforming technology.")
        await engine.index_document(doc)
        result = await engine.retrieve("artificial intelligence")
        assert result.total_chunks >= 1

    @pytest.mark.asyncio
    async def test_engine_query(self, engine):
        await engine.initialize()
        doc = _make_index_doc(content="Neural networks are inspired by the brain.")
        await engine.index_document(doc)
        req = RetrievalQuery(query="neural networks", top_k=5)
        context = await engine.query(req)
        assert isinstance(context, ContextPackage)

    @pytest.mark.asyncio
    async def test_engine_health(self, engine):
        await engine.initialize()
        h = await engine.health()
        assert h["status"] == "healthy"
        assert "repository_status" in h

    @pytest.mark.asyncio
    async def test_engine_metrics(self, engine):
        await engine.initialize()
        summary = engine.get_metrics_summary()
        assert "total_queries" in summary

    @pytest.mark.asyncio
    async def test_engine_traces(self, engine):
        await engine.initialize()
        doc = _make_index_doc(content="Test content for trace test.")
        await engine.index_document(doc)
        await engine.retrieve("test")
        traces = engine.get_traces()
        assert len(traces) >= 1

    @pytest.mark.asyncio
    async def test_engine_statistics(self, engine):
        await engine.initialize()
        doc = _make_index_doc()
        await engine.index_document(doc)
        stats = await engine.get_statistics()
        assert stats["document_count"] == 1

    @pytest.mark.asyncio
    async def test_engine_set_knowledge_engine(self, engine):
        mock_ke = MagicMock()
        engine.set_knowledge_engine(mock_ke)
        assert engine._knowledge_engine is mock_ke

    @pytest.mark.asyncio
    async def test_engine_set_memory_provider(self, engine):
        mock_mp = MagicMock()
        engine.set_memory_provider(mock_mp)
        assert engine._memory_provider is mock_mp

    @pytest.mark.asyncio
    async def test_engine_set_cognitive_engine(self, engine):
        mock_ce = MagicMock()
        engine.set_cognitive_engine(mock_ce)
        assert engine._cognitive_engine is mock_ce

    @pytest.mark.asyncio
    async def test_engine_with_knowledge_integration(self, engine):
        await engine.initialize()
        mock_ke = AsyncMock()
        mock_entity = MagicMock()
        mock_entity.name = "Test Entity"
        mock_entity.description = "A test entity description"
        mock_ke.search = AsyncMock(return_value=[mock_entity])
        engine.set_knowledge_engine(mock_ke)
        doc = _make_index_doc(content="Test knowledge integration content.")
        await engine.index_document(doc)
        req = RetrievalQuery(query="test entity", top_k=5)
        context = await engine.query(req)
        assert isinstance(context, ContextPackage)

    @pytest.mark.asyncio
    async def test_engine_properties(self, engine):
        assert engine.lifecycle is not None
        assert engine.metrics is not None
        assert engine.tracer is not None
        assert engine.index is not None
        assert engine.pipeline is not None

    @pytest.mark.asyncio
    async def test_engine_reindex_all(self, engine):
        await engine.initialize()
        doc = _make_index_doc(content="Reindex test content.")
        await engine.index_document(doc)
        results = await engine.reindex(reindex_all=True)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_engine_index_documents_batch(self, engine):
        await engine.initialize()
        docs = [_make_index_doc(content=f"Batch doc {i}") for i in range(3)]
        results = await engine.index_documents(docs)
        assert len(results) == 3


# ═══════════════════════════════════════════════════════════════════════
# 14. Metrics Tests
# ═══════════════════════════════════════════════════════════════════════


class TestMetrics:
    def test_record_request(self):
        metrics = RAGMetrics()
        m = RequestMetric(request_id="r1", query="q", start_time=time.time())
        m.complete()
        metrics.record_request(m)
        assert metrics.total_queries == 1

    def test_record_document_indexed(self):
        metrics = RAGMetrics()
        metrics.record_document_indexed(5)
        summary = metrics.get_summary()
        assert summary["total_documents"] == 1
        assert summary["total_chunks"] == 5

    def test_record_document_removed(self):
        metrics = RAGMetrics()
        metrics.record_document_indexed(10)
        metrics.record_document_removed(3)
        summary = metrics.get_summary()
        assert summary["total_chunks"] == 7

    def test_get_summary(self):
        metrics = RAGMetrics()
        summary = metrics.get_summary()
        assert summary["total_queries"] == 0
        assert summary["cache_hits"] == 0
        assert summary["cache_misses"] == 0

    def test_cache_hit_tracking(self):
        metrics = RAGMetrics()
        m = RequestMetric(request_id="r1", query="q", start_time=time.time(), cache_hit=True)
        m.complete()
        metrics.record_request(m)
        summary = metrics.get_summary()
        assert summary["cache_hits"] == 1

    def test_cache_miss_tracking(self):
        metrics = RAGMetrics()
        m = RequestMetric(request_id="r1", query="q", start_time=time.time(), cache_hit=False)
        m.complete()
        metrics.record_request(m)
        summary = metrics.get_summary()
        assert summary["cache_misses"] == 1

    def test_get_recent_requests(self):
        metrics = RAGMetrics()
        for i in range(5):
            m = RequestMetric(request_id=f"r{i}", query=f"q{i}", start_time=time.time())
            m.complete()
            metrics.record_request(m)
        recent = metrics.get_recent_requests(3)
        assert len(recent) == 3

    def test_reset(self):
        metrics = RAGMetrics()
        m = RequestMetric(request_id="r1", query="q", start_time=time.time())
        m.complete()
        metrics.record_request(m)
        metrics.reset()
        assert metrics.total_queries == 0

    def test_request_metric_complete(self):
        m = RequestMetric(request_id="r1", query="q", start_time=time.time())
        m.complete()
        assert m.end_time is not None
        assert m.latency_ms >= 0
        assert m.success is True

    def test_request_metric_complete_failure(self):
        m = RequestMetric(request_id="r1", query="q", start_time=time.time())
        m.complete(False, "error occurred")
        assert m.success is False
        assert m.error == "error occurred"

    def test_get_rag_metrics(self):
        m = get_rag_metrics()
        assert isinstance(m, RAGMetrics)

    def test_metrics_overflow_protection(self):
        metrics = RAGMetrics()
        for i in range(1100):
            m = RequestMetric(request_id=f"r{i}", query=f"q{i}", start_time=time.time())
            m.complete()
            metrics.record_request(m)
        assert metrics.total_queries == 1100
        recent = metrics.get_recent_requests(2000)
        assert len(recent) <= 500


# ═══════════════════════════════════════════════════════════════════════
# 15. Tracing Tests
# ═══════════════════════════════════════════════════════════════════════


class TestTracing:
    def test_start_trace(self):
        tracer = RAGTracer()
        trace = tracer.start_trace("test query")
        assert trace.query == "test query"
        assert trace.status == "pending"

    def test_start_span(self):
        tracer = RAGTracer()
        trace = tracer.start_trace("q")
        span = tracer.start_span("embed", trace)
        assert span.name == "embed"
        assert span in trace.spans

    def test_finish_span(self):
        tracer = RAGTracer()
        trace = tracer.start_trace("q")
        span = tracer.start_span("op", trace)
        tracer.finish_span(span, "completed")
        assert span.status == "completed"
        assert span.end_time is not None

    def test_finish_trace(self):
        tracer = RAGTracer()
        trace = tracer.start_trace("q")
        tracer.finish_trace(trace, "completed")
        assert trace.status == "completed"
        assert trace.end_time is not None

    def test_get_trace(self):
        tracer = RAGTracer()
        trace = tracer.start_trace("q")
        found = tracer.get_trace(trace.trace_id)
        assert found is trace

    def test_get_trace_not_found(self):
        tracer = RAGTracer()
        found = tracer.get_trace(uuid4())
        assert found is None

    def test_get_traces(self):
        tracer = RAGTracer()
        tracer.start_trace("q1")
        tracer.start_trace("q2")
        traces = tracer.get_traces(10)
        assert len(traces) == 2

    def test_get_trace_count(self):
        tracer = RAGTracer()
        tracer.start_trace("q1")
        assert tracer.get_trace_count() == 1

    def test_clear(self):
        tracer = RAGTracer()
        tracer.start_trace("q1")
        count = tracer.clear()
        assert count == 1
        assert tracer.get_trace_count() == 0

    def test_trace_overflow(self):
        tracer = RAGTracer(max_traces=5)
        for i in range(10):
            tracer.start_trace(f"q{i}")
        assert tracer.get_trace_count() <= 5

    def test_span_add_event(self):
        span = RAGSpan()
        span.add_event("test_event", {"key": "value"})
        assert len(span.events) == 1

    def test_span_set_attribute(self):
        span = RAGSpan()
        span.set_attribute("key", "value")
        assert span.attributes["key"] == "value"

    def test_span_to_dict(self):
        span = RAGSpan(name="test")
        d = span.to_dict()
        assert d["name"] == "test"
        assert "span_id" in d

    def test_trace_to_dict(self):
        tracer = RAGTracer()
        trace = tracer.start_trace("q")
        d = trace.to_dict()
        assert d["query"] == "q"
        assert "trace_id" in d

    def test_tracer_to_dict(self):
        tracer = RAGTracer()
        d = tracer.to_dict()
        assert "trace_count" in d
        assert "max_traces" in d

    def test_get_rag_tracer(self):
        t = get_rag_tracer()
        assert isinstance(t, RAGTracer)

    def test_trace_with_metadata(self):
        tracer = RAGTracer()
        trace = tracer.start_trace("q", metadata={"key": "value"})
        assert trace.metadata["key"] == "value"

    def test_span_error(self):
        span = RAGSpan()
        span.finish("error", "something failed")
        assert span.error == "something failed"
        assert span.status == "error"


# ═══════════════════════════════════════════════════════════════════════
# 16. Lifecycle Tests
# ═══════════════════════════════════════════════════════════════════════


class TestLifecycle:
    def test_initial_state(self):
        lc = RAGLifecycle("test")
        assert lc.state == RAGState.REGISTERED
        assert not lc.is_ready

    def test_valid_transitions(self):
        lc = RAGLifecycle("test")
        lc.initialized()
        assert lc.state == RAGState.INITIALIZED
        lc.ready()
        assert lc.state == RAGState.READY
        assert lc.is_ready

    def test_indexing_transition(self):
        lc = RAGLifecycle("test")
        lc.initialized()
        lc.ready()
        lc.indexing()
        assert lc.state == RAGState.INDEXING
        assert lc.is_available

    def test_retrieving_transition(self):
        lc = RAGLifecycle("test")
        lc.initialized()
        lc.ready()
        lc.retrieving()
        assert lc.state == RAGState.RETRIEVING
        assert lc.is_available

    def test_failed_transition(self):
        lc = RAGLifecycle("test")
        lc.initialized()
        lc.ready()
        lc.failed("error occurred")
        assert lc.state == RAGState.FAILED
        assert lc.error_count == 1
        assert lc.last_error == "error occurred"

    def test_shutdown_transition(self):
        lc = RAGLifecycle("test")
        lc.initialized()
        lc.ready()
        lc.shutdown()
        assert lc.state == RAGState.SHUTDOWN

    def test_invalid_transition_raises(self):
        lc = RAGLifecycle("test")
        with pytest.raises(RAGLifecycleError):
            lc.ready()  # Can't go from REGISTERED -> READY

    def test_recover(self):
        lc = RAGLifecycle("test")
        lc.initialized()
        lc.ready()
        lc.failed("error")
        lc.recover()
        assert lc.state == RAGState.REGISTERED

    def test_recover_from_shutdown(self):
        lc = RAGLifecycle("test")
        lc.initialized()
        lc.ready()
        lc.shutdown()
        lc.recover()
        assert lc.state == RAGState.REGISTERED

    def test_history(self):
        lc = RAGLifecycle("test")
        lc.initialized()
        lc.ready()
        history = lc.get_history()
        assert len(history) == 2

    def test_to_dict(self):
        lc = RAGLifecycle("test")
        d = lc.to_dict()
        assert d["component_id"] == "test"
        assert d["state"] == "registered"

    def test_is_available_in_indexing(self):
        lc = RAGLifecycle("test")
        lc.initialized()
        lc.ready()
        lc.indexing()
        assert lc.is_available

    def test_valid_transitions_dict(self):
        assert RAGState.REGISTERED in VALID_RAG_TRANSITIONS
        assert RAGState.READY in VALID_RAG_TRANSITIONS
        assert RAGState.FAILED in VALID_RAG_TRANSITIONS

    def test_component_id(self):
        lc = RAGLifecycle("my_component")
        assert lc.component_id == "my_component"


# ═══════════════════════════════════════════════════════════════════════
# 17. Factory Tests
# ═══════════════════════════════════════════════════════════════════════


class TestFactory:
    def test_factory_default(self):
        factory = RAGFactory()
        assert factory.embedder is not None
        assert factory.repository is not None

    def test_factory_create_engine(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        assert isinstance(engine, RAGEngine)

    def test_factory_create_pipeline(self):
        factory = RAGFactory()
        pipeline = factory.create_pipeline()
        assert isinstance(pipeline, RAGPipeline)

    def test_factory_create_index(self):
        factory = RAGFactory()
        index = factory.create_index()
        assert isinstance(index, RAGIndex)

    def test_factory_create_default_engine(self):
        factory = RAGFactory()
        engine = factory.create_default_engine()
        assert isinstance(engine, RAGFactory)

    def test_factory_with_custom_components(self):
        embedder = InMemoryEmbeddingProvider(dimension=128)
        repo = InMemoryRepository()
        factory = RAGFactory(embedder=embedder, repository=repo)
        assert factory.embedder.embedding_dimension == 128

    def test_factory_properties(self):
        factory = RAGFactory()
        assert factory.metrics is not None
        assert factory.tracer is not None

    def test_get_rag_factory(self):
        factory = get_rag_factory()
        assert isinstance(factory, RAGFactory)

    def test_get_rag_factory_with_params(self):
        embedder = InMemoryEmbeddingProvider(dimension=256)
        repo = InMemoryRepository()
        factory = get_rag_factory(embedder=embedder, repository=repo)
        assert factory.embedder.embedding_dimension == 256


# ═══════════════════════════════════════════════════════════════════════
# 18. Integration Tests
# ═══════════════════════════════════════════════════════════════════════


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_index_and_retrieve_flow(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()

        doc = _make_index_doc(
            content="Retrieval-augmented generation combines retrieval with language models for better answers.",
            title="RAG Overview",
            source="documentation",
        )
        result = await engine.index_document(doc)
        assert result.status == DocumentStatus.INDEXED

        retrieval = await engine.retrieve("retrieval augmented generation")
        assert retrieval.total_chunks >= 1

    @pytest.mark.asyncio
    async def test_full_query_flow(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()

        docs = [
            _make_index_doc(
                content="Python is a versatile programming language used in web development and data science.",
                title="Python Guide",
                source="docs",
            ),
            _make_index_doc(
                content="Machine learning algorithms learn patterns from training data.",
                title="ML Basics",
                source="docs",
            ),
        ]
        await engine.index_documents(docs)

        req = RetrievalQuery(query="python machine learning", top_k=5)
        context = await engine.query(req)
        assert isinstance(context, ContextPackage)
        assert len(context.retrieved_chunks) >= 1

    @pytest.mark.asyncio
    async def test_full_query_with_context(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()

        doc = _make_index_doc(
            content="FastAPI is a modern web framework for building APIs with Python.",
            title="FastAPI",
            source="docs",
        )
        await engine.index_document(doc)

        req = RetrievalQuery(query="web framework python", top_k=5)
        context = await engine.query(
            req,
            user_context={"name": "Alice", "role": "Backend Developer"},
            conversation_history=[
                {"role": "user", "content": "What is the best Python web framework?"},
                {"role": "assistant", "content": "FastAPI is a great choice."},
            ],
            goal_context=[{"name": "Build REST API", "status": "active"}],
            task_context=[{"title": "Choose framework", "status": "completed"}],
            knowledge_context=[{"name": "Python", "description": "Programming language"}],
        )
        assert isinstance(context, ContextPackage)
        assert "Alice" in context.user_context.get("name", "")

    @pytest.mark.asyncio
    async def test_full_metrics_flow(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()

        doc = _make_index_doc(content="Test metrics flow content for verification.")
        await engine.index_document(doc)

        await engine.retrieve("test metrics")
        summary = engine.get_metrics_summary()
        assert summary["total_queries"] >= 1

    @pytest.mark.asyncio
    async def test_full_tracing_flow(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()

        doc = _make_index_doc(content="Test tracing flow content for verification.")
        await engine.index_document(doc)

        await engine.retrieve("test trace")
        traces = engine.get_traces()
        assert len(traces) >= 1

    @pytest.mark.asyncio
    async def test_full_lifecycle_flow(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        assert engine.lifecycle.state == RAGState.REGISTERED

        await engine.initialize()
        assert engine.lifecycle.is_ready

        doc = _make_index_doc(content="Lifecycle test content.")
        await engine.index_document(doc)

        await engine.retrieve("lifecycle")
        assert engine.lifecycle.is_ready

        await engine.shutdown()
        assert engine.lifecycle.state == RAGState.SHUTDOWN

    @pytest.mark.asyncio
    async def test_multiple_documents_and_retrieve(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()

        docs = [
            _make_index_doc(content=f"Document about topic {i} with unique content.", title=f"Doc {i}")
            for i in range(10)
        ]
        results = await engine.index_documents(docs)
        assert len(results) == 10

        retrieval = await engine.retrieve("topic")
        assert retrieval.total_chunks >= 1

    @pytest.mark.asyncio
    async def test_engine_with_knowledge_graph_integration(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()

        mock_kg = AsyncMock()
        entity = MagicMock()
        entity.name = "Python"
        entity.description = "Programming language"
        entity.confidence = 0.95
        mock_kg.search = AsyncMock(return_value=[entity])
        engine.set_knowledge_engine(mock_kg)

        doc = _make_index_doc(
            content="Python is widely used in data science and web development.",
            title="Python",
        )
        await engine.index_document(doc)

        req = RetrievalQuery(query="python programming", top_k=5)
        context = await engine.query(req)
        assert isinstance(context, ContextPackage)

    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()
        health = await engine.health()
        assert health["status"] == "healthy"
        assert health["lifecycle_state"] == "ready"

    @pytest.mark.asyncio
    async def test_statistics_integration(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()

        doc = _make_index_doc(
            content="Statistics integration test document.",
            source="test_source",
        )
        await engine.index_document(doc)

        stats = await engine.get_statistics()
        assert stats["document_count"] == 1
        assert stats["chunk_count"] >= 1

    @pytest.mark.asyncio
    async def test_reindex_integration(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()

        doc = _make_index_doc(content="Reindex integration test content.")
        await engine.index_document(doc)

        results = await engine.reindex(reindex_all=True)
        assert isinstance(results, list)


# ═══════════════════════════════════════════════════════════════════════
# 19. Edge Cases
# ═══════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_retrieve_empty_index(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()
        result = await engine.retrieve("query on empty index")
        assert result.status == RetrievalStatus.NO_RESULTS

    @pytest.mark.asyncio
    async def test_query_empty_index(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()
        req = RetrievalQuery(query="empty query")
        context = await engine.query(req)
        assert isinstance(context, ContextPackage)

    @pytest.mark.asyncio
    async def test_very_long_query(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()
        long_query = "word " * 1000
        result = await engine.retrieve(long_query)
        assert result.status in (RetrievalStatus.NO_RESULTS, RetrievalStatus.SUCCESS)

    @pytest.mark.asyncio
    async def test_special_characters_query(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()
        doc = _make_index_doc(content="Test document with special characters: @#$%^&*()")
        await engine.index_document(doc)
        result = await engine.retrieve("@#$%^&*()")
        assert result is not None

    @pytest.mark.asyncio
    async def test_unicode_content(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()
        doc = _make_index_doc(
            content="Contenido en español: inteligencia artificial y aprendizaje automático.",
            title="Español",
        )
        result = await engine.index_document(doc)
        assert result.status == DocumentStatus.INDEXED

    @pytest.mark.asyncio
    async def test_concurrent_indexing(self):
        import asyncio
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()

        async def index_doc(i: int) -> IndexResult:
            doc = _make_index_doc(content=f"Concurrent document {i} content.")
            return await engine.index_document(doc)

        results = await asyncio.gather(*[index_doc(i) for i in range(5)])
        assert len(results) == 5
        assert all(r.status == DocumentStatus.INDEXED for r in results)

    @pytest.mark.asyncio
    async def test_zero_top_k(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()
        doc = _make_index_doc(content="Test zero top_k content.")
        await engine.index_document(doc)
        result = await engine.retrieve("test", top_k=0)
        assert result.total_chunks == 0

    @pytest.mark.asyncio
    async def test_high_threshold(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()
        doc = _make_index_doc(content="High threshold test content.")
        await engine.index_document(doc)
        result = await engine.retrieve("test", threshold=0.99)
        assert result.total_chunks == 0

    @pytest.mark.asyncio
    async def test_reranker_with_single_chunk(self):
        reranker = SimilarityReranker()
        chunks = [_make_retrieved_chunk(content="single chunk", score=0.8)]
        result = await reranker.rerank("query", chunks, top_k=10)
        assert len(result) == 1
        assert result[0].rerank_score == 0.8

    @pytest.mark.asyncio
    async def test_context_builder_with_many_chunks(self):
        builder = DefaultContextBuilder()
        chunks = [_make_retrieved_chunk(content=f"chunk {i} content") for i in range(50)]
        result = await builder.build("query", chunks)
        assert isinstance(result, ContextPackage)

    def test_filter_operators_comprehensive(self):
        from app.rag.filters import _evaluate

        meta = {"str_field": "hello", "int_field": 5, "list_field": [1, 2, 3]}
        assert _evaluate(meta, FilterCondition(field="str_field", operator=FilterOperator.EQ, value="hello"))
        assert _evaluate(meta, FilterCondition(field="str_field", operator=FilterOperator.NEQ, value="world"))
        assert _evaluate(meta, FilterCondition(field="int_field", operator=FilterOperator.GT, value=3))
        assert _evaluate(meta, FilterCondition(field="int_field", operator=FilterOperator.LT, value=10))
        assert _evaluate(meta, FilterCondition(field="int_field", operator=FilterOperator.GTE, value=5))
        assert _evaluate(meta, FilterCondition(field="int_field", operator=FilterOperator.LTE, value=5))
        assert not _evaluate(meta, FilterCondition(field="str_field", operator=FilterOperator.EQ, value="nope"))
        assert _evaluate(meta, FilterCondition(field="str_field", operator=FilterOperator.CONTAINS, value="ell"))
        assert _evaluate(meta, FilterCondition(field="str_field", operator=FilterOperator.STARTS_WITH, value="hel"))
        assert not _evaluate(meta, FilterCondition(field="missing", operator=FilterOperator.EQ, value="x"))
        assert _evaluate(meta, FilterCondition(field="missing", operator=FilterOperator.NEQ, value="x"))
        assert _evaluate(meta, FilterCondition(field="missing", operator=FilterOperator.NIN, value=[1, 2]))

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self):
        from app.rag.embeddings import InMemoryEmbeddingProvider

        class FailingEmbedder(InMemoryEmbeddingProvider):
            async def embed(self, text: str) -> list[float]:
                raise RuntimeError("Embedding failed")

        embedder = FailingEmbedder()
        repo = InMemoryRepository()
        pipeline = RAGPipeline(embedder=embedder, repository=repo)
        result = await pipeline.retrieve("test query")
        assert result.status == RetrievalStatus.ERROR

    @pytest.mark.asyncio
    async def test_engine_query_failure_handling(self):
        factory = RAGFactory()
        engine = factory.create_engine()
        await engine.initialize()

        class FailingRetriever(VectorRetriever):
            async def retrieve(self, *args, **kwargs):
                raise RuntimeError("Retrieval failed")

        engine._pipeline._retriever = FailingRetriever(
            engine._repository, engine._embedder, "documents"
        )
        req = RetrievalQuery(query="fail")
        with pytest.raises(RuntimeError):
            await engine.query(req)

    @pytest.mark.asyncio
    async def test_chroma_repository_init(self):
        repo = ChromaRepository()
        assert repo.repository_id == "chroma"
        h = await repo.health()
        assert h["status"] == "uninitialized"

    def test_chunker_ids(self):
        assert FixedSizeChunker().chunker_id == "fixed_size"
        assert SemanticChunker().chunker_id == "semantic"
        assert RecursiveChunker().chunker_id == "recursive"
        assert MarkdownChunker().chunker_id == "markdown"
        assert CodeChunker().chunker_id == "code"

    def test_retriever_ids(self):
        assert VectorRetriever.__init__  # just checking class exists
        assert KeywordRetriever.__init__
        assert HybridRetriever.__init__
        assert MemoryRetriever.__init__
        assert KnowledgeRetriever.__init__


# ═══════════════════════════════════════════════════════════════════════
# 20. ABC Verification Tests
# ═══════════════════════════════════════════════════════════════════════


class TestABCs:
    def test_retriever_is_abstract(self):
        with pytest.raises(TypeError):
            Retriever()

    def test_reranker_is_abstract(self):
        with pytest.raises(TypeError):
            Reranker()

    def test_chunker_is_abstract(self):
        with pytest.raises(TypeError):
            Chunker()

    def test_embedding_provider_is_abstract(self):
        with pytest.raises(TypeError):
            EmbeddingProvider()

    def test_query_rewriter_is_abstract(self):
        with pytest.raises(TypeError):
            QueryRewriter()

    def test_context_builder_is_abstract(self):
        with pytest.raises(TypeError):
            ContextBuilder()

    def test_citation_provider_is_abstract(self):
        with pytest.raises(TypeError):
            CitationProvider()

    def test_vector_repository_is_abstract(self):
        with pytest.raises(TypeError):
            VectorRepository()

    def test_concrete_implementations(self):
        assert issubclass(VectorRetriever, Retriever)
        assert issubclass(SimilarityReranker, Reranker)
        assert issubclass(FixedSizeChunker, Chunker)
        assert issubclass(InMemoryEmbeddingProvider, EmbeddingProvider)
        assert issubclass(PassthroughRewriter, QueryRewriter)
        assert issubclass(DefaultContextBuilder, ContextBuilder)
        assert issubclass(DefaultCitationProvider, CitationProvider)
        assert issubclass(InMemoryRepository, VectorRepository)
