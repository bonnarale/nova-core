from __future__ import annotations

import pytest


class TestSDKImports:
    def test_import_main_package(self) -> None:
        from nova_core_sdk import NovaClient, Configuration
        assert NovaClient is not None
        assert Configuration is not None

    def test_import_exceptions(self) -> None:
        from nova_core_sdk.exceptions import (
            NovaError,
            NovaAPIError,
            NovaAuthError,
            NovaRateLimitError,
            NovaServerError,
            NovaConnectionError,
            NovaTimeoutError,
            NovaValidationError,
        )
        assert NovaError is not None

    def test_import_models(self) -> None:
        from nova_core_sdk.models import ChatRequestModel, CreateAgentRequest
        assert ChatRequestModel is not None

    def test_import_responses(self) -> None:
        from nova_core_sdk.responses import APIResponse, PaginatedResponse
        assert APIResponse is not None

    def test_import_pagination(self) -> None:
        from nova_core_sdk.pagination import PageIterator, AsyncPageIterator
        assert PageIterator is not None

    def test_import_retry(self) -> None:
        from nova_core_sdk.retry import RetryHandler
        assert RetryHandler is not None

    def test_import_middleware(self) -> None:
        from nova_core_sdk.middleware import Middleware, TelemetryMiddleware
        assert Middleware is not None

    def test_import_hooks(self) -> None:
        from nova_core_sdk.hooks import HookManager
        assert HookManager is not None

    def test_import_telemetry(self) -> None:
        from nova_core_sdk.telemetry import TelemetryCollector
        assert TelemetryCollector is not None

    def test_import_streaming(self) -> None:
        from nova_core_sdk.streaming import StreamProcessor, AsyncStreamProcessor
        assert StreamProcessor is not None

    def test_import_websocket(self) -> None:
        from nova_core_sdk.websocket import WebSocketConnection, AsyncWebSocketClient
        assert WebSocketConnection is not None

    def test_import_auth(self) -> None:
        from nova_core_sdk.auth import AuthProvider, APIKeyAuth, BearerTokenAuth, create_auth
        assert AuthProvider is not None

    def test_import_factory(self) -> None:
        from nova_core_sdk.factory import create_client, create_async_client
        assert create_client is not None

    def test_import_async_client(self) -> None:
        from nova_core_sdk.async_client import AsyncNovaClient
        assert AsyncNovaClient is not None
