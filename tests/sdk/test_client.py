from __future__ import annotations

import pytest
from nova_core_sdk.client import NovaClient
from nova_core_sdk.configuration import Configuration


class TestNovaClient:
    def test_init_default(self) -> None:
        client = NovaClient()
        assert client._config.base_url == "http://localhost:8000"

    def test_init_with_config(self) -> None:
        config = Configuration(base_url="http://example.com:9000", api_key="k")
        client = NovaClient(config)
        assert client._config.base_url == "http://example.com:9000"

    def test_services_exist(self) -> None:
        client = NovaClient()
        assert client.agents is not None
        assert client.models is not None
        assert client.memory is not None
        assert client.kernel is not None
        assert client.goals is not None
        assert client.tasks is not None
        assert client.workflows is not None
        assert client.scheduler is not None
        assert client.tools is not None
        assert client.rag is not None
        assert client.vector_memory is not None
        assert client.events is not None
        assert client.plugins is not None
        assert client.learning is not None
        assert client.knowledge_graph is not None
        assert client.observability is not None
        assert client.deployment is not None
        assert client.scaling is not None
        assert client.security is not None
        assert client.enterprise is not None
        assert client.profile is not None
        assert client.database is not None
        assert client.performance is not None
        assert client.resilience is not None
        assert client.autonomy is not None

    def test_websocket_creates_connection(self) -> None:
        client = NovaClient(Configuration(base_url="http://localhost:8000"))
        ws = client.websocket("/ws/events")
        assert ws is not None
        assert ws._running is False

    def test_middleware_accessible(self) -> None:
        client = NovaClient()
        assert client._middleware is not None

    def test_hooks_accessible(self) -> None:
        client = NovaClient()
        assert client._hooks is not None
