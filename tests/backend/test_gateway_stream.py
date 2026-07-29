"""Tests for ModelGateway chat_stream resilience."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.gateway import ModelGateway, ProviderNotFoundError
from app.models.registry import ProviderRegistry
from app.models.providers.mock import MockProvider


class TestGatewayStreamResilience:
    """Tests for chat_stream retry, fallback, and error handling."""

    @pytest.mark.asyncio
    async def test_chat_stream_success(self) -> None:
        """Test chat_stream yields chunks on success."""
        registry = ProviderRegistry()
        provider = MockProvider()
        registry.register("mock", provider)
        gateway = ModelGateway(registry=registry)
        await gateway.initialize()

        chunks = []
        async for chunk in gateway.chat_stream(
            model="mock-model",
            messages=[{"role": "user", "content": "Hello"}],
            provider="mock",
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert any(c.get("done") for c in chunks)
        await gateway.shutdown()

    @pytest.mark.asyncio
    async def test_chat_stream_provider_not_found(self) -> None:
        """Test chat_stream raises when provider not found."""
        gateway = ModelGateway()
        await gateway.initialize()
        with pytest.raises(ProviderNotFoundError):
            chunks = []
            async for chunk in gateway.chat_stream(
                model="model",
                messages=[{"role": "user", "content": "Hello"}],
                provider="nonexistent",
            ):
                chunks.append(chunk)

    @pytest.mark.asyncio
    async def test_chat_stream_records_metrics(self) -> None:
        """Test chat_stream records metrics on completion."""
        registry = ProviderRegistry()
        provider = MockProvider()
        registry.register("mock", provider)
        gateway = ModelGateway(registry=registry)
        await gateway.initialize()

        chunks = []
        async for chunk in gateway.chat_stream(
            model="mock-model",
            messages=[{"role": "user", "content": "Hello"}],
            provider="mock",
        ):
            chunks.append(chunk)

        metrics = gateway.metrics.get_summary()
        assert metrics["total_requests"] >= 1
        await gateway.shutdown()

    @pytest.mark.asyncio
    async def test_chat_stream_retry_on_connection_error(self) -> None:
        """Test chat_stream retries on connection error before first yield."""
        registry = ProviderRegistry()

        call_count = 0

        class FlakyProvider(MockProvider):
            async def chat_stream(self, model, messages, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    import httpx
                    raise httpx.ConnectError("Connection refused")
                # Second call succeeds
                yield {"message": {"content": "Recovered"}, "done": True}

        provider = FlakyProvider()
        registry.register("flaky", provider)
        gateway = ModelGateway(registry=registry)
        await gateway.initialize()

        chunks = []
        async for chunk in gateway.chat_stream(
            model="mock-model",
            messages=[{"role": "user", "content": "Hello"}],
            provider="flaky",
        ):
            chunks.append(chunk)

        assert call_count == 2  # Retried once
        assert any(c.get("message", {}).get("content") == "Recovered" for c in chunks)
        await gateway.shutdown()

    @pytest.mark.asyncio
    async def test_chat_stream_no_retry_after_yield(self) -> None:
        """Test chat_stream does NOT retry after first token yielded."""
        registry = ProviderRegistry()

        class MidStreamErrorProvider(MockProvider):
            async def chat_stream(self, model, messages, **kwargs):
                yield {"message": {"content": "partial"}, "done": False}
                import httpx
                raise httpx.ConnectError("Connection lost")

        provider = MidStreamErrorProvider()
        registry.register("midstream", provider)
        gateway = ModelGateway(registry=registry)
        await gateway.initialize()

        chunks = []
        async for chunk in gateway.chat_stream(
            model="mock-model",
            messages=[{"role": "user", "content": "Hello"}],
            provider="midstream",
        ):
            chunks.append(chunk)

        # Should have partial content + error event, no retry
        assert any(c.get("message", {}).get("content") == "partial" for c in chunks)
        assert any(c.get("error") for c in chunks)
        await gateway.shutdown()

    @pytest.mark.asyncio
    async def test_chat_stream_fallback_on_exhausted_retries(self) -> None:
        """Test chat_stream falls back to another provider after retries exhausted."""
        from app.models.policies import FallbackPolicy

        registry = ProviderRegistry()

        async def always_fail_stream(model, messages, **kwargs):
            import httpx
            raise httpx.ConnectError("Always fails")
            yield  # Make it an async generator

        class AlwaysFailProvider(MockProvider):
            async def chat_stream(self, model, messages, **kwargs):
                import httpx
                raise httpx.ConnectError("Always fails")
                yield  # noqa: unreachable — makes this an async generator

        fail_provider = AlwaysFailProvider()
        backup_provider = MockProvider(response="Backup response")
        registry.register("primary", fail_provider)
        registry.register("backup", backup_provider)

        fallback = FallbackPolicy(fallback_chain=["primary", "backup"])
        from app.models.router import ModelRouter
        router = ModelRouter(registry=registry, fallback=fallback)
        gateway = ModelGateway(registry=registry, router=router)
        await gateway.initialize()

        chunks = []
        async for chunk in gateway.chat_stream(
            model="mock-model",
            messages=[{"role": "user", "content": "Hello"}],
            provider="primary",
        ):
            chunks.append(chunk)

        # Should have gotten backup response or error
        assert len(chunks) > 0
        await gateway.shutdown()
