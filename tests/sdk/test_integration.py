from __future__ import annotations

import pytest
from nova_core_sdk.factory import create_client, create_async_client
from nova_core_sdk.configuration import Configuration
from nova_core_sdk.async_client import AsyncNovaClient


class TestFactory:
    def test_create_client_default(self) -> None:
        client = create_client()
        assert client is not None
        assert client._config.base_url == "http://localhost:8000"

    def test_create_client_custom_url(self) -> None:
        client = create_client(base_url="http://example.com:9000")
        assert client._config.base_url == "http://example.com:9000"

    def test_create_client_with_api_key(self) -> None:
        client = create_client(api_key="my-key")
        assert client._config.api_key == "my-key"

    def test_create_client_with_token(self) -> None:
        client = create_client(bearer_token="tok")
        assert client._config.bearer_token == "tok"

    def test_create_async_client(self) -> None:
        client = create_async_client()
        assert isinstance(client, AsyncNovaClient)
