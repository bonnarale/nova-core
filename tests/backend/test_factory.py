"""Tests for ModelGatewayFactory dynamic registration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from os import environ

from app.core.config import Settings
from app.models.factory import ModelGatewayFactory
from app.models.providers.base import ModelProvider
from app.models.providers.ollama import OllamaProvider
from app.models.providers.openai import OpenAIProvider
from app.models.providers.anthropic import AnthropicProvider


class TestFactoryRegistration:
    """Tests for provider class registration."""

    def test_register_provider_class(self) -> None:
        """Test registering a provider class."""
        factory = ModelGatewayFactory()
        ModelGatewayFactory.register_provider_class("test", MockProviderForFactory)
        assert "test" in ModelGatewayFactory.get_registered_classes()

    def test_get_registered_classes_returns_copy(self) -> None:
        """Test get_registered_classes returns a copy."""
        classes = ModelGatewayFactory.get_registered_classes()
        classes["injected"] = MockProviderForFactory
        assert "injected" not in ModelGatewayFactory.get_registered_classes()

    def test_create_provider_dispatches_to_registry(self) -> None:
        """Test create_provider uses registered class."""
        factory = ModelGatewayFactory()
        ModelGatewayFactory.register_provider_class("test_dispatch", MockProviderForFactory)
        try:
            provider = factory.create_provider("test1", "test_dispatch")
            assert isinstance(provider, MockProviderForFactory)
        finally:
            ModelGatewayFactory._provider_classes.pop("test_dispatch", None)

    def test_create_ollama_provider_backward_compatible(self) -> None:
        """Test create_provider with ollama still works."""
        factory = ModelGatewayFactory()
        provider = factory.create_provider("ollama", "ollama")
        assert isinstance(provider, OllamaProvider)

    def test_create_provider_unknown_type_raises(self) -> None:
        """Test create_provider with unknown type raises ValueError."""
        factory = ModelGatewayFactory()
        with pytest.raises(ValueError, match="Unknown provider type"):
            factory.create_provider("test", "nonexistent")

    @patch.dict(environ, {"OPENAI_API_KEY": "test-openai-key"})
    def test_create_cloud_providers_openai(self) -> None:
        """Test create_cloud_providers creates OpenAI when key present."""
        settings = Settings()
        factory = ModelGatewayFactory(settings)
        providers = factory.create_cloud_providers()
        assert len(providers) == 1
        assert isinstance(providers[0], OpenAIProvider)

    @patch.dict(environ, {"ANTHROPIC_API_KEY": "test-anthropic-key"})
    def test_create_cloud_providers_anthropic(self) -> None:
        """Test create_cloud_providers creates Anthropic when key present."""
        settings = Settings()
        factory = ModelGatewayFactory(settings)
        providers = factory.create_cloud_providers()
        assert len(providers) == 1
        assert isinstance(providers[0], AnthropicProvider)

    def test_create_cloud_providers_no_keys(self) -> None:
        """Test create_cloud_providers returns empty when no keys."""
        settings = Settings()
        factory = ModelGatewayFactory(settings)
        providers = factory.create_cloud_providers()
        assert len(providers) == 0

    @patch.dict(environ, {
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
    })
    def test_create_cloud_providers_both(self) -> None:
        """Test create_cloud_providers creates both when keys present."""
        settings = Settings()
        factory = ModelGatewayFactory(settings)
        providers = factory.create_cloud_providers()
        assert len(providers) == 2
        types = {type(p).__name__ for p in providers}
        assert "OpenAIProvider" in types
        assert "AnthropicProvider" in types


class TestFactoryCreateDefaultGateway:
    """Tests for create_default_gateway with cloud providers."""

    @patch.dict(environ, {"OPENAI_API_KEY": "test-key"})
    def test_default_gateway_includes_openai(self) -> None:
        """Test default gateway registers OpenAI when key is set."""
        factory = ModelGatewayFactory()
        gateway = factory.create_default_gateway()
        registry = factory.get_registry()
        assert "openai" in registry.list_providers()

    def test_default_gateway_has_ollama(self) -> None:
        """Test default gateway always has Ollama."""
        factory = ModelGatewayFactory()
        gateway = factory.create_default_gateway()
        registry = factory.get_registry()
        assert "ollama" in registry.list_providers()


class MockProviderForFactory(ModelProvider):
    """Minimal mock provider for factory tests."""

    @property
    def provider_id(self) -> str:
        return "mock_factory"

    @property
    def provider_name(self) -> str:
        return "Mock Factory Provider"

    def get_capabilities(self):
        from app.models.capabilities import ProviderCapabilities
        return ProviderCapabilities()

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health(self) -> dict:
        return {"status": "healthy", "provider": self.provider_id}

    async def chat(self, model: str, messages: list[dict[str, str]], **kwargs) -> dict:
        return {"message": {"content": "Mock"}}

    async def chat_stream(self, model: str, messages: list[dict[str, str]], **kwargs):
        yield {"message": {"content": "Mock"}, "done": True}

    async def list_models(self) -> list[str]:
        return ["mock-model"]

    async def get_model_info(self, model: str) -> dict:
        return {"name": model}

    async def count_tokens(self, model: str, messages: list[dict[str, str]]) -> int:
        return 0

    async def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        return 0.0

    async def close(self) -> None:
        pass
