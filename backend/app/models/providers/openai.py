"""OpenAI model provider implementation."""

import logging
from typing import Any, AsyncIterator

import httpx

from app.models.capabilities import ProviderCapabilities, ProviderCapability
from app.models.providers.base import ModelProvider

logger = logging.getLogger(__name__)

DEFAULT_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]


class OpenAIProvider(ModelProvider):
    """OpenAI model provider implementation using raw httpx."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1") -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._client: httpx.AsyncClient | None = None
        self._initialized = False

    @property
    def provider_id(self) -> str:
        return "openai"

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported=[
                ProviderCapability.CHAT,
                ProviderCapability.COMPLETION,
                ProviderCapability.STREAMING,
            ],
            max_concurrent_requests=10,
            max_tokens_per_request=128000,
            max_requests_per_minute=60,
            supports_streaming=True,
            supports_caching=True,
            supports_retry=True,
            supports_circuit_breaker=True,
        )

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=180.0,
        )
        self._initialized = True
        logger.info("OpenAI provider initialized: %s", self._base_url)

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._initialized = False
        logger.info("OpenAI provider shutdown")

    async def health(self) -> dict[str, Any]:
        if not self._client:
            return {"status": "uninitialized", "provider": self.provider_id}
        try:
            response = await self._client.get("/models")
            response.raise_for_status()
            data = response.json()
            return {
                "status": "healthy",
                "provider": self.provider_id,
                "models": len(data.get("data", [])),
            }
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
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        payload.update(kwargs)
        logger.info("OpenAI chat request: model=%s", model)
        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        # Map to internal format
        content = ""
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")

        return {
            "message": {"content": content},
            "model": data.get("model", model),
            "usage": {
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                "total_tokens": data.get("usage", {}).get("total_tokens", 0),
            },
        }

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        if not self._client:
            raise RuntimeError("Provider not initialized")
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        payload.update(kwargs)
        logger.info("OpenAI streaming chat request: model=%s", model)
        async with self._client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    import json
                    if line.startswith("data: "):
                        line = line[6:]
                    if line.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if delta.get("content"):
                            yield {
                                "message": {"content": delta["content"]},
                                "done": False,
                            }
                    except json.JSONDecodeError:
                        continue
            yield {"message": {"content": ""}, "done": True}

    async def list_models(self) -> list[str]:
        if not self._client:
            raise RuntimeError("Provider not initialized")
        try:
            response = await self._client.get("/models")
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return list(DEFAULT_MODELS)

    async def get_model_info(self, model: str) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("Provider not initialized")
        try:
            response = await self._client.get(f"/models/{model}")
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
        cost_map: dict[str, tuple[float, float]] = {
            "gpt-4o": (0.0025 / 1000, 0.01 / 1000),
            "gpt-4o-mini": (0.00015 / 1000, 0.0006 / 1000),
            "gpt-3.5-turbo": (0.0005 / 1000, 0.0015 / 1000),
        }
        input_cost_per_token, output_cost_per_token = cost_map.get(
            model, (0.0025 / 1000, 0.01 / 1000)
        )
        return input_tokens * input_cost_per_token + output_tokens * output_cost_per_token

    async def close(self) -> None:
        await self.shutdown()
