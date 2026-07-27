"""Connection pool implementation for the Database Architecture."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app.db.enums import PoolStatus
from app.db.models import ConnectionPoolStats

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Connection pool with health monitoring and statistics."""

    def __init__(
        self,
        pool_size: int = 5,
        max_overflow: int = 10,
        timeout: float = 30.0,
        recycle: float = 1800.0,
    ) -> None:
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._timeout = timeout
        self._recycle = recycle
        self._lock = threading.Lock()
        self._active = 0
        self._idle = pool_size
        self._overflow = 0
        self._total_created = 0
        self._total_checked_out = 0
        self._total_checked_in = 0
        self._status = PoolStatus.HEALTHY
        self._connections: list[dict[str, Any]] = []
        self._start_time = time.time()

    @property
    def pool_size(self) -> int:
        return self._pool_size

    @property
    def max_overflow(self) -> int:
        return self._max_overflow

    @property
    def status(self) -> PoolStatus:
        return self._status

    async def checkout(self) -> dict[str, Any]:
        with self._lock:
            if self._active >= self._pool_size + self._max_overflow:
                self._status = PoolStatus.EXHAUSTED
                raise ConnectionError("Connection pool exhausted")
            conn = {
                "id": f"conn-{self._total_created}",
                "created_at": time.time(),
                "checked_out_at": time.time(),
            }
            self._connections.append(conn)
            self._active += 1
            self._idle = max(0, self._pool_size - self._active)
            self._total_created += 1
            self._total_checked_out += 1
            self._status = PoolStatus.HEALTHY
            return conn

    async def checkin(self, connection: dict[str, Any]) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)
            self._idle = max(0, self._pool_size - self._active)
            self._total_checked_in += 1
            if connection in self._connections:
                self._connections.remove(connection)
            if self._active < self._pool_size:
                self._status = PoolStatus.HEALTHY

    async def dispose(self) -> None:
        with self._lock:
            self._connections.clear()
            self._active = 0
            self._idle = 0
            self._status = PoolStatus.CLOSED

    async def health_check(self) -> bool:
        return self._status != PoolStatus.CLOSED

    def get_stats(self) -> ConnectionPoolStats:
        return ConnectionPoolStats(
            pool_size=self._pool_size,
            active_connections=self._active,
            idle_connections=self._idle,
            overflow=self._overflow,
            max_overflow=self._max_overflow,
            status=self._status.value,
            total_checked_out=self._total_checked_out,
            total_checked_in=self._total_checked_in,
            total_connections_created=self._total_created,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.get_stats().to_dict()
