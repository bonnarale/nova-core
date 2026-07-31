"""ToolRegistry — central registry for all tools."""

from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolSpec
from app.tools.exceptions import ToolNotFoundError
from app.tools.lifecycle import ToolLifecycle, ToolState


class ToolRegistry:
    """Registry of all available tools.

    Tools are identified by their ``spec.name``.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._lifecycles: dict[str, ToolLifecycle] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        name = tool.spec.name
        self._tools[name] = tool
        if name not in self._lifecycles:
            self._lifecycles[name] = ToolLifecycle(tool_id=name)

    def unregister(self, tool_name: str) -> None:
        """Remove a tool from the registry by name."""
        self._tools.pop(tool_name, None)
        self._lifecycles.pop(tool_name, None)

    def lookup(self, tool_name: str) -> Tool:
        """Look up a tool by name. Raises ``ToolNotFoundError`` if missing."""
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ToolNotFoundError(tool_name)
        return tool

    def get_tool(self, tool_name: str) -> Tool | None:
        """Look up a tool by name, returning None if missing."""
        return self._tools.get(tool_name)

    def get_lifecycle(self, tool_name: str) -> ToolLifecycle | None:
        return self._lifecycles.get(tool_name)

    def list_tools(self) -> list[ToolSpec]:
        """Return the specs of all registered tools."""
        return [t.spec for t in self._tools.values()]

    def list_tool_specs_dict(self) -> list[dict[str, Any]]:
        """Return the specs as serializable dicts."""
        return [t.spec.to_dict() for t in self._tools.values()]

    def discover(
        self,
        category: str | None = None,
        capability: str | None = None,
        tag: str | None = None,
    ) -> list[Tool]:
        """Discover tools by category, capability, or tag."""
        results: list[Tool] = []
        for tool in self._tools.values():
            spec = tool.spec
            if category and spec.category != category:
                continue
            if capability and capability not in spec.capabilities:
                continue
            if tag and tag not in spec.tags:
                continue
            results.append(tool)
        return results

    async def health_check(self) -> dict[str, Any]:
        """Run health checks on all registered tools."""
        results: dict[str, Any] = {}
        for name, tool in self._tools.items():
            try:
                h = await tool.health()
                results[name] = h
            except Exception as exc:
                results[name] = {"tool_id": name, "status": "error", "error": str(exc)}
        return results

    def clear(self) -> None:
        """Remove all registered tools."""
        self._tools.clear()
        self._lifecycles.clear()

    def __contains__(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def __len__(self) -> int:
        return len(self._tools)
