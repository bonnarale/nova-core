"""Plugin subsystem — dynamic plugin management, hooks, and lifecycle."""

from __future__ import annotations

from app.plugins.api import PluginAPI
from app.plugins.base import (
    HookHandler,
    PluginBase,
    PluginDiscovery,
    PluginMiddlewareBase,
    PluginProvider,
    PluginRepository,
    PluginValidator,
)
from app.plugins.config import PluginConfigManager
from app.plugins.dependency import DependencyResolver
from app.plugins.discovery import PluginDiscoveryService
from app.plugins.engine import PluginEngine
from app.plugins.enums import (
    HookPriority,
    HookType,
    PluginEventType,
    PluginPermission,
    PluginState,
    PluginType,
)
from app.plugins.events import PluginEventBus
from app.plugins.exceptions import (
    HookError,
    PluginConflictError,
    PluginDependencyError,
    PluginError,
    PluginInitError,
    PluginLoadError,
    PluginNotFoundError,
    PluginSandboxError,
    PluginTimeoutError,
    PluginValidationError,
    PluginVersionError,
)
from app.plugins.factory import PluginFactory
from app.plugins.hooks import HookManager, HookRegistry
from app.plugins.lifecycle import PluginLifecycle
from app.plugins.loader import PluginLoader
from app.plugins.manifest import ManifestValidator
from app.plugins.manager import PluginManager
from app.plugins.metrics import PluginMetrics, get_plugin_metrics
from app.plugins.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    MiddlewareChain,
    TimingMiddleware,
)
from app.plugins.models import (
    HookContext,
    HookRegistration,
    PluginDependency,
    PluginEvent,
    PluginExecutionResult,
    PluginInfo,
    PluginManifest,
    PluginStatistics,
    SandboxConfig,
)
from app.plugins.persistence import InMemoryPluginRepository
from app.plugins.registry import PluginRegistry
from app.plugins.sandbox import PluginSandbox
from app.plugins.sandbox_manager import SandboxManager
from app.plugins.tracing import PluginTracer
from app.plugins.version import VersionManager

__all__ = [
    "PluginAPI",
    "PluginBase",
    "PluginConfigManager",
    "PluginDiscovery",
    "PluginDiscoveryService",
    "PluginEngine",
    "PluginError",
    "PluginEventType",
    "PluginEventBus",
    "PluginEvent",
    "PluginFactory",
    "PluginInfo",
    "PluginLoadError",
    "PluginLoader",
    "PluginManager",
    "PluginManifest",
    "PluginMetrics",
    "PluginMiddlewareBase",
    "PluginNotFoundError",
    "PluginPermission",
    "PluginProvider",
    "PluginRegistry",
    "PluginRepository",
    "PluginSandbox",
    "PluginSandboxError",
    "PluginState",
    "PluginStatistics",
    "PluginTimeoutError",
    "PluginType",
    "PluginValidationError",
    "PluginValidator",
    "PluginVersionError",
    "DependencyResolver",
    "HookContext",
    "HookError",
    "HookHandler",
    "HookManager",
    "HookPriority",
    "HookRegistry",
    "HookRegistration",
    "HookType",
    "InMemoryPluginRepository",
    "ManifestValidator",
    "MiddlewareChain",
    "ErrorHandlingMiddleware",
    "LoggingMiddleware",
    "TimingMiddleware",
    "PluginDependency",
    "PluginExecutionResult",
    "SandboxConfig",
    "SandboxManager",
    "VersionManager",
    "get_plugin_metrics",
]
