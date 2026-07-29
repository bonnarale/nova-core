"""Integration abstract base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.integration.enums import ComponentState, HealthStatus


class IntegrationProvider(ABC):
    """Base provider interface for integration operations."""

    @abstractmethod
    async def start(self) -> None:
        """Start the integration provider."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the integration provider."""
        ...

    @abstractmethod
    def is_running(self) -> bool:
        """Check if the provider is running."""
        ...


class IntegrationCoordinator(ABC):
    """Coordinator interface for subsystem integration."""

    @abstractmethod
    async def register_component(self, name: str, component: Any, **kwargs: Any) -> None:
        """Register a component with the integration layer."""
        ...

    @abstractmethod
    async def unregister_component(self, name: str) -> bool:
        """Unregister a component by name."""
        ...

    @abstractmethod
    async def get_component(self, name: str) -> Any | None:
        """Get a registered component by name."""
        ...

    @abstractmethod
    async def list_components(self) -> list[dict[str, Any]]:
        """List all registered components."""
        ...


class DependencyGraphProvider(ABC):
    """Provider for dependency graph operations."""

    @abstractmethod
    async def add_dependency(self, source: str, target: str, dep_type: str = "required") -> None:
        """Add a dependency edge."""
        ...

    @abstractmethod
    async def remove_dependency(self, source: str, target: str) -> None:
        """Remove a dependency edge."""
        ...

    @abstractmethod
    async def get_dependencies(self, component: str) -> dict[str, list[str]]:
        """Get dependencies for a component."""
        ...

    @abstractmethod
    async def detect_cycles(self) -> list[list[str]]:
        """Detect circular dependencies."""
        ...

    @abstractmethod
    async def topological_sort(self) -> list[str]:
        """Get topological ordering of components."""
        ...


class CompatibilityProvider(ABC):
    """Provider for compatibility checking."""

    @abstractmethod
    async def check_compatibility(self, component_a: str, component_b: str) -> dict[str, Any]:
        """Check compatibility between two components."""
        ...

    @abstractmethod
    async def check_all(self) -> list[dict[str, Any]]:
        """Check compatibility across all components."""
        ...


class DiagnosticsProvider(ABC):
    """Provider for system diagnostics."""

    @abstractmethod
    async def collect_diagnostics(self) -> dict[str, Any]:
        """Collect comprehensive diagnostics data."""
        ...

    @abstractmethod
    async def get_component_info(self, name: str) -> dict[str, Any] | None:
        """Get diagnostic info for a specific component."""
        ...
