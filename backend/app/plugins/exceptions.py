"""Plugin subsystem exceptions."""

from __future__ import annotations


class PluginError(Exception):
    """Base exception for plugin errors."""

    def __init__(self, plugin_id: str, message: str = "") -> None:
        self.plugin_id = plugin_id
        self.message = message or f"Plugin error: {plugin_id}"
        super().__init__(self.message)


class PluginNotFoundError(PluginError):
    """Raised when a plugin is not found."""

    def __init__(self, plugin_id: str) -> None:
        super().__init__(plugin_id, f"Plugin not found: {plugin_id}")


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""

    def __init__(self, plugin_id: str, reason: str = "") -> None:
        super().__init__(plugin_id, f"Failed to load plugin {plugin_id}: {reason}")


class PluginInitError(PluginError):
    """Raised when a plugin fails to initialize."""

    def __init__(self, plugin_id: str, reason: str = "") -> None:
        super().__init__(plugin_id, f"Failed to initialize plugin {plugin_id}: {reason}")


class PluginValidationError(PluginError):
    """Raised when plugin validation fails."""

    def __init__(self, plugin_id: str, errors: list[str] | None = None) -> None:
        self.errors = errors or []
        detail = "; ".join(self.errors) if self.errors else "validation failed"
        super().__init__(plugin_id, f"Plugin validation error for {plugin_id}: {detail}")


class PluginConflictError(PluginError):
    """Raised when there is a dependency conflict between plugins."""

    def __init__(self, plugin_id: str, conflict: str = "") -> None:
        super().__init__(plugin_id, f"Plugin conflict for {plugin_id}: {conflict}")


class PluginTimeoutError(PluginError):
    """Raised when a plugin operation times out."""

    def __init__(self, plugin_id: str, operation: str = "") -> None:
        super().__init__(plugin_id, f"Plugin timeout for {plugin_id}: {operation}")


class PluginSandboxError(PluginError):
    """Raised when a plugin violates sandbox constraints."""

    def __init__(self, plugin_id: str, violation: str = "") -> None:
        super().__init__(plugin_id, f"Sandbox violation for {plugin_id}: {violation}")


class PluginDependencyError(PluginError):
    """Raised when plugin dependency resolution fails."""

    def __init__(self, plugin_id: str, missing: str = "") -> None:
        super().__init__(plugin_id, f"Dependency error for {plugin_id}: {missing}")


class PluginVersionError(PluginError):
    """Raised when plugin version is incompatible."""

    def __init__(self, plugin_id: str, required: str = "", actual: str = "") -> None:
        super().__init__(plugin_id, f"Version incompatibility for {plugin_id}: requires {required}, got {actual}")


class HookError(PluginError):
    """Raised when a hook execution fails."""

    def __init__(self, plugin_id: str, hook_name: str = "", reason: str = "") -> None:
        super().__init__(plugin_id, f"Hook error [{hook_name}] for {plugin_id}: {reason}")
