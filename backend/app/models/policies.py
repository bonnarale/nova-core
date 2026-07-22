"""Policies for model provider operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class PolicyType(str, Enum):
    """Types of policies."""

    RETRY = "retry"
    CIRCUIT_BREAKER = "circuit_breaker"
    RATE_LIMIT = "rate_limit"
    LOAD_BALANCER = "load_balancer"
    FALLBACK = "fallback"
    CACHE = "cache"


class RetryStrategy(str, Enum):
    """Retry strategies."""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


@dataclass
class RetryPolicy:
    """Policy for retrying failed requests."""

    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    retryable_errors: list[str] = field(default_factory=lambda: ["timeout", "rate_limit", "server_error"])

    def get_delay(self, attempt: int) -> float:
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (2 ** attempt)
        else:
            delay = self.base_delay * (attempt + 1)
        return min(delay, self.max_delay)

    def should_retry(self, error_type: str, attempt: int) -> bool:
        return attempt < self.max_retries and error_type in self.retryable_errors


@dataclass
class CircuitBreakerPolicy:
    """Policy for circuit breaking unhealthy providers."""

    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    state: str = "closed"

    def record_failure(self, timestamp: float) -> None:
        self.failure_count += 1
        self.last_failure_time = timestamp
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "closed"

    def should_allow(self, timestamp: float) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if self.last_failure_time and (timestamp - self.last_failure_time) > self.recovery_timeout:
                self.state = "half_open"
                return True
            return False
        return True

    def reset(self) -> None:
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"


@dataclass
class RateLimitPolicy:
    """Policy for rate limiting requests."""

    requests_per_minute: int = 60
    requests_per_second: int = 10
    burst_size: int = 20
    _timestamps: list[float] = field(default_factory=list)

    def can_request(self, timestamp: float) -> bool:
        self._timestamps = [t for t in self._timestamps if timestamp - t < 60.0]
        return len(self._timestamps) < self.requests_per_minute

    def record_request(self, timestamp: float) -> None:
        self._timestamps.append(timestamp)

    def get_wait_time(self, timestamp: float) -> float:
        self._timestamps = [t for t in self._timestamps if timestamp - t < 60.0]
        if len(self._timestamps) < self.requests_per_minute:
            return 0.0
        oldest = min(self._timestamps)
        return 60.0 - (timestamp - oldest)


@dataclass
class LoadBalancerPolicy:
    """Policy for load balancing across providers."""

    strategy: str = "round_robin"
    weights: dict[str, float] = field(default_factory=dict)
    _index: int = 0

    def select_provider(self, providers: list[str]) -> str:
        if not providers:
            raise ValueError("No providers available")
        if self.strategy == "round_robin":
            provider = providers[self._index % len(providers)]
            self._index += 1
            return provider
        if self.strategy == "weighted":
            total_weight = sum(self.weights.get(p, 1.0) for p in providers)
            import random
            r = random.random() * total_weight
            cumulative = 0.0
            for p in providers:
                cumulative += self.weights.get(p, 1.0)
                if r <= cumulative:
                    return p
            return providers[-1]
        if self.strategy == "least_connections":
            return min(providers, key=lambda p: self.weights.get(p, 0.0))
        return providers[0]


@dataclass
class FallbackPolicy:
    """Policy for fallback to alternative providers."""

    enabled: bool = True
    fallback_chain: list[str] = field(default_factory=list)
    max_fallbacks: int = 2

    def get_fallback(self, failed_provider: str) -> Optional[str]:
        if not self.enabled:
            return None
        try:
            idx = self.fallback_chain.index(failed_provider)
            if idx + 1 < len(self.fallback_chain) and idx + 1 <= self.max_fallbacks:
                return self.fallback_chain[idx + 1]
        except ValueError:
            pass
        available = [p for p in self.fallback_chain if p != failed_provider]
        return available[0] if available else None


@dataclass
class CachePolicy:
    """Policy for response caching."""

    enabled: bool = True
    ttl_seconds: float = 300.0
    max_size: int = 1000
    cache_keys: list[str] = field(default_factory=lambda: ["model", "messages"])

    def should_cache(self, status: str) -> bool:
        return self.enabled and status == "completed"

    def get_cache_key(self, model: str, messages: list[dict[str, str]], **kwargs: Any) -> str:
        import hashlib
        import json
        key_data = {"model": model, "messages": messages, **{k: v for k, v in kwargs.items() if k in self.cache_keys}}
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()


def get_retry_policy(
    max_retries: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    base_delay: float = 1.0,
) -> RetryPolicy:
    return RetryPolicy(max_retries=max_retries, strategy=strategy, base_delay=base_delay)


def get_circuit_breaker_policy(
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
) -> CircuitBreakerPolicy:
    return CircuitBreakerPolicy(failure_threshold=failure_threshold, recovery_timeout=recovery_timeout)


def get_rate_limit_policy(
    requests_per_minute: int = 60,
) -> RateLimitPolicy:
    return RateLimitPolicy(requests_per_minute=requests_per_minute)
