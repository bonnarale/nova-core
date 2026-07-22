"""Tool Runtime for NOVA CORE — unified execution layer for agent capabilities.

Every tool invocation goes through ``ToolRuntime`` or ``ToolExecutor``, which enforces:
- Input validation
- Permission checks
- Timeout / retry
- Tracing / metrics / events
- Lifecycle management
- Execution policies

Example wiring::

    from app.tools import (
        ToolRuntime, ToolManager, ToolFactory,
        DockerTool, FilesystemTool, GitTool, HttpTool,
        PythonTool, ToolExecutor, ToolRegistry, WebSearchTool,
        default_tool_registry,
    )

    manager = ToolManager()
    factory = ToolFactory(manager)
    factory.register_all_builtins()
    runtime = ToolRuntime(manager=manager)
    result = await runtime.execute_tool("filesystem", {"operation": "read", "path": "/tmp/test.txt"})
"""

from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.context import ToolContext
from app.tools.exceptions import (
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolValidationError,
)
from app.tools.executor import ToolExecutor
from app.tools.filesystem import FilesystemTool
from app.tools.git import GitTool
from app.tools.docker import DockerTool
from app.tools.factory import ToolFactory
from app.tools.http import HttpTool
from app.tools.lifecycle import ToolLifecycle, ToolState
from app.tools.manager import ToolManager
from app.tools.metrics import ToolMetrics
from app.tools.permissions import PermissionChecker, PermissionLevel, ToolPermission
from app.tools.policies import (
    ToolExecutionPolicy,
    ToolPolicyType,
    get_tool_policy,
    list_tool_policies,
    ImmediatePolicy,
    BackgroundPolicy,
    RetryablePolicy,
    ExclusivePolicy,
    ParallelPolicy,
    IdempotentPolicy,
)
from app.tools.python import PythonTool
from app.tools.registry import ToolRegistry
from app.tools.result import ToolResult
from app.tools.runtime import ToolRuntime
from app.tools.schema import build_input_schema, validate_schema
from app.tools.tracing import ToolTracer, ToolTrace
from app.tools.web import WebSearchTool


def default_tool_registry() -> ToolRegistry:
    """Create a ToolRegistry pre-loaded with all built-in tools."""
    registry = ToolRegistry()
    registry.register(FilesystemTool())
    registry.register(GitTool())
    registry.register(DockerTool())
    registry.register(PythonTool())
    registry.register(HttpTool())
    registry.register(WebSearchTool())
    return registry


__all__ = [
    # Base
    "Tool",
    "ToolParam",
    "ToolSpec",
    # Context
    "ToolContext",
    # Exceptions
    "ToolError",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolPermissionError",
    "ToolTimeoutError",
    "ToolValidationError",
    # Executor
    "ToolExecutor",
    # Factory
    "ToolFactory",
    # Lifecycle
    "ToolLifecycle",
    "ToolState",
    # Manager
    "ToolManager",
    # Metrics
    "ToolMetrics",
    # Permissions
    "PermissionChecker",
    "PermissionLevel",
    "ToolPermission",
    # Policies
    "ToolExecutionPolicy",
    "ToolPolicyType",
    "get_tool_policy",
    "list_tool_policies",
    "ImmediatePolicy",
    "BackgroundPolicy",
    "RetryablePolicy",
    "ExclusivePolicy",
    "ParallelPolicy",
    "IdempotentPolicy",
    # Python
    "PythonTool",
    # Registry
    "ToolRegistry",
    # Result
    "ToolResult",
    # Runtime
    "ToolRuntime",
    # Schema
    "build_input_schema",
    "validate_schema",
    # Tracing
    "ToolTracer",
    "ToolTrace",
    # Built-in tools
    "DockerTool",
    "FilesystemTool",
    "GitTool",
    "HttpTool",
    "WebSearchTool",
    # Helpers
    "default_tool_registry",
]
