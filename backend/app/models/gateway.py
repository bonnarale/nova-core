from typing import Any

from app.core.config import Settings
from app.models.providers.base import ModelProvider
from app.models.providers.ollama import OllamaProvider


class ModelGateway:
    """Gateway for interacting with LLM model providers."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings
        self._providers: dict[str, ModelProvider] = {}

    def _get_provider(self, provider_name: str = "ollama") -> ModelProvider:
        """Get or create a provider instance.

        Args:
            provider_name: Name of the provider to use.

        Returns:
            ModelProvider instance.

        Raises:
            ValueError: If provider is not supported.
        """
        if provider_name not in self._providers:
            if provider_name == "ollama":
                if self._settings is None:
                    self._settings = Settings()
                self._providers[provider_name] = OllamaProvider(self._settings)
            else:
                raise ValueError(f"Unsupported provider: {provider_name}")
        return self._providers[provider_name]

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        provider: str = "ollama",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a chat request to a model.

        Args:
            model: The model name/identifier.
            messages: List of message dictionaries with 'role' and 'content' keys.
            provider: Provider name (default: "ollama").
            **kwargs: Additional provider-specific parameters.

        Returns:
            Response dictionary containing the model's response.
        """
        provider_instance = self._get_provider(provider)
        return await provider_instance.chat(model, messages, **kwargs)

    async def list_models(self, provider: str = "ollama") -> list[str]:
        """List available models from a provider.

        Args:
            provider: Provider name (default: "ollama").

        Returns:
            List of model names/identifiers.
        """
        provider_instance = self._get_provider(provider)
        return await provider_instance.list_models()

    async def close(self) -> None:
        """Close all provider clients."""
        for provider in self._providers.values():
            await provider.close()