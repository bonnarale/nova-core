"""Tests for Anthropic provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.providers.anthropic import AnthropicProvider, DEFAULT_MODELS


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    def test_init_creates_provider(self) -> None:
        """Test that AnthropicProvider initializes with correct config."""
        provider = AnthropicProvider(api_key="test-key", base_url="https://api.anthropic.com")
        assert provider._api_key == "test-key"
        assert provider._base_url == "https://api.anthropic.com"
        assert provider.provider_id == "anthropic"
        assert provider.provider_name == "Anthropic"

    def test_provider_capabilities(self) -> None:
        """Test that AnthropicProvider reports capabilities."""
        provider = AnthropicProvider(api_key="test-key")
        caps = provider.get_capabilities()
        assert caps.supports_streaming is True
        assert caps.max_tokens_per_request == 200000

    @pytest.mark.asyncio
    async def test_health_returns_uninitialized(self) -> None:
        """Test health returns uninitialized when not initialized."""
        provider = AnthropicProvider(api_key="test-key")
        health = await provider.health()
        assert health["status"] == "uninitialized"

    @pytest.mark.asyncio
    async def test_chat_raises_when_not_initialized(self) -> None:
        """Test chat raises when provider is not initialized."""
        provider = AnthropicProvider(api_key="test-key")
        with pytest.raises(RuntimeError, match="not initialized"):
            await provider.chat("claude-3-5-haiku-20241022", [{"role": "user", "content": "Hello"}])

    @pytest.mark.asyncio
    async def test_list_models_raises_when_not_initialized(self) -> None:
        """Test list_models raises when provider is not initialized."""
        provider = AnthropicProvider(api_key="test-key")
        with pytest.raises(RuntimeError, match="not initialized"):
            await provider.list_models()

    @pytest.mark.asyncio
    async def test_initialize_and_shutdown(self) -> None:
        """Test initialize and shutdown lifecycle."""
        provider = AnthropicProvider(api_key="test-key")
        await provider.initialize()
        assert provider._initialized is True
        assert provider._client is not None
        await provider.shutdown()
        assert provider._initialized is False
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_count_tokens(self) -> None:
        """Test token counting."""
        provider = AnthropicProvider(api_key="test-key")
        tokens = await provider.count_tokens("claude-3-5-haiku-20241022", [{"role": "user", "content": "Hello world"}])
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_estimate_cost(self) -> None:
        """Test cost estimation."""
        provider = AnthropicProvider(api_key="test-key")
        cost = await provider.estimate_cost("claude-sonnet-4-20250514", 1000, 500)
        assert cost > 0

    @pytest.mark.asyncio
    async def test_close_calls_shutdown(self) -> None:
        """Test that close delegates to shutdown."""
        provider = AnthropicProvider(api_key="test-key")
        await provider.initialize()
        await provider.close()
        assert provider._initialized is False

    @pytest.mark.asyncio
    async def test_health_with_mock_client_success(self) -> None:
        """Test health returns healthy when API responds."""
        provider = AnthropicProvider(api_key="test-key")
        await provider.initialize()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        provider._client.post = AsyncMock(return_value=mock_response)
        health = await provider.health()
        assert health["status"] == "healthy"
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_health_with_mock_client_auth_failure(self) -> None:
        """Test health returns unhealthy on 401."""
        provider = AnthropicProvider(api_key="test-key")
        await provider.initialize()
        mock_response = MagicMock()
        mock_response.status_code = 401
        provider._client.post = AsyncMock(return_value=mock_response)
        health = await provider.health()
        assert health["status"] == "unhealthy"
        assert "Invalid API key" in health["error"]
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_chat_with_mock_client(self) -> None:
        """Test chat returns response from Anthropic API."""
        provider = AnthropicProvider(api_key="test-key")
        await provider.initialize()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Hello!"}],
            "model": "claude-sonnet-4-20250514",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        provider._client.post = AsyncMock(return_value=mock_response)
        result = await provider.chat("claude-sonnet-4-20250514", [{"role": "user", "content": "Hello"}])
        assert result["message"]["content"] == "Hello!"
        assert result["usage"]["prompt_tokens"] == 10
        assert result["usage"]["completion_tokens"] == 5
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_chat_with_system_message(self) -> None:
        """Test chat extracts system message into separate param."""
        provider = AnthropicProvider(api_key="test-key")
        await provider.initialize()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-sonnet-4-20250514",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        provider._client.post = AsyncMock(return_value=mock_response)
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        result = await provider.chat("claude-sonnet-4-20250514", messages)
        # Verify the system message was extracted
        call_args = provider._client.post.call_args
        payload = call_args[1]["json"]
        assert payload["system"] == "You are helpful"
        assert all(m["role"] != "system" for m in payload["messages"])
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_chat_stream_with_mock_client(self) -> None:
        """Test chat_stream yields chunks from Anthropic API."""
        provider = AnthropicProvider(api_key="test-key")
        await provider.initialize()

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)
        mock_stream.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            lines = [
                'data: {"type":"content_block_delta","delta":{"text":"Hello"}}',
                'data: {"type":"content_block_delta","delta":{"text":" world"}}',
                'data: {"type":"message_stop"}',
            ]
            for line in lines:
                yield line

        mock_stream.aiter_lines = mock_aiter_lines
        provider._client.stream = MagicMock(return_value=mock_stream)

        chunks = []
        async for chunk in provider.chat_stream("claude-3-5-haiku-20241022", [{"role": "user", "content": "Hello"}]):
            chunks.append(chunk)

        assert len(chunks) > 0
        content_chunks = [c for c in chunks if c.get("message", {}).get("content")]
        assert len(content_chunks) >= 2
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_list_models_returns_defaults(self) -> None:
        """Test list_models returns hardcoded defaults."""
        provider = AnthropicProvider(api_key="test-key")
        await provider.initialize()
        models = await provider.list_models()
        assert models == list(DEFAULT_MODELS)
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_get_model_info(self) -> None:
        """Test get_model_info returns model data."""
        provider = AnthropicProvider(api_key="test-key")
        info = await provider.get_model_info("claude-sonnet-4-20250514")
        assert info["name"] == "claude-sonnet-4-20250514"
        assert info["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_estimate_cost_claude_haiku(self) -> None:
        """Test cost estimation for Claude Haiku is cheaper than Sonnet."""
        provider = AnthropicProvider(api_key="test-key")
        cost_haiku = await provider.estimate_cost("claude-3-5-haiku-20241022", 1000, 500)
        cost_sonnet = await provider.estimate_cost("claude-sonnet-4-20250514", 1000, 500)
        assert cost_haiku < cost_sonnet

    @pytest.mark.asyncio
    async def test_estimate_cost_claude_opus(self) -> None:
        """Test cost estimation for Claude Opus is most expensive."""
        provider = AnthropicProvider(api_key="test-key")
        cost_opus = await provider.estimate_cost("claude-3-opus-20240229", 1000, 500)
        cost_sonnet = await provider.estimate_cost("claude-sonnet-4-20250514", 1000, 500)
        assert cost_opus > cost_sonnet
