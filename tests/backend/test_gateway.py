import pytest
from unittest.mock import AsyncMock, patch

from app.core.config import Settings
from app.models.gateway import ModelGateway
from app.models.providers.ollama import OllamaProvider


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    def test_init_creates_client_with_settings_url(self) -> None:
        """Test that OllamaProvider initializes with correct base URL."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        provider = OllamaProvider(settings)
        
        assert provider._base_url == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_chat_sends_correct_request(self) -> None:
        """Test that chat method sends correct request to Ollama API."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        provider = OllamaProvider(settings)
        
        mock_response = AsyncMock()
        mock_response.json.return_value = {"message": {"content": "test response"}}
        mock_response.raise_for_status = AsyncMock()
        
        with patch.object(provider._client, "post", return_value=mock_response):
            result = await provider.chat(
                model="llama3",
                messages=[{"role": "user", "content": "Hello"}],
            )
        
        assert result == {"message": {"content": "test response"}}

    @pytest.mark.asyncio
    async def test_list_models_returns_model_names(self) -> None:
        """Test that list_models returns list of model names."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        provider = OllamaProvider(settings)
        
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3"},
                {"name": "phi3"},
            ]
        }
        mock_response.raise_for_status = AsyncMock()
        
        with patch.object(provider._client, "get", return_value=mock_response):
            result = await provider.list_models()
        
        assert result == ["llama3", "phi3"]

    @pytest.mark.asyncio
    async def test_close_closes_client(self) -> None:
        """Test that close method closes the HTTP client."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        provider = OllamaProvider(settings)
        
        with patch.object(provider._client, "aclose", new_callable=AsyncMock) as mock_close:
            await provider.close()
        
        mock_close.assert_called_once()


class TestModelGateway:
    """Tests for ModelGateway."""

    def test_init_with_settings(self) -> None:
        """Test that ModelGateway initializes with settings."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        gateway = ModelGateway(settings)
        
        assert gateway._settings == settings

    def test_init_without_settings(self) -> None:
        """Test that ModelGateway initializes without settings."""
        gateway = ModelGateway()
        
        assert gateway._settings is None

    def test_get_provider_creates_ollama_provider(self) -> None:
        """Test that _get_provider creates OllamaProvider for ollama."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        gateway = ModelGateway(settings)
        
        provider = gateway._get_provider("ollama")
        
        assert isinstance(provider, OllamaProvider)

    def test_get_provider_raises_for_unsupported(self) -> None:
        """Test that _get_provider raises ValueError for unsupported provider."""
        gateway = ModelGateway()
        
        with pytest.raises(ValueError, match="Unsupported provider"):
            gateway._get_provider("unsupported")

    @pytest.mark.asyncio
    async def test_chat_delegates_to_provider(self) -> None:
        """Test that chat method delegates to provider."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        gateway = ModelGateway(settings)
        
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = {"response": "test"}
        gateway._providers["ollama"] = mock_provider
        
        result = await gateway.chat(
            model="llama3",
            messages=[{"role": "user", "content": "Hello"}],
        )
        
        mock_provider.chat.assert_called_once_with(
            "llama3",
            [{"role": "user", "content": "Hello"}],
        )
        assert result == {"response": "test"}

    @pytest.mark.asyncio
    async def test_list_models_delegates_to_provider(self) -> None:
        """Test that list_models method delegates to provider."""
        settings = Settings(OLLAMA_HOST="localhost", OLLAMA_PORT=11434)
        gateway = ModelGateway(settings)
        
        mock_provider = AsyncMock()
        mock_provider.list_models.return_value = ["llama3", "phi3"]
        gateway._providers["ollama"] = mock_provider
        
        result = await gateway.list_models()
        
        mock_provider.list_models.assert_called_once()
        assert result == ["llama3", "phi3"]

    @pytest.mark.asyncio
    async def test_close_closes_all_providers(self) -> None:
        """Test that close method closes all providers."""
        gateway = ModelGateway()
        
        mock_provider1 = AsyncMock()
        mock_provider2 = AsyncMock()
        gateway._providers = {"ollama": mock_provider1, "other": mock_provider2}
        
        await gateway.close()
        
        mock_provider1.close.assert_called_once()
        mock_provider2.close.assert_called_once()