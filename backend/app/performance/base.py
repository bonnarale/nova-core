"""Performance abstract base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PerformanceProvider(ABC):
    """Base provider interface for performance optimization."""

    @abstractmethod
    async def start(self) -> None:
        """Start the provider."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the provider."""
        ...

    @abstractmethod
    def is_running(self) -> bool:
        """Check if the provider is running."""
        ...


class OptimizerProvider(ABC):
    """Provider interface for optimization operations."""

    @abstractmethod
    async def optimize(self, target: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run optimization for a target component."""
        ...

    @abstractmethod
    def get_recommendations(self) -> list[dict[str, Any]]:
        """Get optimization recommendations."""
        ...


class ProfilerProvider(ABC):
    """Provider interface for profiling operations."""

    @abstractmethod
    async def start_profile(self, profile_type: str = "comprehensive") -> str:
        """Start a profiling session."""
        ...

    @abstractmethod
    async def stop_profile(self, session_id: str) -> dict[str, Any]:
        """Stop a profiling session and return results."""
        ...

    @abstractmethod
    def get_active_sessions(self) -> list[dict[str, Any]]:
        """Get list of active profiling sessions."""
        ...


class BenchmarkProvider(ABC):
    """Provider interface for benchmark operations."""

    @abstractmethod
    async def run_benchmark(self, category: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a benchmark suite."""
        ...

    @abstractmethod
    def get_results(self, category: str | None = None) -> list[dict[str, Any]]:
        """Get benchmark results."""
        ...
