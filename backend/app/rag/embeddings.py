"""RAG embedding providers — generate vector embeddings from text."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

from app.rag.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using Ollama's embedding models."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        dimension: int = 768,
    ) -> None:
        self._model = model
        self._base_url = base_url
        self._dimension = dimension
        self._client: Any = None

    @property
    def provider_id(self) -> str:
        return "ollama"

    @property
    def embedding_dimension(self) -> int:
        return self._dimension

    async def _ensure_client(self) -> Any:
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(base_url=self._base_url, timeout=60.0)
            except ImportError:
                raise RuntimeError("httpx is required for OllamaEmbeddingProvider")
        return self._client

    async def embed(self, text: str) -> list[float]:
        client = await self._ensure_client()
        response = await client.post("/api/embed", json={"model": self._model, "input": text})
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings", [[]])
        return embeddings[0] if embeddings else [0.0] * self._dimension

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        client = await self._ensure_client()
        response = await client.post("/api/embed", json={"model": self._model, "input": texts})
        response.raise_for_status()
        data = response.json()
        return data.get("embeddings", [[]])

    async def health(self) -> dict[str, Any]:
        try:
            client = await self._ensure_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            return {"status": "healthy", "provider": self.provider_id, "model": self._model}
        except Exception as e:
            return {"status": "unhealthy", "provider": self.provider_id, "error": str(e)}


class InMemoryEmbeddingProvider(EmbeddingProvider):
    """Deterministic in-memory embedding provider for testing."""

    def __init__(self, dimension: int = 384) -> None:
        self._dimension = dimension

    @property
    def provider_id(self) -> str:
        return "in_memory"

    @property
    def embedding_dimension(self) -> int:
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode()).digest()
        vec = [((b - 128) / 128.0) for b in h]
        while len(vec) < self._dimension:
            vec.extend(vec[:self._dimension - len(vec)])
        return vec[:self._dimension]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "provider": self.provider_id, "dimension": self._dimension}


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using OpenAI's embedding API."""

    def __init__(self, api_key: str = "", model: str = "text-embedding-3-small", dimension: int = 1536) -> None:
        self._api_key = api_key
        self._model = model
        self._dimension = dimension
        self._client: Any = None

    @property
    def provider_id(self) -> str:
        return "openai"

    @property
    def embedding_dimension(self) -> int:
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model, "input": texts},
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy" if self._api_key else "unconfigured", "provider": self.provider_id}


class GoogleEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using Google's embedding API."""

    def __init__(self, api_key: str = "", model: str = "text-embedding-004", dimension: int = 768) -> None:
        self._api_key = api_key
        self._model = model
        self._dimension = dimension

    @property
    def provider_id(self) -> str:
        return "google"

    @property
    def embedding_dimension(self) -> int:
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:embedContent?key={self._api_key}",
                json={"model": f"models/{self._model}", "content": {"parts": [{"text": text}]}},
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]["values"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy" if self._api_key else "unconfigured", "provider": self.provider_id}


def get_embedding_provider(
    provider: str = "in_memory",
    **kwargs: Any,
) -> EmbeddingProvider:
    providers = {
        "in_memory": lambda kw: InMemoryEmbeddingProvider(dimension=kw.get("dimension", 384)),
        "ollama": lambda kw: OllamaEmbeddingProvider(
            model=kw.get("model", "nomic-embed-text"),
            base_url=kw.get("base_url", "http://localhost:11434"),
            dimension=kw.get("dimension", 768),
        ),
        "openai": lambda kw: OpenAIEmbeddingProvider(
            api_key=kw.get("api_key", ""),
            model=kw.get("model", "text-embedding-3-small"),
            dimension=kw.get("dimension", 1536),
        ),
        "google": lambda kw: GoogleEmbeddingProvider(
            api_key=kw.get("api_key", ""),
            model=kw.get("model", "text-embedding-004"),
            dimension=kw.get("dimension", 768),
        ),
    }
    factory = providers.get(provider)
    if not factory:
        raise ValueError(f"Unknown embedding provider: {provider}")
    return factory(kwargs)
