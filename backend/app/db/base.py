"""Abstract base classes for the Database Architecture subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar

T = TypeVar("T")


class RepositoryProvider(ABC):
    """Provider interface for data repositories."""

    @abstractmethod
    async def get(self, entity_id: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    async def list(
        self,
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    async def update(self, entity_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        ...

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        ...

    @abstractmethod
    async def count(self, filters: dict[str, Any] | None = None) -> int:
        ...


class UnitOfWork(ABC):
    """Interface for Unit of Work pattern."""

    @abstractmethod
    async def begin(self) -> None:
        ...

    @abstractmethod
    async def commit(self) -> None:
        ...

    @abstractmethod
    async def rollback(self) -> None:
        ...

    @abstractmethod
    async def flush(self) -> None:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...

    @abstractmethod
    def is_active(self) -> bool:
        ...


class TransactionManager(ABC):
    """Interface for transaction management."""

    @abstractmethod
    async def begin(self) -> None:
        ...

    @abstractmethod
    async def commit(self) -> None:
        ...

    @abstractmethod
    async def rollback(self) -> None:
        ...

    @abstractmethod
    async def savepoint(self) -> str:
        ...

    @abstractmethod
    async def release_savepoint(self, savepoint_id: str) -> None:
        ...

    @abstractmethod
    async def rollback_to_savepoint(self, savepoint_id: str) -> None:
        ...


class SessionProvider(ABC):
    """Interface for session management."""

    @abstractmethod
    async def get_session(self) -> Any:
        ...

    @abstractmethod
    async def close_session(self, session: Any) -> None:
        ...

    @abstractmethod
    async def dispose(self) -> None:
        ...


class MigrationProvider(ABC):
    """Interface for migration management."""

    @abstractmethod
    async def get_current_revision(self) -> str:
        ...

    @abstractmethod
    async def get_head_revision(self) -> str:
        ...

    @abstractmethod
    async def get_pending_migrations(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def get_migration_status(self) -> dict[str, Any]:
        ...

    @abstractmethod
    async def validate_migrations(self) -> bool:
        ...


class DatabaseHealthProvider(ABC):
    """Interface for database health checks."""

    @abstractmethod
    async def check_connectivity(self) -> bool:
        ...

    @abstractmethod
    async def get_latency_ms(self) -> float:
        ...

    @abstractmethod
    async def get_pool_status(self) -> dict[str, Any]:
        ...

    @abstractmethod
    async def get_health(self) -> dict[str, Any]:
        ...
