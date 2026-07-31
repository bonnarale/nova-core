"""ToolFactory — auto-registration of built-in tools with capabilities."""

from __future__ import annotations

import logging
from typing import Any

from app.tools.base import Tool
from app.tools.lifecycle import ToolState
from app.tools.manager import ToolManager
from app.tools.permissions import PermissionLevel, ToolPermission
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolFactory:
    """Factory for registering built-in and custom tools with the ToolManager."""

    def __init__(self, manager: ToolManager | None = None) -> None:
        self._manager = manager or ToolManager()
        self._templates: dict[str, dict[str, Any]] = {}

    @property
    def manager(self) -> ToolManager:
        return self._manager

    def register_template(self, name: str, tool_cls: type[Tool], **kwargs: Any) -> None:
        self._templates[name] = {"cls": tool_cls, "kwargs": kwargs}

    def create_and_register(
        self,
        tool_cls: type[Tool],
        policy: str | None = None,
        permissions: ToolPermission | None = None,
        dependencies: list[str] | None = None,
    ) -> Tool:
        tool = tool_cls()
        self._manager.register(
            tool,
            policy=policy,
            permissions=permissions,
            dependencies=dependencies,
        )
        return tool

    def register_all_builtins(self) -> None:
        from app.tools.filesystem import FilesystemTool
        from app.tools.git import GitTool
        from app.tools.docker import DockerTool
        from app.tools.python import PythonTool
        from app.tools.http import HttpTool
        from app.tools.web import WebSearchTool

        builtins: list[tuple[type[Tool], str | None]] = [
            (FilesystemTool, None),
            (GitTool, None),
            (DockerTool, None),
            (PythonTool, None),
            (HttpTool, None),
            (WebSearchTool, None),
        ]

        try:
            from app.tools.builtin.memory_search import MemorySearchTool
            builtins.append((MemorySearchTool, None))
        except ImportError:
            pass

        try:
            from app.tools.builtin.knowledge_search import KnowledgeSearchTool
            builtins.append((KnowledgeSearchTool, None))
        except ImportError:
            pass

        try:
            from app.tools.builtin.goal_query import GoalQueryTool
            builtins.append((GoalQueryTool, None))
        except ImportError:
            pass

        try:
            from app.tools.builtin.task_query import TaskQueryTool
            builtins.append((TaskQueryTool, None))
        except ImportError:
            pass

        try:
            from app.tools.builtin.agent_discovery import AgentDiscoveryTool
            builtins.append((AgentDiscoveryTool, None))
        except ImportError:
            pass

        for tool_cls, policy in builtins:
            try:
                self.create_and_register(tool_cls, policy=policy)
            except Exception as exc:
                logger.warning("Failed to register builtin %s: %s", tool_cls.__name__, exc)

    def register_verticals(self) -> None:
        """Register vertical tool modules (consulting, etc.)."""
        try:
            from app.tools.verticals.consulting import ConsultingTools
            vertical = ConsultingTools()
            for tool in vertical.get_tools():
                self._manager.register(tool)
                logger.info("Registered vertical tool: %s", tool.spec.name)
        except Exception as exc:
            logger.warning("Failed to register consulting vertical: %s", exc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "templates": list(self._templates.keys()),
            "manager": self._manager.to_dict(),
        }
