"""Factory for creating and configuring model gateway components."""

import logging
from typing import Any, Optional

from app.core.config import Settings
from app.models.cache import ResponseCache, get_response_cache
from app.models.gateway import ModelGateway
from app.models.load_balancer import LoadBalancingStrategy, get_load_balancer
from app.models.metrics import get_metrics_collector
from app.models.policies import (
    CircuitBreakerPolicy,
    FallbackPolicy,
    RateLimitPolicy,
    RetryPolicy,
    RetryStrategy,
)
from app.models.providers.base import ModelProvider
from app.models.providers.ollama import OllamaProvider
from app.models.registry import ProviderRegistry, get_provider_registry
from app.models.router import ModelRouter
from app.models.tracing import get_model_tracer

logger = logging.getLogger(__name__)


class ModelGatewayFactory:
    """Factory for creating and configuring model gateway components."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or Settings()
        self._registry = get_provider_registry()
        self._provider_configs: dict[str, dict[str, Any]] = {}

    def register_provider_config(self, provider_id: str, config: dict[str, Any]) -> None:
        self._provider_configs[provider_id] = config

    def create_ollama_provider(self) -> OllamaProvider:
        provider = OllamaProvider(self._settings)
        self._registry.register("ollama", provider, {"type": "ollama", "base_url": self._settings.ollama_url})
        return provider

    def create_provider(self, provider_id: str, provider_type: str, **kwargs: Any) -> ModelProvider:
        if provider_type == "ollama":
            provider = self.create_ollama_provider()
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
        self._registry.register(provider_id, provider, kwargs)
        return provider

    def create_gateway(
        self,
        load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        cache_max_size: int = 1000,
        cache_ttl: float = 300.0,
        retry_max: int = 3,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_recovery: float = 30.0,
        rate_limit_rpm: int = 60,
    ) -> ModelGateway:
        cache = get_response_cache(max_size=cache_max_size, default_ttl=cache_ttl)
        load_balancer = get_load_balancer(strategy=load_balancing_strategy)
        metrics = get_metrics_collector()
        tracer = get_model_tracer()

        retry_policy = RetryPolicy(max_retries=retry_max, strategy=retry_strategy)
        circuit_breaker = CircuitBreakerPolicy(
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=circuit_breaker_recovery,
        )
        rate_limit = RateLimitPolicy(requests_per_minute=rate_limit_rpm)
        fallback = FallbackPolicy(fallback_chain=list(self._registry.list_providers()))

        router = ModelRouter(
            registry=self._registry,
            retry_policy=retry_policy,
            circuit_breaker=circuit_breaker,
            rate_limit=rate_limit,
            load_balancer=load_balancer,
            fallback=fallback,
        )

        gateway = ModelGateway(
            registry=self._registry,
            router=router,
            cache=cache,
            load_balancer=load_balancer,
            metrics=metrics,
            tracer=tracer,
        )

        logger.info("Model gateway created with %d providers", self._registry.provider_count)
        return gateway

    def create_default_gateway(self) -> ModelGateway:
        self.create_ollama_provider()
        return self.create_gateway()

    def get_registry(self) -> ProviderRegistry:
        return self._registry


def get_model_gateway_factory(settings: Optional[Settings] = None) -> ModelGatewayFactory:
    return ModelGatewayFactory(settings)
