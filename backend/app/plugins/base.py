"""Abstract base classes for the Plugin subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.plugins.enums import HookType, PluginState
from app.plugins.models import HookContext, PluginManifest


class PluginProvider(ABC):
    """Provider interface for the plugin engine."""

    @abstractmethod
    async def initialize(self) -> None:
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        ...


class PluginBase(ABC):
    """Abstract base class that all plugins must extend."""

    @property
    @abstractmethod
    def manifest(self) -> PluginManifest:
        """Return the plugin's manifest."""
        ...

    @abstractmethod
    async def initialize(self) -> None:
        """Called once after the plugin is loaded."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Called once before the plugin is unloaded."""
        ...

    async def health(self) -> dict[str, Any]:
        """Return health status."""
        return {"plugin_id": self.manifest.plugin_id, "status": "healthy"}

    async def on_enable(self) -> None:
        """Called when the plugin is enabled."""

    async def on_disable(self) -> None:
        """Called when the plugin is disabled."""


class HookHandler(ABC):
    """Abstract base for hook handlers."""

    @property
    @abstractmethod
    def hook_name(self) -> str:
        ...

    @property
    def hook_type(self) -> HookType:
        return HookType.BEFORE

    @property
    def priority(self) -> int:
        return 50

    @abstractmethod
    async def handle(self, context: HookContext) -> HookContext:
        ...


class PluginRepository(ABC):
    """Repository interface for plugin persistence."""

    @abstractmethod
    async def store(self, plugin_id: str, data: dict[str, Any]) -> None:
        ...

    @abstractmethod
    async def get(self, plugin_id: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    async def list_all(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def delete(self, plugin_id: str) -> bool:
        ...

    @abstractmethod
    async def count(self) -> int:
        ...


class PluginMiddlewareBase(ABC):
    """Abstract base for plugin middleware."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def priority(self) -> int:
        return 50

    @abstractmethod
    async def before_execute(self, plugin_id: str, context: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    async def after_execute(self, plugin_id: str, context: dict[str, Any], result: Any) -> Any:
        ...

    @abstractmethod
    async def on_error(self, plugin_id: str, context: dict[str, Any], error: Exception) -> bool:
        ...


class PluginDiscovery(ABC):
    """Interface for discovering plugins."""

    @abstractmethod
    async def discover(self) -> list[PluginManifest]:
        ...

    @abstractmethod
    async def discover_by_type(self, plugin_type: str) -> list[PluginManifest]:
        ...


class PluginValidator(ABC):
    """Interface for validating plugins."""

    @abstractmethod
    async def validate_manifest(self, manifest: PluginManifest) -> list[str]:
        ...

    @abstractmethod
    async def validate_config(self, plugin_id: str, config: dict[str, Any]) -> list[str]:
        ...
