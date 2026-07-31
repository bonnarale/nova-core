from abc import ABC, abstractmethod
from typing import Any


class ModelProvider(ABC):
    """Abstract interface for LLM model providers."""

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
    async def list_models(self) -> list[str]:
        """List available models from the provider.

        Returns:
            List of model names/identifiers.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the provider client and release resources."""
        ...