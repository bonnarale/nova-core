"""Tests for OpenAI provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.providers.openai import OpenAIProvider, DEFAULT_MODELS


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    def test_init_creates_provider(self) -> None:
        """Test that OpenAIProvider initializes with correct config."""
        provider = OpenAIProvider(api_key="test-key", base_url="https://api.openai.com/v1")
        assert provider._api_key == "test-key"
        assert provider._base_url == "https://api.openai.com/v1"
        assert provider.provider_id == "openai"
        assert provider.provider_name == "OpenAI"

    def test_provider_capabilities(self) -> None:
        """Test that OpenAIProvider reports capabilities."""
        provider = OpenAIProvider(api_key="test-key")
        caps = provider.get_capabilities()
        assert caps.supports_streaming is True
        assert caps.max_tokens_per_request == 128000

    @pytest.mark.asyncio
    async def test_health_returns_uninitialized(self) -> None:
        """Test health returns uninitialized when not initialized."""
        provider = OpenAIProvider(api_key="test-key")
        health = await provider.health()
        assert health["status"] == "uninitialized"

    @pytest.mark.asyncio
    async def test_chat_raises_when_not_initialized(self) -> None:
        """Test chat raises when provider is not initialized."""
        provider = OpenAIProvider(api_key="test-key")
        with pytest.raises(RuntimeError, match="not initialized"):
            await provider.chat("gpt-4o", [{"role": "user", "content": "Hello"}])

    @pytest.mark.asyncio
    async def test_list_models_raises_when_not_initialized(self) -> None:
        """Test list_models raises when provider is not initialized."""
        provider = OpenAIProvider(api_key="test-key")
        with pytest.raises(RuntimeError, match="not initialized"):
            await provider.list_models()

    @pytest.mark.asyncio
    async def test_initialize_and_shutdown(self) -> None:
        """Test initialize and shutdown lifecycle."""
        provider = OpenAIProvider(api_key="test-key")
        await provider.initialize()
        assert provider._initialized is True
        assert provider._client is not None
        await provider.shutdown()
        assert provider._initialized is False
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_count_tokens(self) -> None:
        """Test token counting."""
        provider = OpenAIProvider(api_key="test-key")
        tokens = await provider.count_tokens("gpt-4o", [{"role": "user", "content": "Hello world"}])
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_estimate_cost(self) -> None:
        """Test cost estimation."""
        provider = OpenAIProvider(api_key="test-key")
        cost = await provider.estimate_cost("gpt-4o", 1000, 500)
        assert cost > 0

    @pytest.mark.asyncio
    async def test_close_calls_shutdown(self) -> None:
        """Test that close delegates to shutdown."""
        provider = OpenAIProvider(api_key="test-key")
        await provider.initialize()
        await provider.close()
        assert provider._initialized is False

    @pytest.mark.asyncio
    async def test_health_with_mock_client_success(self) -> None:
        """Test health returns healthy when API responds."""
        provider = OpenAIProvider(api_key="test-key")
        await provider.initialize()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]}
        provider._client.get = AsyncMock(return_value=mock_response)
        health = await provider.health()
        assert health["status"] == "healthy"
        assert health["models"] == 2
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_health_with_mock_client_failure(self) -> None:
        """Test health returns unhealthy when API fails."""
        provider = OpenAIProvider(api_key="test-key")
        await provider.initialize()
        provider._client.get = AsyncMock(side_effect=Exception("Connection refused"))
        health = await provider.health()
        assert health["status"] == "unhealthy"
        assert "error" in health
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_chat_with_mock_client(self) -> None:
        """Test chat returns response from OpenAI API."""
        provider = OpenAIProvider(api_key="test-key")
        await provider.initialize()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}}],
            "model": "gpt-4o",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        provider._client.post = AsyncMock(return_value=mock_response)
        result = await provider.chat("gpt-4o", [{"role": "user", "content": "Hello"}])
        assert result["message"]["content"] == "Hello!"
        assert result["usage"]["prompt_tokens"] == 10
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_chat_stream_with_mock_client(self) -> None:
        """Test chat_stream yields chunks from OpenAI API."""
        provider = OpenAIProvider(api_key="test-key")
        await provider.initialize()

        # Mock the streaming response
        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)
        mock_stream.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            lines = [
                'data: {"choices":[{"delta":{"content":"Hello"}}]}',
                'data: {"choices":[{"delta":{"content":" world"}}]}',
                "data: [DONE]",
            ]
            for line in lines:
                yield line

        mock_stream.aiter_lines = mock_aiter_lines
        provider._client.stream = MagicMock(return_value=mock_stream)

        chunks = []
        async for chunk in provider.chat_stream("gpt-4o", [{"role": "user", "content": "Hello"}]):
            chunks.append(chunk)

        assert len(chunks) > 0
        # Should have content chunks + final done chunk
        content_chunks = [c for c in chunks if c.get("message", {}).get("content")]
        assert len(content_chunks) >= 2
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_list_models_with_mock_client(self) -> None:
        """Test list_models returns model IDs from API."""
        provider = OpenAIProvider(api_key="test-key")
        await provider.initialize()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]
        }
        provider._client.get = AsyncMock(return_value=mock_response)
        models = await provider.list_models()
        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_list_models_fallback_on_error(self) -> None:
        """Test list_models returns defaults on API error."""
        provider = OpenAIProvider(api_key="test-key")
        await provider.initialize()
        provider._client.get = AsyncMock(side_effect=Exception("API error"))
        models = await provider.list_models()
        assert models == list(DEFAULT_MODELS)
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_get_model_info_with_mock_client(self) -> None:
        """Test get_model_info returns model data."""
        provider = OpenAIProvider(api_key="test-key")
        await provider.initialize()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"id": "gpt-4o", "object": "model"}
        provider._client.get = AsyncMock(return_value=mock_response)
        info = await provider.get_model_info("gpt-4o")
        assert info["id"] == "gpt-4o"
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_estimate_cost_gpt4o_mini(self) -> None:
        """Test cost estimation for GPT-4o mini."""
        provider = OpenAIProvider(api_key="test-key")
        cost = await provider.estimate_cost("gpt-4o-mini", 1000, 500)
        assert cost > 0
        # gpt-4o-mini is cheaper than gpt-4o
        cost_gpt4o = await provider.estimate_cost("gpt-4o", 1000, 500)
        assert cost < cost_gpt4o
