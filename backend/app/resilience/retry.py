"""Retry logic with configurable strategies."""

from __future__ import annotations

import random
import threading
import time
from typing import Any, Callable, Awaitable, Coroutine

from app.resilience.enums import RetryStrategy


class RetryPolicy:
    """Configuration for a retry policy."""

    __slots__ = ("name", "strategy", "max_retries", "base_delay", "max_delay", "jitter")

    def __init__(
        self,
        name: str = "default",
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter: bool = True,
    ) -> None:
        self.name = name
        self.strategy = strategy
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (2 ** attempt)
        else:
            delay = self.base_delay * (attempt + 1)
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)
        return min(delay, self.max_delay)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "strategy": self.strategy.value,
            "max_retries": self.max_retries,
            "base_delay": self.base_delay,
            "max_delay": self.max_delay,
            "jitter": self.jitter,
        }


class RetryManager:
    """Manages retry execution with configurable policies."""

    def __init__(self) -> None:
        self._policies: dict[str, RetryPolicy] = {"default": RetryPolicy()}
        self._stats: dict[str, dict[str, int]] = {}
        self._lock = threading.RLock()

    def add_policy(self, policy: RetryPolicy) -> None:
        with self._lock:
            self._policies[policy.name] = policy

    def get_policy(self, name: str = "default") -> RetryPolicy:
        with self._lock:
            return self._policies.get(name, self._policies["default"])

    async def execute(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        policy_name: str = "default",
        **kwargs: Any,
    ) -> Any:
        policy = self.get_policy(policy_name)
        last_error: Exception | None = None
        for attempt in range(policy.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                self._record(policy.name, attempt, True)
                return result
            except Exception as exc:
                last_error = exc
                self._record(policy.name, attempt, False)
                if attempt < policy.max_retries:
                    delay = policy.get_delay(attempt)
                    await self._async_sleep(delay)
        raise last_error  # type: ignore[misc]

    def _record(self, policy_name: str, attempt: int, success: bool) -> None:
        with self._lock:
            if policy_name not in self._stats:
                self._stats[policy_name] = {"total": 0, "success": 0, "failure": 0}
            self._stats[policy_name]["total"] += 1
            if success:
                self._stats[policy_name]["success"] += 1
            else:
                self._stats[policy_name]["failure"] += 1

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            total = sum(s["total"] for s in self._stats.values())
            success = sum(s["success"] for s in self._stats.values())
            return {
                "total": total,
                "by_policy": dict(self._stats),
                "success_rate": success / total if total > 0 else 1.0,
            }

    def reset_stats(self) -> None:
        with self._lock:
            self._stats.clear()

    @staticmethod
    async def _async_sleep(delay: float) -> None:
        import asyncio
        await asyncio.sleep(delay)
