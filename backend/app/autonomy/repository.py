"""Repository abstraction for autonomy persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AutonomyRepository(ABC):
    """Abstract repository for autonomy data persistence."""

    @abstractmethod
    async def save(self, collection: str, entity_id: str, data: dict[str, Any]) -> None:
        ...

    @abstractmethod
    async def get(self, collection: str, entity_id: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    async def list(self, collection: str, limit: int = 100) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def delete(self, collection: str, entity_id: str) -> bool:
        ...

    @abstractmethod
    async def count(self, collection: str) -> int:
        ...
