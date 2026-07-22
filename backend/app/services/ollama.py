import logging

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class OllamaService:
    def __init__(self, settings: Settings) -> None:
        self._client = httpx.AsyncClient(base_url=settings.ollama_url, timeout=30)
        self._embedding_model = settings.ollama_embedding_model

    async def ready(self) -> bool:
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for *text* via Ollama."""
        try:
            response = await self._client.post(
                "/api/embeddings",
                json={"model": self._embedding_model, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
        except Exception:
            logger.warning("embedding failed for text (len=%d), returning fallback", len(text))
            return []

    async def close(self) -> None:
        await self._client.aclose()

