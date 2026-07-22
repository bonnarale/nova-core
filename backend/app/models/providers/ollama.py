"""Ollama model provider implementation."""

import logging
from typing import Any, AsyncIterator

import httpx

from app.core.config import Settings
from app.models.capabilities import ProviderCapabilities, ProviderCapability
from app.models.providers.base import ModelProvider

logger = logging.getLogger(__name__)


class OllamaProvider(ModelProvider):
    """Ollama model provider implementation."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.ollama_url
        self._client: httpx.AsyncClient | None = None
        self._initialized = False

    @property
    def provider_id(self) -> str:
        return "ollama"

    @property
    def provider_name(self) -> str:
        return "Ollama"

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported=[
                ProviderCapability.CHAT,
                ProviderCapability.COMPLETION,
                ProviderCapability.STREAMING,
            ],
            max_concurrent_requests=5,
            max_tokens_per_request=4096,
            max_requests_per_minute=60,
            supports_streaming=True,
            supports_caching=False,
            supports_retry=True,
            supports_circuit_breaker=True,
        )

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)
        self._initialized = True
        logger.info("Ollama provider initialized: %s", self._base_url)

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._initialized = False
        logger.info("Ollama provider shutdown")

    async def health(self) -> dict[str, Any]:
        if not self._client:
            return {"status": "uninitialized", "provider": self.provider_id}
        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
            return {"status": "healthy", "provider": self.provider_id, "models": len(response.json().get("models", []))}
        except Exception as e:
            return {"status": "unhealthy", "provider": self.provider_id, "error": str(e)}

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("Provider not initialized")
        payload = {"model": model, "messages": messages, "stream": False, **kwargs}
        logger.info("Ollama chat request: model=%s", model)
        response = await self._client.post("/api/chat", json=payload)
        response.raise_for_status()
        return response.json()

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        if not self._client:
            raise RuntimeError("Provider not initialized")
        payload = {"model": model, "messages": messages, "stream": True, **kwargs}
        logger.info("Ollama streaming chat request: model=%s", model)
        async with self._client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    import json
                    yield json.loads(line)

    async def list_models(self) -> list[str]:
        if not self._client:
            raise RuntimeError("Provider not initialized")
        response = await self._client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        return [model["name"] for model in data.get("models", [])]

    async def get_model_info(self, model: str) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("Provider not initialized")
        try:
            response = await self._client.post("/api/show", json={"name": model})
            response.raise_for_status()
            return response.json()
        except Exception:
            return {"name": model, "provider": self.provider_id}

    async def count_tokens(self, model: str, messages: list[dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += len(content) // 4
        return total

    async def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        return 0.0

    async def close(self) -> None:
        await self.shutdown()
