"""Type definitions for the Plugin subsystem."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PluginProtocol(Protocol):
    """Protocol that all plugins must satisfy."""

    @property
    def plugin_id(self) -> str: ...

    @property
    def plugin_name(self) -> str: ...

    @property
    def plugin_version(self) -> str: ...

    async def initialize(self) -> None: ...

    async def shutdown(self) -> None: ...

    async def health(self) -> dict[str, Any]: ...


@runtime_checkable
class PluginHookHandler(Protocol):
    """Protocol for hook handlers."""

    @property
    def hook_name(self) -> str: ...

    async def handle(self, context: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class PluginMiddleware(Protocol):
    """Protocol for plugin middleware."""

    @property
    def middleware_name(self) -> str: ...

    async def before(self, context: dict[str, Any]) -> dict[str, Any]: ...

    async def after(self, context: dict[str, Any], result: Any) -> Any: ...

    async def on_error(self, context: dict[str, Any], error: Exception) -> bool: ...


@runtime_checkable
class PluginValidator(Protocol):
    """Protocol for plugin validators."""

    async def validate_manifest(self, manifest: dict[str, Any]) -> list[str]: ...

    async def validate_config(self, config: dict[str, Any]) -> list[str]: ...


PluginHook = dict[str, Any]
PluginConfig = dict[str, Any]
PluginManifestData = dict[str, Any]
PluginResult = dict[str, Any]
