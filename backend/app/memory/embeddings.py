"""OllamaEmbeddingProvider — concrete EmbeddingProvider using Ollama."""

from __future__ import annotations

import logging

from app.memory.providers import EmbeddingProvider
from app.services.ollama import OllamaService

logger = logging.getLogger(__name__)


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Generates embeddings via Ollama's /api/embeddings endpoint."""

    def __init__(self, ollama: OllamaService) -> None:
        self._ollama = ollama

    async def embed(self, text: str) -> list[float]:
        embedding = await self._ollama.embed(text)
        if not embedding:
            logger.warning("Empty embedding returned for text (len=%d)", len(text))
            return []
        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            emb = await self.embed(text)
            results.append(emb)
        return results
