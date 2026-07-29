"""Domain models for the Plugin subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.plugins.enums import (
    HookPriority,
    HookType,
    PluginPermission,
    PluginState,
    PluginType,
)


@dataclass
class PluginDependency:
    """Describes a dependency on another plugin."""

    plugin_id: str = ""
    version_min: str = ""
    version_max: str = ""
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "version_min": self.version_min,
            "version_max": self.version_max,
            "required": self.required,
        }


@dataclass
class PluginManifest:
    """Declarative metadata for a plugin."""

    plugin_id: str = ""
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    plugin_type: PluginType = PluginType.EXTENSION
    permissions: list[PluginPermission] = field(default_factory=list)
    dependencies: list[PluginDependency] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)
    hooks: list[str] = field(default_factory=list)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "type": self.plugin_type.value,
            "permissions": [p.value for p in self.permissions],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "capabilities": list(self.capabilities),
            "tags": list(self.tags),
            "config_schema": dict(self.config_schema),
            "hooks": list(self.hooks),
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
        }


@dataclass
class PluginInfo:
    """Runtime information about a registered plugin."""

    manifest: PluginManifest = field(default_factory=PluginManifest)
    state: PluginState = PluginState.REGISTERED
    config: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    load_time_ms: float = 0.0
    init_time_ms: float = 0.0
    instance: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.manifest.plugin_id,
            "name": self.manifest.name,
            "version": self.manifest.version,
            "type": self.manifest.plugin_type.value,
            "state": self.state.value,
            "enabled": self.manifest.enabled,
            "description": self.manifest.description,
            "author": self.manifest.author,
            "permissions": [p.value for p in self.manifest.permissions],
            "capabilities": list(self.manifest.capabilities),
            "tags": list(self.manifest.tags),
            "dependencies": [d.to_dict() for d in self.manifest.dependencies],
            "config": dict(self.config),
            "error_message": self.error_message,
            "load_time_ms": self.load_time_ms,
            "init_time_ms": self.init_time_ms,
        }


@dataclass
class HookRegistration:
    """A registered hook binding."""

    hook_name: str = ""
    plugin_id: str = ""
    hook_type: HookType = HookType.BEFORE
    priority: HookPriority = HookPriority.NORMAL
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hook_name": self.hook_name,
            "plugin_id": self.plugin_id,
            "hook_type": self.hook_type.value,
            "priority": self.priority.value,
            "enabled": self.enabled,
        }


@dataclass
class HookContext:
    """Context passed to hook handlers."""

    hook_name: str = ""
    hook_type: HookType = HookType.BEFORE
    source_plugin_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hook_name": self.hook_name,
            "hook_type": self.hook_type.value,
            "source_plugin_id": self.source_plugin_id,
            "data": dict(self.data),
            "metadata": dict(self.metadata),
        }


@dataclass
class PluginEvent:
    """Event emitted by the plugin system."""

    event_id: str = ""
    event_type: str = ""
    plugin_id: str = ""
    timestamp: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "plugin_id": self.plugin_id,
            "timestamp": self.timestamp,
            "data": dict(self.data),
        }


@dataclass
class PluginExecutionResult:
    """Result of executing a plugin operation."""

    success: bool = True
    plugin_id: str = ""
    operation: str = ""
    result: Any = None
    error: str = ""
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "plugin_id": self.plugin_id,
            "operation": self.operation,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class SandboxConfig:
    """Configuration for plugin sandbox isolation."""

    max_memory_mb: float = 256.0
    max_cpu_seconds: float = 30.0
    max_hooks: int = 100
    allowed_permissions: list[PluginPermission] = field(default_factory=list)
    restricted: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_seconds": self.max_cpu_seconds,
            "max_hooks": self.max_hooks,
            "allowed_permissions": [p.value for p in self.allowed_permissions],
            "restricted": self.restricted,
        }


@dataclass
class PluginStatistics:
    """Aggregate statistics for the plugin system."""

    total_plugins: int = 0
    active_plugins: int = 0
    failed_plugins: int = 0
    total_hooks: int = 0
    total_events: int = 0
    total_executions: int = 0
    average_load_time_ms: float = 0.0
    average_init_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_plugins": self.total_plugins,
            "active_plugins": self.active_plugins,
            "failed_plugins": self.failed_plugins,
            "total_hooks": self.total_hooks,
            "total_events": self.total_events,
            "total_executions": self.total_executions,
            "average_load_time_ms": self.average_load_time_ms,
            "average_init_time_ms": self.average_init_time_ms,
        }
