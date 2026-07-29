"""Load balancer with multiple strategies."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app.scaling.base import LoadBalancerProvider
from app.scaling.enums import LoadBalanceStrategy

logger = logging.getLogger(__name__)


class _Backend:
    __slots__ = ("id", "weight", "healthy", "connections", "last_check")

    def __init__(self, backend_id: str, weight: int = 1) -> None:
        self.id = backend_id
        self.weight = weight
        self.healthy = True
        self.connections = 0
        self.last_check = time.time()


class LoadBalancer(LoadBalancerProvider):
    """Load balancer supporting round robin, least connections, weighted, and health-aware strategies."""

    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN) -> None:
        self._strategy = strategy
        self._lock = threading.Lock()
        self._backends: dict[str, _Backend] = {}
        self._index = 0
        self._total_requests = 0

    @property
    def strategy(self) -> LoadBalanceStrategy:
        return self._strategy

    async def add_backend(self, backend_id: str, weight: int = 1) -> None:
        with self._lock:
            self._backends[backend_id] = _Backend(backend_id, weight)
            logger.debug("Backend added: %s (weight=%d)", backend_id, weight)

    async def remove_backend(self, backend_id: str) -> bool:
        with self._lock:
            if backend_id in self._backends:
                del self._backends[backend_id]
                return True
            return False

    async def next_backend(self) -> str | None:
        with self._lock:
            healthy = [b for b in self._backends.values() if b.healthy]
            if not healthy:
                return None
            self._total_requests += 1

            if self._strategy == LoadBalanceStrategy.ROUND_ROBIN:
                backend = self._select_round_robin(healthy)
            elif self._strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
                backend = self._select_least_connections(healthy)
            elif self._strategy == LoadBalanceStrategy.WEIGHTED:
                backend = self._select_weighted(healthy)
            elif self._strategy == LoadBalanceStrategy.HEALTH_AWARE:
                backend = self._select_health_aware(healthy)
            else:
                backend = healthy[0]

            backend.connections += 1
            backend.last_check = time.time()
            return backend.id

    async def report_health(self, backend_id: str, healthy: bool) -> None:
        with self._lock:
            if backend_id in self._backends:
                self._backends[backend_id].healthy = healthy
                self._backends[backend_id].last_check = time.time()

    async def release_connection(self, backend_id: str) -> None:
        with self._lock:
            if backend_id in self._backends:
                b = self._backends[backend_id]
                if b.connections > 0:
                    b.connections -= 1

    async def get_backends(self) -> dict[str, Any]:
        with self._lock:
            return {
                "strategy": self._strategy.value,
                "total": len(self._backends),
                "healthy": sum(1 for b in self._backends.values() if b.healthy),
                "backends": {
                    bid: {
                        "weight": b.weight,
                        "healthy": b.healthy,
                        "connections": b.connections,
                    }
                    for bid, b in self._backends.items()
                },
                "total_requests": self._total_requests,
            }

    def _select_round_robin(self, backends: list[_Backend]) -> _Backend:
        backend = backends[self._index % len(backends)]
        self._index += 1
        return backend

    def _select_least_connections(self, backends: list[_Backend]) -> _Backend:
        return min(backends, key=lambda b: b.connections)

    def _select_weighted(self, backends: list[_Backend]) -> _Backend:
        total_weight = sum(b.weight for b in backends)
        if total_weight == 0:
            return backends[0]
        import random
        r = random.randint(0, total_weight - 1)
        cumulative = 0
        for b in backends:
            cumulative += b.weight
            if r < cumulative:
                return b
        return backends[-1]

    def _select_health_aware(self, backends: list[_Backend]) -> _Backend:
        scored = sorted(backends, key=lambda b: (b.connections / max(b.weight, 1)))
        return scored[0]
