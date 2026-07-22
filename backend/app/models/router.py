"""Routing logic for model requests."""

import logging
import time
from typing import Any, Optional

from app.models.capabilities import ProviderCapabilities
from app.models.context import ModelContext, RequestStatus
from app.models.lifecycle import ProviderState
from app.models.policies import (
    CircuitBreakerPolicy,
    FallbackPolicy,
    LoadBalancerPolicy,
    RateLimitPolicy,
    RetryPolicy,
    RetryStrategy,
)
from app.models.registry import ProviderRegistry

logger = logging.getLogger(__name__)


class RoutingError(Exception):
    """Raised when routing fails."""


class ModelRouter:
    """Routes model requests to appropriate providers."""

    def __init__(
        self,
        registry: ProviderRegistry,
        retry_policy: Optional[RetryPolicy] = None,
        circuit_breaker: Optional[CircuitBreakerPolicy] = None,
        rate_limit: Optional[RateLimitPolicy] = None,
        load_balancer: Optional[LoadBalancerPolicy] = None,
        fallback: Optional[FallbackPolicy] = None,
    ) -> None:
        self._registry = registry
        self._retry_policy = retry_policy or RetryPolicy()
        self._circuit_breaker = circuit_breaker or CircuitBreakerPolicy()
        self._rate_limit = rate_limit or RateLimitPolicy()
        self._load_balancer = load_balancer or LoadBalancerPolicy()
        self._fallback = fallback or FallbackPolicy()
        self._provider_circuit_breakers: dict[str, CircuitBreakerPolicy] = {}
        self._provider_rate_limits: dict[str, RateLimitPolicy] = {}
        self._routing_history: list[dict[str, Any]] = []

    def select_provider(
        self,
        context: ModelContext,
        available_providers: Optional[list[str]] = None,
    ) -> str:
        if available_providers is None:
            available_providers = self._get_available_providers()

        if not available_providers:
            raise RoutingError("No providers available")

        if context.provider and context.provider in available_providers:
            return context.provider

        selected = self._load_balancer.select_provider(available_providers)
        self._routing_history.append({
            "request_id": str(context.request_id),
            "selected": selected,
            "available": available_providers,
            "timestamp": time.time(),
        })
        return selected

    def _get_available_providers(self) -> list[str]:
        available = []
        now = time.time()
        for provider_id in self._registry.list_providers():
            lifecycle = self._registry.get_lifecycle(provider_id)
            if not lifecycle or not lifecycle.is_available:
                continue
            cb = self._get_circuit_breaker(provider_id)
            if not cb.should_allow(now):
                continue
            available.append(provider_id)
        return available

    def _get_circuit_breaker(self, provider_id: str) -> CircuitBreakerPolicy:
        if provider_id not in self._provider_circuit_breakers:
            self._provider_circuit_breakers[provider_id] = CircuitBreakerPolicy()
        return self._provider_circuit_breakers[provider_id]

    def _get_rate_limit(self, provider_id: str) -> RateLimitPolicy:
        if provider_id not in self._provider_rate_limits:
            self._provider_rate_limits[provider_id] = RateLimitPolicy()
        return self._provider_rate_limits[provider_id]

    def record_success(self, provider_id: str) -> None:
        cb = self._get_circuit_breaker(provider_id)
        cb.record_success()

    def record_failure(self, provider_id: str) -> None:
        cb = self._get_circuit_breaker(provider_id)
        cb.record_failure(time.time())

    def get_fallback_provider(self, failed_provider: str) -> Optional[str]:
        return self._fallback.get_fallback(failed_provider)

    def get_retry_delay(self, attempt: int) -> float:
        return self._retry_policy.get_delay(attempt)

    def can_retry(self, error_type: str, attempt: int) -> bool:
        return self._retry_policy.should_retry(error_type, attempt)

    def get_routing_history(self) -> list[dict[str, Any]]:
        return list(self._routing_history[-100:])

    def to_dict(self) -> dict[str, Any]:
        return {
            "available_providers": self._get_available_providers(),
            "routing_history_count": len(self._routing_history),
        }
