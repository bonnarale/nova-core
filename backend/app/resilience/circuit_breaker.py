"""Circuit breaker implementation."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Awaitable

from app.resilience.enums import CircuitState


class CircuitBreaker:
    """Thread-safe circuit breaker with configurable thresholds."""

    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 30.0, half_open_max: int = 1) -> None:
        self.name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max = half_open_max
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
            return self._state

    def record_success(self) -> None:
        with self._lock:
            self._total_successes += 1
            self._total_calls += 1
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._half_open_max:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def record_failure(self) -> None:
        with self._lock:
            self._total_failures += 1
            self._total_calls += 1
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self._failure_threshold:
                    self._state = CircuitState.OPEN

    def allow_request(self) -> bool:
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            with self._lock:
                return self._half_open_calls < self._half_open_max
        return False

    def reset(self) -> None:
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "failure_threshold": self._failure_threshold,
                "recovery_timeout": self._recovery_timeout,
                "total_calls": self._total_calls,
                "total_failures": self._total_failures,
                "total_successes": self._total_successes,
                "last_failure_time": self._last_failure_time,
            }


class CircuitBreakerManager:
    """Manages multiple named circuit breakers."""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()

    def get_or_create(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> CircuitBreaker:
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, failure_threshold, recovery_timeout)
            return self._breakers[name]

    def get(self, name: str) -> CircuitBreaker | None:
        with self._lock:
            return self._breakers.get(name)

    def get_all(self) -> dict[str, CircuitBreaker]:
        with self._lock:
            return dict(self._breakers)

    def reset_all(self) -> None:
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()

    def reset(self, name: str) -> bool:
        with self._lock:
            breaker = self._breakers.get(name)
            if breaker:
                breaker.reset()
                return True
            return False

    def get_summary(self) -> dict[str, Any]:
        with self._lock:
            states: dict[str, str] = {}
            for name, b in self._breakers.items():
                states[name] = b.state.value
            open_count = sum(1 for b in self._breakers.values() if b.state == CircuitState.OPEN)
            half_open_count = sum(1 for b in self._breakers.values() if b.state == CircuitState.HALF_OPEN)
            return {
                "total": len(self._breakers),
                "closed": len(self._breakers) - open_count - half_open_count,
                "open": open_count,
                "half_open": half_open_count,
                "states": states,
            }
