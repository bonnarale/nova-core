"""In-memory security repository."""

from __future__ import annotations

from typing import Any


class InMemorySecurityRepository:
    """In-memory storage for security data."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def store(self, key: str, data: dict[str, Any]) -> None:
        self._store[key] = dict(data)

    async def get(self, key: str) -> dict[str, Any] | None:
        data = self._store.get(key)
        return dict(data) if data is not None else None

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def list_all(self) -> list[dict[str, Any]]:
        return [dict(v) for v in self._store.values()]

    async def count(self) -> int:
        return len(self._store)

    async def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return key in self._store
