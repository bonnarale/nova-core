"""Database health checks for the Database Architecture."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.db.base import DatabaseHealthProvider
from app.db.connection_pool import ConnectionPool
from app.db.enums import MigrationStatus, PoolStatus
from app.db.migrations import InMemoryMigrationProvider
from app.db.models import DatabaseHealth

logger = logging.getLogger(__name__)


class DatabaseHealthChecker(DatabaseHealthProvider):
    """Database health checker with connectivity, latency, and pool monitoring."""

    def __init__(
        self,
        pool: ConnectionPool | None = None,
        migration_provider: InMemoryMigrationProvider | None = None,
    ) -> None:
        self._pool = pool or ConnectionPool()
        self._migration_provider = migration_provider or InMemoryMigrationProvider()
        self._last_latency = 0.0

    async def check_connectivity(self) -> bool:
        try:
            start = time.time()
            healthy = await self._pool.health_check()
            self._last_latency = (time.time() - start) * 1000
            return healthy
        except Exception:
            return False

    async def get_latency_ms(self) -> float:
        return self._last_latency

    async def get_pool_status(self) -> dict[str, Any]:
        return self._pool.to_dict()

    async def get_health(self) -> dict[str, Any]:
        connected = await self.check_connectivity()
        pool_stats = self._pool.get_stats()
        migration_status = await self._migration_provider.get_migration_status()
        health = DatabaseHealth(
            connected=connected,
            latency_ms=self._last_latency,
            pool_status=self._pool.status.value,
            active_connections=pool_stats.active_connections,
            idle_connections=pool_stats.idle_connections,
            pool_size=pool_stats.pool_size,
            migration_status=migration_status.get("status", MigrationStatus.UNKNOWN.value),
            current_revision=migration_status.get("current_revision", ""),
            head_revision=migration_status.get("head_revision", ""),
            last_check=time.time(),
        )
        return health.to_dict()
