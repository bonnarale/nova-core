"""Tests for the original OllamaProvider (adapted for Chapter 16 interface)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import Settings
from app.models.gateway import ModelGateway
from app.models.providers.ollama import OllamaProvider
from app.models.registry import ProviderRegistry
from app.models.providers.mock import MockProvider


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    def test_init_creates_provider_with_settings_url(self) -> None:
        """Test that OllamaProvider initializes with correct base URL."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        provider = OllamaProvider(settings)
        assert provider._base_url == "http://localhost:11434"
        assert provider.provider_id == "ollama"

    def test_provider_capabilities(self) -> None:
        """Test that OllamaProvider reports capabilities."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        provider = OllamaProvider(settings)
        caps = provider.get_capabilities()
        assert caps.supports_streaming is True

    @pytest.mark.asyncio
    async def test_health_returns_uninitialized(self) -> None:
        """Test health returns uninitialized when not initialized."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        provider = OllamaProvider(settings)
        health = await provider.health()
        assert health["status"] == "uninitialized"

    @pytest.mark.asyncio
    async def test_chat_raises_when_not_initialized(self) -> None:
        """Test chat raises when provider is not initialized."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        provider = OllamaProvider(settings)
        with pytest.raises(RuntimeError, match="not initialized"):
            await provider.chat("llama3", [{"role": "user", "content": "Hello"}])

    @pytest.mark.asyncio
    async def test_list_models_raises_when_not_initialized(self) -> None:
        """Test list_models raises when provider is not initialized."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        provider = OllamaProvider(settings)
        with pytest.raises(RuntimeError, match="not initialized"):
            await provider.list_models()

    @pytest.mark.asyncio
    async def test_initialize_and_shutdown(self) -> None:
        """Test initialize and shutdown lifecycle."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        provider = OllamaProvider(settings)
        await provider.initialize()
        assert provider._initialized is True
        await provider.shutdown()
        assert provider._initialized is False

    @pytest.mark.asyncio
    async def test_count_tokens(self) -> None:
        """Test token counting."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        provider = OllamaProvider(settings)
        tokens = await provider.count_tokens("llama3", [{"role": "user", "content": "Hello world"}])
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_estimate_cost(self) -> None:
        """Test cost estimation."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        provider = OllamaProvider(settings)
        cost = await provider.estimate_cost("llama3", 100, 50)
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_close_calls_shutdown(self) -> None:
        """Test that close delegates to shutdown."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        provider = OllamaProvider(settings)
        await provider.initialize()
        await provider.close()
        assert provider._initialized is False


class TestModelGatewayLegacy:
    """Tests for ModelGateway (Chapter 16 interface)."""

    def test_init_default(self) -> None:
        """Test that ModelGateway initializes with defaults."""
        gateway = ModelGateway()
        assert gateway._initialized is False

    @pytest.mark.asyncio
    async def test_initialize(self) -> None:
        """Test gateway initialization."""
        gateway = ModelGateway()
        await gateway.initialize()
        assert gateway._initialized is True

    @pytest.mark.asyncio
    async def test_shutdown(self) -> None:
        """Test gateway shutdown."""
        gateway = ModelGateway()
        await gateway.initialize()
        await gateway.shutdown()
        assert gateway._initialized is False

    @pytest.mark.asyncio
    async def test_chat_with_mock_provider(self) -> None:
        """Test chat delegates to registered provider."""
        registry = ProviderRegistry()
        provider = MockProvider()
        registry.register("mock", provider)
        gateway = ModelGateway(registry=registry)
        await gateway.initialize()
        result = await gateway.chat(
            model="llama3",
            messages=[{"role": "user", "content": "Hello"}],
            provider="mock",
        )
        assert result["message"]["content"] == "Mock response"

    @pytest.mark.asyncio
    async def test_list_models_from_mock(self) -> None:
        """Test list_models delegates to provider."""
        registry = ProviderRegistry()
        provider = MockProvider()
        registry.register("mock", provider)
        gateway = ModelGateway(registry=registry)
        await gateway.initialize()
        models = await gateway.list_models(provider="mock")
        assert "mock-model-1" in models

    @pytest.mark.asyncio
    async def test_shutdown_closes_all(self) -> None:
        """Test that shutdown shuts down all providers."""
        registry = ProviderRegistry()
        provider = MockProvider()
        registry.register("mock", provider)
        gateway = ModelGateway(registry=registry)
        await gateway.initialize()
        await gateway.shutdown()
        assert gateway._initialized is False
