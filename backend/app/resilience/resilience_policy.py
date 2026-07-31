"""Resilience policy configuration."""

from __future__ import annotations

import threading
from typing import Any

from app.resilience.enums import FallbackStrategy, RecoveryPolicy, RetryStrategy


class ResiliencePolicy:
    """Configurable resilience policy for a subsystem."""

    __slots__ = (
        "name", "circuit_breaker_threshold", "circuit_breaker_timeout",
        "retry_strategy", "max_retries", "retry_base_delay",
        "timeout", "fallback_strategy", "recovery_policy",
        "bulkhead_limit", "rate_limit",
    )

    def __init__(
        self,
        name: str = "default",
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: float = 30.0,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        timeout: float = 30.0,
        fallback_strategy: FallbackStrategy = FallbackStrategy.DEFAULT,
        recovery_policy: RecoveryPolicy = RecoveryPolicy.RESTART,
        bulkhead_limit: int = 10,
        rate_limit: float = 100.0,
    ) -> None:
        self.name = name
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.retry_strategy = retry_strategy
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.timeout = timeout
        self.fallback_strategy = fallback_strategy
        self.recovery_policy = recovery_policy
        self.bulkhead_limit = bulkhead_limit
        self.rate_limit = rate_limit

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "circuit_breaker_threshold": self.circuit_breaker_threshold,
            "circuit_breaker_timeout": self.circuit_breaker_timeout,
            "retry_strategy": self.retry_strategy.value,
            "max_retries": self.max_retries,
            "retry_base_delay": self.retry_base_delay,
            "timeout": self.timeout,
            "fallback_strategy": self.fallback_strategy.value,
            "recovery_policy": self.recovery_policy.value,
            "bulkhead_limit": self.bulkhead_limit,
            "rate_limit": self.rate_limit,
        }


class ResiliencePolicyManager:
    """Manages resilience policies for all subsystems."""

    _SUBSYSTEM_POLICIES: dict[str, dict[str, Any]] = {
        "cognitive_engine": {"circuit_breaker_threshold": 3, "timeout": 120.0, "max_retries": 2},
        "memory_system": {"circuit_breaker_threshold": 5, "timeout": 10.0, "max_retries": 3},
        "learning_engine": {"circuit_breaker_threshold": 3, "timeout": 60.0, "max_retries": 2},
        "knowledge_engine": {"circuit_breaker_threshold": 5, "timeout": 30.0, "max_retries": 3},
        "reasoning_engine": {"circuit_breaker_threshold": 3, "timeout": 60.0, "max_retries": 2},
        "goal_engine": {"circuit_breaker_threshold": 5, "timeout": 15.0, "max_retries": 3},
        "task_engine": {"circuit_breaker_threshold": 5, "timeout": 30.0, "max_retries": 3},
        "planning_engine": {"circuit_breaker_threshold": 3, "timeout": 60.0, "max_retries": 2},
        "execution_engine": {"circuit_breaker_threshold": 5, "timeout": 120.0, "max_retries": 3},
        "multi_agent": {"circuit_breaker_threshold": 3, "timeout": 60.0, "max_retries": 2},
        "tool_system": {"circuit_breaker_threshold": 5, "timeout": 30.0, "max_retries": 3},
        "model_gateway": {"circuit_breaker_threshold": 3, "timeout": 120.0, "max_retries": 2},
        "rag": {"circuit_breaker_threshold": 5, "timeout": 30.0, "max_retries": 3},
        "vector_memory": {"circuit_breaker_threshold": 5, "timeout": 15.0, "max_retries": 3},
        "event_system": {"circuit_breaker_threshold": 5, "timeout": 10.0, "max_retries": 3},
        "scheduler": {"circuit_breaker_threshold": 5, "timeout": 30.0, "max_retries": 3},
        "workflow_engine": {"circuit_breaker_threshold": 5, "timeout": 300.0, "max_retries": 2},
        "plugin_system": {"circuit_breaker_threshold": 3, "timeout": 30.0, "max_retries": 2},
        "security": {"circuit_breaker_threshold": 3, "timeout": 15.0, "max_retries": 2},
        "observability": {"circuit_breaker_threshold": 5, "timeout": 10.0, "max_retries": 3},
        "deployment": {"circuit_breaker_threshold": 5, "timeout": 60.0, "max_retries": 2},
        "scaling": {"circuit_breaker_threshold": 5, "timeout": 30.0, "max_retries": 3},
    }

    def __init__(self) -> None:
        self._policies: dict[str, ResiliencePolicy] = {}
        self._lock = threading.RLock()
        for name, overrides in self._SUBSYSTEM_POLICIES.items():
            self._policies[name] = ResiliencePolicy(name, **overrides)

    def get(self, name: str) -> ResiliencePolicy:
        with self._lock:
            return self._policies.get(name, ResiliencePolicy(name))

    def set(self, policy: ResiliencePolicy) -> None:
        with self._lock:
            self._policies[policy.name] = policy

    def get_all(self) -> dict[str, ResiliencePolicy]:
        with self._lock:
            return dict(self._policies)

    def get_all_as_dicts(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {k: v.to_dict() for k, v in self._policies.items()}
