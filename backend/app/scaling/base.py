"""Abstract base classes for the Scaling subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ScalingProvider(ABC):
    """Provider interface for scaling operations."""

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def shutdown(self) -> None: ...

    @abstractmethod
    async def scale_up(self, amount: int = 1) -> dict[str, Any]: ...

    @abstractmethod
    async def scale_down(self, amount: int = 1) -> dict[str, Any]: ...

    @abstractmethod
    def is_running(self) -> bool: ...

    @abstractmethod
    async def get_status(self) -> dict[str, Any]: ...


class LoadBalancerProvider(ABC):
    """Provider interface for load balancing."""

    @abstractmethod
    async def add_backend(self, backend_id: str, weight: int = 1) -> None: ...

    @abstractmethod
    async def remove_backend(self, backend_id: str) -> bool: ...

    @abstractmethod
    async def next_backend(self) -> str | None: ...

    @abstractmethod
    async def report_health(self, backend_id: str, healthy: bool) -> None: ...

    @abstractmethod
    async def get_backends(self) -> dict[str, Any]: ...


class WorkerPoolProvider(ABC):
    """Provider interface for worker pool management."""

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def add_worker(self, worker_id: str = "") -> str: ...

    @abstractmethod
    async def remove_worker(self, worker_id: str) -> bool: ...

    @abstractmethod
    async def submit_task(self, task: dict[str, Any], priority: str = "normal") -> str: ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]: ...


class CacheProvider(ABC):
    """Provider interface for caching."""

    @abstractmethod
    async def get(self, key: str) -> Any | None: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: float | None = None) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> bool: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    async def clear(self) -> int: ...

    @abstractmethod
    async def size(self) -> int: ...


class DistributedLockProvider(ABC):
    """Provider interface for distributed locks."""

    @abstractmethod
    async def acquire(self, key: str, timeout: float = 30.0, lease: float = 60.0) -> bool: ...

    @abstractmethod
    async def release(self, key: str) -> bool: ...

    @abstractmethod
    async def is_locked(self, key: str) -> bool: ...

    @abstractmethod
    async def extend(self, key: str, lease: float = 60.0) -> bool: ...


class AutoscalerProvider(ABC):
    """Provider interface for autoscaling."""

    @abstractmethod
    async def evaluate(self) -> dict[str, Any]: ...

    @abstractmethod
    async def get_recommendation(self) -> dict[str, Any]: ...

    @abstractmethod
    async def record_metric(self, metric: str, value: float) -> None: ...

    @abstractmethod
    def get_config(self) -> dict[str, Any]: ...
