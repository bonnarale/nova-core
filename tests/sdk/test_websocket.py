from __future__ import annotations

import pytest
from nova_core_sdk.websocket import WebSocketConnection, AsyncWebSocketClient


class TestWebSocketConnection:
    @pytest.mark.asyncio
    async def test_connect_disconnect(self) -> None:
        ws = WebSocketConnection("ws://localhost:8000/ws")
        assert ws.connected is False
        await ws.connect()
        assert ws.connected is True
        await ws.close()
        assert ws.connected is False

    @pytest.mark.asyncio
    async def test_send_when_not_connected(self) -> None:
        ws = WebSocketConnection("ws://localhost:8000/ws")
        with pytest.raises(ConnectionError):
            await ws.send({"type": "test"})

    def test_event_handlers(self) -> None:
        ws = WebSocketConnection("ws://localhost:8000/ws")
        called = []
        ws.on_message(lambda msg: called.append(msg))
        ws.on_close(lambda: called.append("closed"))
        ws.on_error(lambda err: called.append("error"))
        assert len(called) == 0


class TestAsyncWebSocketClient:
    def test_init(self) -> None:
        client = AsyncWebSocketClient("ws://localhost:8000/ws")
        assert client._running is False
        assert client._ws is None

    def test_register_handler(self) -> None:
        client = AsyncWebSocketClient("ws://localhost:8000/ws")
        handler = lambda msg: None
        client.on("message", handler)
        assert handler in client._handlers["message"]
