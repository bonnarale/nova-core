import json
import logging
from typing import Any

import httpx

from app.core.config import Settings
from app.models.providers.base import ModelProvider

logger = logging.getLogger(__name__)


class OllamaProvider(ModelProvider):
    """Ollama model provider implementation."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_url
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a chat request to Ollama.

        Args:
            model: The model name/identifier.
            messages: List of message dictionaries with 'role' and 'content' keys.
            **kwargs: Additional parameters (temperature, max_tokens, stream, etc.).

        Returns:
            Response dictionary containing the model's response.
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            **kwargs,
        }

        logger.info("=== MEMORY_AUDIT [OllamaProvider] request payload ===")
        logger.info("payload=%s", json.dumps(payload, indent=2, ensure_ascii=False))

        response = await self._client.post("/api/chat", json=payload)
        response.raise_for_status()

        raw = response.json()
        logger.info("=== MEMORY_AUDIT [OllamaProvider] raw response ===")
        logger.info("response=%s", json.dumps(raw, indent=2, ensure_ascii=False))
        return raw

    async def list_models(self) -> list[str]:
        """List available models from Ollama.

        Returns:
            List of model names/identifiers.
        """
        response = await self._client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        return [model["name"] for model in data.get("models", [])]

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()