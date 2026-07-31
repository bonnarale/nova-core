"""Read replica and failover abstractions."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


class Replica:
    """Represents a read replica."""

    __slots__ = ("replica_id", "host", "port", "healthy", "lag_ms", "last_check", "weight")

    def __init__(self, replica_id: str, host: str = "localhost", port: int = 5432, weight: int = 1) -> None:
        self.replica_id = replica_id
        self.host = host
        self.port = port
        self.healthy = True
        self.lag_ms = 0.0
        self.last_check = time.time()
        self.weight = weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "replica_id": self.replica_id,
            "host": self.host,
            "port": self.port,
            "healthy": self.healthy,
            "lag_ms": self.lag_ms,
            "weight": self.weight,
        }


class ReplicationManager:
    """Manages read replicas with failover and synchronization tracking."""

    def __init__(self, primary_id: str = "primary") -> None:
        self._lock = threading.Lock()
        self._primary_id = primary_id
        self._replicas: dict[str, Replica] = {}
        self._failover_count = 0
        self._sync_events: list[dict[str, Any]] = []

    @property
    def primary_id(self) -> str:
        return self._primary_id

    def add_replica(self, replica_id: str, host: str = "localhost", port: int = 5432, weight: int = 1) -> None:
        with self._lock:
            self._replicas[replica_id] = Replica(replica_id, host, port, weight)

    def remove_replica(self, replica_id: str) -> bool:
        with self._lock:
            if replica_id in self._replicas:
                del self._replicas[replica_id]
                return True
            return False

    def report_health(self, replica_id: str, healthy: bool, lag_ms: float = 0.0) -> None:
        with self._lock:
            if replica_id in self._replicas:
                r = self._replicas[replica_id]
                was_healthy = r.healthy
                r.healthy = healthy
                r.lag_ms = lag_ms
                r.last_check = time.time()
                if was_healthy and not healthy:
                    self._failover_count += 1
                    logger.warning("Replica %s became unhealthy", replica_id)

    def get_healthy_replicas(self) -> list[Replica]:
        with self._lock:
            return [r for r in self._replicas.values() if r.healthy]

    def select_replica(self) -> Replica | None:
        healthy = self.get_healthy_replicas()
        if not healthy:
            return None
        return min(healthy, key=lambda r: r.lag_ms)

    def record_sync(self, replica_id: str, success: bool, duration_ms: float = 0.0) -> None:
        self._sync_events.append({
            "replica_id": replica_id,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
        })
        if len(self._sync_events) > 1000:
            self._sync_events = self._sync_events[-500:]

    def get_statistics(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._replicas)
            healthy = sum(1 for r in self._replicas.values() if r.healthy)
            return {
                "primary": self._primary_id,
                "total_replicas": total,
                "healthy_replicas": healthy,
                "failover_count": self._failover_count,
                "sync_events": len(self._sync_events),
                "replicas": {rid: r.to_dict() for rid, r in self._replicas.items()},
            }
