"""Vector repository implementations — adapters between storage and the rest of the system."""

from __future__ import annotations

from typing import Any, Optional

from app.vector_memory.base import VectorRepository
from app.vector_memory.schemas import MemoryCategory, VectorRecord


class InMemoryVectorRepository(VectorRepository):
    """In-memory vector repository backed by InMemoryVectorStorage."""

    def __init__(self) -> None:
        from app.vector_memory.storage import InMemoryVectorStorage
        self._storage = InMemoryVectorStorage()

    @property
    def storage(self) -> Any:
        return self._storage

    async def add(self, records: list[VectorRecord]) -> int:
        return await self._storage.add(records)

    async def update(self, records: list[VectorRecord]) -> int:
        return await self._storage.update(records)

    async def delete(self, vector_ids: list[str]) -> int:
        return await self._storage.delete(vector_ids)

    async def get(self, vector_id: str) -> Optional[VectorRecord]:
        return await self._storage.get(vector_id)

    async def list_by_user(
        self,
        user_id: str,
        memory_category: Optional[MemoryCategory] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        return await self._storage.list_by_user(user_id, memory_category, limit, offset)

    async def list_by_session(
        self,
        session_id: str,
        memory_category: Optional[MemoryCategory] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        return await self._storage.list_by_session(session_id, memory_category, limit, offset)

    async def list_by_category(
        self,
        memory_category: MemoryCategory,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        return await self._storage.list_by_category(memory_category, limit, offset)

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[VectorRecord]:
        return await self._storage.list_all(limit, offset)

    async def count(self) -> int:
        return await self._storage.count()

    async def count_by_category(self) -> dict[str, int]:
        return await self._storage.count_by_category()

    async def get_all_ids(self) -> list[str]:
        return await self._storage.get_all_ids()

    async def search_by_tags(self, tags: list[str], limit: int = 50) -> list[VectorRecord]:
        return await self._storage.search_by_tags(tags, limit)

    async def health(self) -> dict[str, Any]:
        return await self._storage.health()


class ChromaVectorRepository(VectorRepository):
    """ChromaDB-backed vector repository."""

    def __init__(self, chroma_client: Any = None) -> None:
        from app.vector_memory.storage import ChromaVectorStorage
        self._storage = ChromaVectorStorage(chroma_client=chroma_client)

    @property
    def storage(self) -> Any:
        return self._storage

    async def add(self, records: list[VectorRecord]) -> int:
        return await self._storage.add(records)

    async def update(self, records: list[VectorRecord]) -> int:
        return await self._storage.update(records)

    async def delete(self, vector_ids: list[str]) -> int:
        return await self._storage.delete(vector_ids)

    async def get(self, vector_id: str) -> Optional[VectorRecord]:
        return await self._storage.get(vector_id)

    async def list_by_user(
        self,
        user_id: str,
        memory_category: Optional[MemoryCategory] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        return await self._storage.list_by_user(user_id, memory_category, limit, offset)

    async def list_by_session(
        self,
        session_id: str,
        memory_category: Optional[MemoryCategory] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        return await self._storage.list_by_session(session_id, memory_category, limit, offset)

    async def list_by_category(
        self,
        memory_category: MemoryCategory,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        return await self._storage.list_by_category(memory_category, limit, offset)

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[VectorRecord]:
        return await self._storage.list_all(limit, offset)

    async def count(self) -> int:
        return await self._storage.count()

    async def count_by_category(self) -> dict[str, int]:
        return await self._storage.count_by_category()

    async def get_all_ids(self) -> list[str]:
        return await self._storage.get_all_ids()

    async def search_by_tags(self, tags: list[str], limit: int = 50) -> list[VectorRecord]:
        return await self._storage.search_by_tags(tags, limit)

    async def health(self) -> dict[str, Any]:
        return await self._storage.health()


# Legacy alias
InMemoryRepository = InMemoryVectorRepository
