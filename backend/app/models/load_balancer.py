"""Load balancing across model providers."""

import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    WEIGHTED = "weighted"
    LEAST_CONNECTIONS = "least_connections"
    LATENCY_BASED = "latency_based"


@dataclass
class ProviderStats:
    """Statistics for a provider."""

    provider_id: str
    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    weight: float = 1.0
    last_request_time: float = 0.0

    @property
    def average_latency(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    def record_request(self, latency_ms: float, success: bool = True) -> None:
        self.total_requests += 1
        self.total_latency_ms += latency_ms
        self.last_request_time = time.time()
        if not success:
            self.failed_requests += 1

    def connection_started(self) -> None:
        self.active_connections += 1

    def connection_ended(self) -> None:
        self.active_connections = max(0, self.active_connections - 1)


class LoadBalancer:
    """Load balancer for distributing requests across providers."""

    def __init__(
        self,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        health_check_enabled: bool = True,
    ) -> None:
        self._strategy = strategy
        self._health_check_enabled = health_check_enabled
        self._stats: dict[str, ProviderStats] = {}
        self._round_robin_index = 0
        self._weights: dict[str, float] = {}

    @property
    def strategy(self) -> LoadBalancingStrategy:
        return self._strategy

    def register_provider(self, provider_id: str, weight: float = 1.0) -> None:
        self._stats[provider_id] = ProviderStats(provider_id=provider_id, weight=weight)
        self._weights[provider_id] = weight
        logger.info("Provider registered with load balancer: %s (weight=%.2f)", provider_id, weight)

    def unregister_provider(self, provider_id: str) -> None:
        self._stats.pop(provider_id, None)
        self._weights.pop(provider_id, None)

    def select_provider(
        self,
        available_providers: list[str],
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        if not available_providers:
            raise ValueError("No providers available")

        if self._strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin(available_providers)
        if self._strategy == LoadBalancingStrategy.RANDOM:
            return self._random(available_providers)
        if self._strategy == LoadBalancingStrategy.WEIGHTED:
            return self._weighted(available_providers)
        if self._strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections(available_providers)
        if self._strategy == LoadBalancingStrategy.LATENCY_BASED:
            return self._latency_based(available_providers)
        return available_providers[0]

    def _round_robin(self, providers: list[str]) -> str:
        provider = providers[self._round_robin_index % len(providers)]
        self._round_robin_index += 1
        return provider

    def _random(self, providers: list[str]) -> str:
        return random.choice(providers)

    def _weighted(self, providers: list[str]) -> str:
        total_weight = sum(self._weights.get(p, 1.0) for p in providers)
        r = random.random() * total_weight
        cumulative = 0.0
        for p in providers:
            cumulative += self._weights.get(p, 1.0)
            if r <= cumulative:
                return p
        return providers[-1]

    def _least_connections(self, providers: list[str]) -> str:
        return min(providers, key=lambda p: self._stats.get(p, ProviderStats(p)).active_connections)

    def _latency_based(self, providers: list[str]) -> str:
        def get_latency(p: str) -> float:
            stats = self._stats.get(p)
            if not stats or stats.total_requests == 0:
                return float("inf")
            return stats.average_latency
        return min(providers, key=get_latency)

    def record_request(self, provider_id: str, latency_ms: float, success: bool = True) -> None:
        if provider_id not in self._stats:
            self._stats[provider_id] = ProviderStats(provider_id=provider_id)
        self._stats[provider_id].record_request(latency_ms, success)

    def connection_started(self, provider_id: str) -> None:
        if provider_id in self._stats:
            self._stats[provider_id].connection_started()

    def connection_ended(self, provider_id: str) -> None:
        if provider_id in self._stats:
            self._stats[provider_id].connection_ended()

    def get_provider_stats(self, provider_id: str) -> Optional[ProviderStats]:
        return self._stats.get(provider_id)

    def get_all_stats(self) -> dict[str, ProviderStats]:
        return dict(self._stats)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self._strategy.value,
            "providers": {
                pid: {
                    "active_connections": stats.active_connections,
                    "total_requests": stats.total_requests,
                    "average_latency": stats.average_latency,
                    "failure_rate": stats.failure_rate,
                    "weight": stats.weight,
                }
                for pid, stats in self._stats.items()
            },
        }


def get_load_balancer(
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
) -> LoadBalancer:
    return LoadBalancer(strategy=strategy)
