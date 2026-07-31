"""In-memory persistence for enterprise data."""

from __future__ import annotations

import threading
from typing import Any

from app.enterprise.repository import EnterpriseRepository


class InMemoryEnterpriseRepository(EnterpriseRepository):
    """Thread-safe in-memory repository."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, dict[str, Any]]] = {}
        self._lock = threading.RLock()

    async def save(self, collection: str, entity_id: str, data: dict[str, Any]) -> None:
        with self._lock:
            self._store.setdefault(collection, {})[entity_id] = dict(data)

    async def get(self, collection: str, entity_id: str) -> dict[str, Any] | None:
        with self._lock:
            entity = self._store.get(collection, {}).get(entity_id)
            return dict(entity) if entity else None

    async def list(self, collection: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            entities = list(self._store.get(collection, {}).values())
            return [dict(e) for e in entities[:limit]]

    async def delete(self, collection: str, entity_id: str) -> bool:
        with self._lock:
            coll = self._store.get(collection, {})
            if entity_id in coll:
                del coll[entity_id]
                return True
            return False

    async def count(self, collection: str) -> int:
        with self._lock:
            return len(self._store.get(collection, {}))

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
