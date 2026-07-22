"""Mock model provider for testing."""

import asyncio
import logging
from typing import Any, AsyncIterator

from app.models.capabilities import ProviderCapabilities, ProviderCapability
from app.models.providers.base import ModelProvider

logger = logging.getLogger(__name__)


class MockProvider(ModelProvider):
    """Mock model provider for testing."""

    def __init__(self, response: str = "Mock response", delay: float = 0.0) -> None:
        self._response = response
        self._delay = delay
        self._initialized = False
        self._chat_count = 0
        self._should_fail = False
        self._fail_count = 0

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def provider_name(self) -> str:
        return "Mock Provider"

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported=[
                ProviderCapability.CHAT,
                ProviderCapability.COMPLETION,
                ProviderCapability.STREAMING,
            ],
            max_concurrent_requests=10,
            max_tokens_per_request=4096,
            max_requests_per_minute=60,
            supports_streaming=True,
            supports_caching=True,
            supports_retry=True,
            supports_circuit_breaker=True,
        )

    async def initialize(self) -> None:
        self._initialized = True
        logger.info("Mock provider initialized")

    async def shutdown(self) -> None:
        self._initialized = False
        logger.info("Mock provider shutdown")

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "provider": self.provider_id, "chat_count": self._chat_count}

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        self._chat_count += 1
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        if self._should_fail:
            self._fail_count += 1
            raise RuntimeError("Mock provider failure")
        return {
            "message": {"content": self._response},
            "model": model,
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        self._chat_count += 1
        words = self._response.split()
        for i, word in enumerate(words):
            yield {
                "message": {"content": word + " "},
                "done": i == len(words) - 1,
            }

    async def list_models(self) -> list[str]:
        return ["mock-model-1", "mock-model-2"]

    async def get_model_info(self, model: str) -> dict[str, Any]:
        return {"name": model, "provider": self.provider_id, "parameters": "7B"}

    async def count_tokens(self, model: str, messages: list[dict[str, str]]) -> int:
        return sum(len(m.get("content", "")) // 4 for m in messages)

    async def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        return 0.001

    async def close(self) -> None:
        await self.shutdown()

    def set_should_fail(self, should_fail: bool) -> None:
        self._should_fail = should_fail

    def set_response(self, response: str) -> None:
        self._response = response

    def set_delay(self, delay: float) -> None:
        self._delay = delay

    def get_chat_count(self) -> int:
        return self._chat_count

    def get_fail_count(self) -> int:
        return self._fail_count
