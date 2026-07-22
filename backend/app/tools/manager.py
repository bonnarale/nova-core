"""ToolManager — manages tool lifecycle, dependencies, permissions, policies, and monitoring."""

from __future__ import annotations

import logging
from typing import Any

from app.tools.base import Tool, ToolSpec
from app.tools.context import ToolContext
from app.tools.exceptions import ToolNotFoundError, ToolPermissionError
from app.tools.lifecycle import ToolLifecycle, ToolState
from app.tools.metrics import ToolMetrics
from app.tools.policies import (
    ToolExecutionPolicy,
    ToolPolicyType,
    get_tool_policy,
)
from app.tools.permissions import PermissionChecker, PermissionLevel, ToolPermission
from app.tools.registry import ToolRegistry
from app.tools.tracing import ToolTracer

logger = logging.getLogger(__name__)


class ToolManager:
    """Manages tool lifecycle, dependency injection, permissions, execution policies, and monitoring.

    Wraps ToolRegistry with higher-level operations: init, shutdown, health, policy-aware dispatch, etc.
    """

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        permission_checker: PermissionChecker | None = None,
        tracer: ToolTracer | None = None,
        metrics: ToolMetrics | None = None,
    ) -> None:
        self._registry = registry or ToolRegistry()
        self._permission_checker = permission_checker or PermissionChecker()
        self._tracer = tracer or ToolTracer()
        self._metrics = metrics or ToolMetrics()
        self._policies: dict[str, ToolExecutionPolicy] = {}
        self._dependencies: dict[str, list[str]] = {}

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    @property
    def permission_checker(self) -> PermissionChecker:
        return self._permission_checker

    @property
    def tracer(self) -> ToolTracer:
        return self._tracer

    @property
    def metrics(self) -> ToolMetrics:
        return self._metrics

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        tool: Tool,
        policy: str | ToolExecutionPolicy | None = None,
        permissions: ToolPermission | None = None,
        dependencies: list[str] | None = None,
    ) -> None:
        self._registry.register(tool)
        name = tool.spec.name
        lc = self._registry.get_lifecycle(name)
        if lc:
            lc.initialize()
            lc.ready()

        if policy:
            if isinstance(policy, str):
                self._policies[name] = get_tool_policy(policy)
            else:
                self._policies[name] = policy
        elif tool.spec.policy and tool.spec.policy != "immediate":
            try:
                self._policies[name] = get_tool_policy(tool.spec.policy)
            except ValueError:
                pass

        if permissions:
            self._permission_checker.register(permissions)

        if dependencies:
            self._dependencies[name] = dependencies

        logger.info("ToolManager: registered tool %s", name)

    def unregister(self, tool_name: str) -> None:
        lc = self._registry.get_lifecycle(tool_name)
        if lc:
            lc.shutdown()
        self._registry.unregister(tool_name)
        self._policies.pop(tool_name, None)
        self._dependencies.pop(tool_name, None)
        self._permission_checker.unregister(tool_name)
        logger.info("ToolManager: unregistered tool %s", tool_name)

    def get_tool(self, tool_name: str) -> Tool | None:
        return self._registry.get_tool(tool_name)

    def list_tools(self) -> list[ToolSpec]:
        return self._registry.list_tools()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize_all(self) -> None:
        for tool in self._registry._tools.values():
            lc = self._registry.get_lifecycle(tool.spec.name)
            if lc and lc.state == ToolState.REGISTERED:
                lc.initialize()
            try:
                await tool.initialize()
                if lc:
                    lc.ready()
            except Exception as exc:
                logger.error("Failed to initialize tool %s: %s", tool.spec.name, exc)
                if lc:
                    lc.fail()

    async def shutdown_all(self) -> None:
        for name, tool in list(self._registry._tools.items()):
            lc = self._registry.get_lifecycle(name)
            try:
                await tool.shutdown()
            except Exception as exc:
                logger.debug("Error shutting down tool %s: %s", name, exc)
            if lc:
                lc.shutdown()

    async def health_check(self) -> dict[str, Any]:
        return await self._registry.health_check()

    def get_lifecycle(self, tool_name: str) -> ToolLifecycle | None:
        return self._registry.get_lifecycle(tool_name)

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def check_permission(
        self,
        tool_name: str,
        agent_id: str = "",
        user_id: str = "",
        roles: list[str] | None = None,
        required_level: PermissionLevel = PermissionLevel.READ,
    ) -> bool:
        return self._permission_checker.check(
            tool_name, agent_id=agent_id, user_id=user_id, roles=roles, required_level=required_level,
        )

    def set_permission(self, permission: ToolPermission) -> None:
        self._permission_checker.register(permission)

    # ------------------------------------------------------------------
    # Policies
    # ------------------------------------------------------------------

    def get_policy(self, tool_name: str) -> ToolExecutionPolicy | None:
        return self._policies.get(tool_name)

    def set_policy(self, tool_name: str, policy: ToolExecutionPolicy) -> None:
        self._policies[tool_name] = policy

    # ------------------------------------------------------------------
    # Dependencies
    # ------------------------------------------------------------------

    def get_dependencies(self, tool_name: str) -> list[str]:
        return self._dependencies.get(tool_name, [])

    def check_dependencies(self, tool_name: str) -> bool:
        deps = self._dependencies.get(tool_name, [])
        return all(d in self._registry for d in deps)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(
        self,
        category: str | None = None,
        capability: str | None = None,
        tag: str | None = None,
    ) -> list[Tool]:
        return self._registry.discover(category=category, capability=capability, tag=tag)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        tools = {}
        for name, tool in self._registry._tools.items():
            lc = self._registry.get_lifecycle(name)
            tools[name] = {
                "spec": tool.spec.to_dict(),
                "lifecycle": lc.to_dict() if lc else None,
                "policy": self._policies[name].to_dict() if name in self._policies else None,
                "dependencies": self._dependencies.get(name, []),
            }
        return {
            "tools": tools,
            "permissions": self._permission_checker.to_dict(),
            "metrics": self._metrics.snapshot(),
            "traces_count": len(self._tracer.get_all_traces()),
        }
