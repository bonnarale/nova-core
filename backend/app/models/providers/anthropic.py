"""Anthropic model provider implementation."""

import logging
from typing import Any, AsyncIterator

import httpx

from app.models.capabilities import ProviderCapabilities, ProviderCapability
from app.models.providers.base import ModelProvider

logger = logging.getLogger(__name__)

DEFAULT_MODELS = ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]


class AnthropicProvider(ModelProvider):
    """Anthropic model provider implementation using raw httpx."""

    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com") -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._client: httpx.AsyncClient | None = None
        self._initialized = False

    @property
    def provider_id(self) -> str:
        return "anthropic"

    @property
    def provider_name(self) -> str:
        return "Anthropic"

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported=[
                ProviderCapability.CHAT,
                ProviderCapability.COMPLETION,
                ProviderCapability.STREAMING,
            ],
            max_concurrent_requests=10,
            max_tokens_per_request=200000,
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
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=180.0,
        )
        self._initialized = True
        logger.info("Anthropic provider initialized: %s", self._base_url)

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._initialized = False
        logger.info("Anthropic provider shutdown")

    async def health(self) -> dict[str, Any]:
        if not self._client:
            return {"status": "uninitialized", "provider": self.provider_id}
        try:
            # Anthropic doesn't have a dedicated health endpoint,
            # so we use a minimal message to verify auth
            response = await self._client.post(
                "/v1/messages",
                json={
                    "model": DEFAULT_MODELS[0],
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            if response.status_code == 401:
                return {"status": "unhealthy", "provider": self.provider_id, "error": "Invalid API key"}
            return {"status": "healthy", "provider": self.provider_id}
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

        # Extract system message (Anthropic requires it as a separate param)
        system_msg = ""
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg.get("content", "")
            else:
                filtered_messages.append(msg)

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": kwargs.pop("max_tokens", 4096),
            "messages": filtered_messages,
        }
        if system_msg:
            payload["system"] = system_msg
        payload.update(kwargs)

        logger.info("Anthropic chat request: model=%s", model)
        response = await self._client.post("/v1/messages", json=payload)
        response.raise_for_status()
        data = response.json()

        # Map to internal format
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        return {
            "message": {"content": content},
            "model": data.get("model", model),
            "usage": {
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                "total_tokens": (
                    data.get("usage", {}).get("input_tokens", 0)
                    + data.get("usage", {}).get("output_tokens", 0)
                ),
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

        # Extract system message
        system_msg = ""
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg.get("content", "")
            else:
                filtered_messages.append(msg)

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": kwargs.pop("max_tokens", 4096),
            "messages": filtered_messages,
            "stream": True,
        }
        if system_msg:
            payload["system"] = system_msg
        payload.update(kwargs)

        logger.info("Anthropic streaming chat request: model=%s", model)
        async with self._client.stream("POST", "/v1/messages", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                import json
                if line.startswith("data: "):
                    line = line[6:]
                try:
                    event = json.loads(line)
                    event_type = event.get("type", "")
                    if event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            yield {"message": {"content": text}, "done": False}
                    elif event_type == "message_stop":
                        break
                except json.JSONDecodeError:
                    continue
            yield {"message": {"content": ""}, "done": True}

    async def list_models(self) -> list[str]:
        if not self._client:
            raise RuntimeError("Provider not initialized")
        # Anthropic doesn't expose a models list endpoint
        return list(DEFAULT_MODELS)

    async def get_model_info(self, model: str) -> dict[str, Any]:
        return {"name": model, "provider": self.provider_id}

    async def count_tokens(self, model: str, messages: list[dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += len(content) // 4
        return total

    async def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        cost_map: dict[str, tuple[float, float]] = {
            "claude-sonnet-4-20250514": (0.003 / 1000, 0.015 / 1000),
            "claude-3-5-haiku-20241022": (0.0008 / 1000, 0.004 / 1000),
            "claude-3-opus-20240229": (0.015 / 1000, 0.075 / 1000),
        }
        input_cost_per_token, output_cost_per_token = cost_map.get(
            model, (0.003 / 1000, 0.015 / 1000)
        )
        return input_tokens * input_cost_per_token + output_tokens * output_cost_per_token

    async def close(self) -> None:
        await self.shutdown()
