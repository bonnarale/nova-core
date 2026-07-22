"""Base model provider interface."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional

from app.models.capabilities import ProviderCapabilities


class ModelProvider(ABC):
    """Abstract interface for LLM model providers.

    Extended interface supporting:
    - Provider lifecycle (initialize, shutdown, health)
    - Chat completion with streaming
    - Model listing and capabilities
    - Token counting and cost estimation
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name for this provider."""
        ...

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities."""
        ...

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider (create clients, validate credentials)."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the provider and release resources."""
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Check provider health status.

        Returns:
            Dictionary with health status information.
        """
        ...

    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a chat request to the model.

        Args:
            model: The model name/identifier.
            messages: List of message dictionaries with 'role' and 'content' keys.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Response dictionary containing the model's response.
        """
        ...

    @abstractmethod
    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat response from the model.

        Args:
            model: The model name/identifier.
            messages: List of message dictionaries with 'role' and 'content' keys.
            **kwargs: Additional provider-specific parameters.

        Yields:
            Response chunks as dictionaries.
        """
        ...
        yield {}  # pragma: no cover

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models from the provider.

        Returns:
            List of model names/identifiers.
        """
        ...

    @abstractmethod
    async def get_model_info(self, model: str) -> dict[str, Any]:
        """Get detailed information about a model.

        Args:
            model: The model name/identifier.

        Returns:
            Dictionary with model information.
        """
        ...

    @abstractmethod
    async def count_tokens(self, model: str, messages: list[dict[str, str]]) -> int:
        """Count tokens in a message list.

        Args:
            model: The model name/identifier.
            messages: List of message dictionaries.

        Returns:
            Estimated token count.
        """
        ...

    @abstractmethod
    async def estimate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate cost for a request.

        Args:
            model: The model name/identifier.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the provider client and release resources."""
        ...
