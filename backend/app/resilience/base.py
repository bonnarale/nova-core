"""Resilience abstract base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ResilienceProvider(ABC):
    """Base provider interface for resilience operations."""

    @abstractmethod
    async def start(self) -> None:
        """Start the resilience provider."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the resilience provider."""
        ...

    @abstractmethod
    def is_running(self) -> bool:
        """Check if the provider is running."""
        ...


class CircuitBreakerProvider(ABC):
    """Provider interface for circuit breaker operations."""

    @abstractmethod
    async def execute(self, name: str, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute a function through a circuit breaker."""
        ...

    @abstractmethod
    def get_state(self, name: str) -> str:
        """Get the state of a circuit breaker."""
        ...


class RetryProvider(ABC):
    """Provider interface for retry operations."""

    @abstractmethod
    async def execute(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute a function with retry logic."""
        ...


class TimeoutProvider(ABC):
    """Provider interface for timeout operations."""

    @abstractmethod
    async def execute(self, func: Any, *args: Any, timeout: float | None = None, **kwargs: Any) -> Any:
        """Execute a function with a timeout."""
        ...


class RecoveryProvider(ABC):
    """Provider interface for recovery operations."""

    @abstractmethod
    async def recover(self, component: str) -> bool:
        """Attempt to recover a failed component."""
        ...

    @abstractmethod
    def get_recovery_history(self) -> list[dict[str, Any]]:
        """Get history of recovery attempts."""
        ...


class FailoverProvider(ABC):
    """Provider interface for failover operations."""

    @abstractmethod
    async def failover(self, primary: str, reason: str) -> str | None:
        """Execute failover from primary to secondary."""
        ...

    @abstractmethod
    def get_failover_history(self) -> list[dict[str, Any]]:
        """Get history of failover events."""
        ...
