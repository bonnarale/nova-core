"""In-memory plugin repository."""

from __future__ import annotations

from typing import Any

from app.plugins.base import PluginRepository


class InMemoryPluginRepository(PluginRepository):
    """In-memory storage for plugin data."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def store(self, plugin_id: str, data: dict[str, Any]) -> None:
        self._store[plugin_id] = dict(data)

    async def get(self, plugin_id: str) -> dict[str, Any] | None:
        data = self._store.get(plugin_id)
        return dict(data) if data is not None else None

    async def list_all(self) -> list[dict[str, Any]]:
        return [dict(v) for v in self._store.values()]

    async def delete(self, plugin_id: str) -> bool:
        if plugin_id in self._store:
            del self._store[plugin_id]
            return True
        return False

    async def count(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, plugin_id: str) -> bool:
        return plugin_id in self._store
