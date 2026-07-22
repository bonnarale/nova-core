"""AgentDiscoveryTool — discover and query registered agents."""

from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.result import ToolResult


class AgentDiscoveryTool(Tool):
    """Discover and query registered agents in the Multi-Agent Runtime."""

    def __init__(self, agent_runtime: Any = None) -> None:
        self._runtime = agent_runtime

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="agent_discovery",
            description="Discover and query registered agents — list, find by capability, health check.",
            category="retrieval",
            tool_id="agent_discovery",
            version="1.0.0",
            capabilities=["agent", "discovery", "registry"],
            tags=["agent", "discovery", "runtime"],
            policy="immediate",
            timeout_default=10.0,
            retry_default=0,
            permission_level="read",
            parameters=[
                ToolParam(name="operation", type="string", required=True, description="One of: list, get, health, capabilities"),
                ToolParam(name="agent_id", type="string", required=False, description="Agent ID (for get/health)"),
                ToolParam(name="capability", type="string", required=False, description="Filter by capability"),
            ],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        operation = params.get("operation", "")

        if not self._runtime:
            return ToolResult(
                success=True,
                data={"agents": [], "message": "Agent runtime not configured"},
                metadata={"stub": True},
            )

        try:
            if operation == "list":
                return await self._list_agents()
            elif operation == "get":
                return await self._get_agent(params)
            elif operation == "health":
                return await self._health_check(params)
            elif operation == "capabilities":
                return await self._get_capabilities(params)
            else:
                return ToolResult.error_result("agent_discovery", f"Unknown operation: {operation}")
        except Exception as exc:
            return ToolResult.error_result("agent_discovery", f"Agent discovery failed: {exc}")

    async def _list_agents(self) -> ToolResult:
        agents = self._runtime.list_agents()
        agent_list = []
        for agent in agents:
            agent_list.append({
                "agent_id": agent.agent_id,
                "type": agent.__class__.__name__,
                "definition": agent.definition.to_dict() if hasattr(agent, "definition") else {},
            })
        return ToolResult(
            success=True,
            data={"agents": agent_list, "total": len(agent_list)},
        )

    async def _get_agent(self, params: dict[str, Any]) -> ToolResult:
        agent_id = params.get("agent_id", "")
        if not agent_id:
            return ToolResult.error_result("agent_discovery", "agent_id is required for get")
        agent = self._runtime.get_agent(agent_id)
        if agent is None:
            return ToolResult.error_result("agent_discovery", f"Agent '{agent_id}' not found")
        return ToolResult(
            success=True,
            data={
                "agent_id": agent.agent_id,
                "type": agent.__class__.__name__,
                "definition": agent.definition.to_dict() if hasattr(agent, "definition") else {},
            },
        )

    async def _health_check(self, params: dict[str, Any]) -> ToolResult:
        results = await self._runtime.health()
        return ToolResult(success=True, data=results)

    async def _get_capabilities(self, params: dict[str, Any]) -> ToolResult:
        agents = self._runtime.list_agents()
        caps = {}
        for agent in agents:
            defn = agent.definition if hasattr(agent, "definition") else None
            caps[agent.agent_id] = {
                "role": defn.role if defn else "",
                "allowed_tools": list(defn.allowed_tools) if defn else [],
                "permissions": dict(defn.permissions) if defn else {},
            }
        return ToolResult(success=True, data={"capabilities": caps})
