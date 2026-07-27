"""End-to-end test: SemanticMemory with REAL Ollama (nomic-embed-text + ChromaDB).

These tests require:
  - Ollama running on localhost:11434
  - nomic-embed-text model pulled

Run with: pytest tests/backend/test_e2e_semantic_memory.py -v -m e2e
"""
from __future__ import annotations

import httpx
import pytest


def ollama_available() -> bool:
    """Check if Ollama is running and nomic-embed-text is available."""
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in response.json().get("models", [])]
        return any("nomic-embed-text" in m for m in models)
    except Exception:
        return False


pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.e2e,
    pytest.mark.skipif(
        not ollama_available(),
        reason="Ollama or nomic-embed-text not available"
    ),
]


def _local_settings():
    """Settings pointing at localhost:11434 (bypasses .env file)."""
    from unittest.mock import patch
    from app.core.config import Settings
    with patch.dict("os.environ", {
        "OLLAMA_HOST": "localhost",
        "OLLAMA_PORT": "11434",
        "OLLAMA_EMBEDDING_MODEL": "nomic-embed-text",
    }):
        return Settings(_env_file=None)


# ------------------------------------------------------------------
# 1. Raw Ollama embedding endpoint
# ------------------------------------------------------------------

class TestOllamaEmbeddingRaw:
    """Direct tests against Ollama /api/embeddings endpoint."""

    async def test_embedding_returns_768_dims(self):
        """nomic-embed-text produces 768-dimensional vectors."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": "Hello world"},
                timeout=10,
            )
            data = response.json()
            embedding = data.get("embedding", [])
            assert len(embedding) == 768, f"Expected 768 dims, got {len(embedding)}"

    async def test_embedding_values_are_finite(self):
        """Embedding values should be finite floats."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": "Test values"},
                timeout=10,
            )
            embedding = response.json()["embedding"]
            assert all(isinstance(x, float) for x in embedding)
            assert all(-100 < x < 100 for x in embedding)

    async def test_similar_inputs_have_similar_embeddings(self):
        """Semantically similar inputs should produce similar embeddings."""
        async with httpx.AsyncClient() as client:
            resp1 = await client.post(
                "http://localhost:11434/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": "How do neural networks work?"},
                timeout=10,
            )
            resp2 = await client.post(
                "http://localhost:11434/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": "Explain neural network architecture"},
                timeout=10,
            )
            resp3 = await client.post(
                "http://localhost:11434/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": "What is the capital of France?"},
                timeout=10,
            )
            e1 = resp1.json()["embedding"]
            e2 = resp2.json()["embedding"]
            e3 = resp3.json()["embedding"]

            def cosine(a, b):
                dot = sum(x*y for x, y in zip(a, b))
                na = sum(x**2 for x in a) ** 0.5
                nb = sum(x**2 for x in b) ** 0.5
                return dot / (na * nb) if na > 0 and nb > 0 else 0

            sim_related = cosine(e1, e2)
            sim_unrelated = cosine(e1, e3)

            assert sim_related > sim_unrelated, (
                f"Related ({sim_related:.3f}) should be more similar "
                f"than unrelated ({sim_unrelated:.3f})"
            )


# ------------------------------------------------------------------
# 2. OllamaService.embed integration
# ------------------------------------------------------------------

class TestOllamaServiceEmbed:
    """Test the app's OllamaService.embed method with real Ollama."""

    async def test_ollama_service_embed(self):
        """OllamaService.embed returns a valid embedding."""
        from app.services.ollama import OllamaService

        settings = _local_settings()
        service = OllamaService(settings)
        embedding = await service.embed("Test OllamaService integration")

        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)
        await service.close()


# ------------------------------------------------------------------
# 3. OllamaEmbeddingProvider integration
# ------------------------------------------------------------------

class TestOllamaEmbeddingProviderIntegration:
    """Test the EmbeddingProvider abstraction with real Ollama."""

    async def test_provider_returns_valid_embedding(self):
        """OllamaEmbeddingProvider.embed produces 768-dim vector."""
        from app.memory.embeddings import OllamaEmbeddingProvider
        from app.services.ollama import OllamaService

        settings = _local_settings()
        service = OllamaService(settings)
        provider = OllamaEmbeddingProvider(ollama=service)
        embedding = await provider.embed("Test embedding provider")

        assert len(embedding) == 768
        assert isinstance(embedding[0], float)
        await service.close()


# ------------------------------------------------------------------
# 4. Full SemanticMemory RAG pipeline
# ------------------------------------------------------------------

class TestSemanticMemoryRAGPipeline:
    """Full store -> search pipeline with real Ollama + ChromaDB (in-memory)."""

    async def test_store_and_search(self):
        """Store a document and search for related content."""
        import chromadb
        from app.memory.embeddings import OllamaEmbeddingProvider
        from app.memory.semantic import SemanticMemory
        from app.memory.vector_store import ChromaDBVectorStore
        from app.services.ollama import OllamaService

        settings = _local_settings()
        service = OllamaService(settings)
        embedder = OllamaEmbeddingProvider(ollama=service)
        client = chromadb.Client()
        vector_store = ChromaDBVectorStore(chroma_client=client)
        sm = SemanticMemory(embedder=embedder, vector_store=vector_store)

        # Store some knowledge
        await sm.store(session_id=None, content="Python is a high-level programming language known for readability")
        await sm.store(session_id=None, content="FastAPI is a modern Python web framework for building APIs")
        await sm.store(session_id=None, content="Docker containers package applications with their dependencies")

        # Search for Python-related content
        results = await sm.search("Tell me about Python programming", top_k=2)

        assert len(results) > 0
        top_content = results[0].get("content", "")
        assert "Python" in top_content or "python" in top_content.lower()
        await service.close()

    async def test_index_profile_facts(self):
        """index_profile_facts stores user profile data."""
        import chromadb
        from app.memory.embeddings import OllamaEmbeddingProvider
        from app.memory.semantic import SemanticMemory
        from app.memory.vector_store import ChromaDBVectorStore
        from app.services.ollama import OllamaService

        settings = _local_settings()
        service = OllamaService(settings)
        embedder = OllamaEmbeddingProvider(ollama=service)
        client = chromadb.Client()
        vector_store = ChromaDBVectorStore(chroma_client=client)
        sm = SemanticMemory(embedder=embedder, vector_store=vector_store)

        await sm.index_profile_facts({
            "name": "Alice",
            "facts": ["Alice is a Python developer"],
            "preferences": {"theme": "dark"},
        })

        results = await sm.search("Alice Python developer", top_k=1)
        assert len(results) > 0
        await service.close()

    async def test_index_goals(self):
        """index_goals stores goal data."""
        import chromadb
        from app.memory.embeddings import OllamaEmbeddingProvider
        from app.memory.semantic import SemanticMemory
        from app.memory.vector_store import ChromaDBVectorStore
        from app.services.ollama import OllamaService

        settings = _local_settings()
        service = OllamaService(settings)
        embedder = OllamaEmbeddingProvider(ollama=service)
        client = chromadb.Client()
        vector_store = ChromaDBVectorStore(chroma_client=client)
        sm = SemanticMemory(embedder=embedder, vector_store=vector_store)

        await sm.index_goals([
            {"title": "Learn FastAPI", "description": "Build REST APIs with Python", "id": "g1", "status": "active"},
        ])

        results = await sm.search("FastAPI REST APIs", top_k=1)
        assert len(results) > 0
        assert "FastAPI" in results[0]["content"]
        await service.close()
