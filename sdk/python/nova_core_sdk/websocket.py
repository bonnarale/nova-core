from __future__ import annotations

import asyncio
import json
from typing import Any, Callable


class WebSocketConnection:
    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self._url = url
        self._headers = headers or {}
        self._connected = False
        self._message_handler: Callable[..., Any] | None = None
        self._close_handler: Callable[..., Any] | None = None
        self._error_handler: Callable[..., Any] | None = None

    def on_message(self, handler: Callable[..., Any]) -> None:
        self._message_handler = handler

    def on_close(self, handler: Callable[..., Any]) -> None:
        self._close_handler = handler

    def on_error(self, handler: Callable[..., Any]) -> None:
        self._error_handler = handler

    async def connect(self) -> None:
        self._connected = True

    async def send(self, data: dict[str, Any]) -> None:
        if not self._connected:
            raise ConnectionError("WebSocket not connected")

    async def recv(self) -> dict[str, Any]:
        return {}

    async def close(self) -> None:
        self._connected = False
        if self._close_handler:
            self._close_handler()

    @property
    def connected(self) -> bool:
        return self._connected


class AsyncWebSocketClient:
    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self._url = url
        self._headers = headers or {}
        self._ws: WebSocketConnection | None = None
        self._running = False
        self._handlers: dict[str, list[Callable[..., Any]]] = {}

    def on(self, event: str, handler: Callable[..., Any]) -> None:
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    async def connect(self) -> None:
        self._ws = WebSocketConnection(self._url, self._headers)
        await self._ws.connect()
        self._running = True

    async def send(self, data: dict[str, Any]) -> None:
        if self._ws:
            await self._ws.send(data)

    async def listen(self) -> None:
        if not self._ws:
            raise ConnectionError("Not connected")
        self._running = True
        while self._running:
            try:
                message = await self._ws.recv()
                for handler in self._handlers.get("message", []):
                    handler(message)
            except Exception:
                if not self._running:
                    break
                for handler in self._handlers.get("error", []):
                    handler(Exception("WebSocket error"))

    async def disconnect(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
        for handler in self._handlers.get("close", []):
            handler()
