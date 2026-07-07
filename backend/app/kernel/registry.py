"""Registry for kernel components (agents, tools, providers)."""

import logging
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)


class Agent(Protocol):
    """Protocol for agent implementations."""

    agent_id: str

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute a task and return results."""
        ...


class Tool(Protocol):
    """Protocol for tool implementations."""

    tool_id: str

    async def run(self, input: dict[str, Any]) -> dict[str, Any]:
        """Run the tool with given input."""
        ...


# Agent registry
_agents: dict[str, Agent] = {}


def register_agent(agent: Agent) -> None:
    """Register an agent with the kernel."""
    _agents[agent.agent_id] = agent
    logger.debug("Agent registered: %s", agent.agent_id)


def get_agent(agent_id: str) -> Optional[Agent]:
    """Get an agent by ID."""
    return _agents.get(agent_id)


def list_agents() -> list[str]:
    """List all registered agent IDs."""
    return list(_agents.keys())


def unregister_agent(agent_id: str) -> bool:
    """Unregister an agent by ID."""
    if agent_id in _agents:
        del _agents[agent_id]
        logger.debug("Agent unregistered: %s", agent_id)
        return True
    return False


# Tool registry
_tools: dict[str, Tool] = {}


def register_tool(tool: Tool) -> None:
    """Register a tool with the kernel."""
    _tools[tool.tool_id] = tool
    logger.debug("Tool registered: %s", tool.tool_id)


def get_tool(tool_id: str) -> Optional[Tool]:
    """Get a tool by ID."""
    return _tools.get(tool_id)


def list_tools() -> list[str]:
    """List all registered tool IDs."""
    return list(_tools.keys())


def unregister_tool(tool_id: str) -> bool:
    """Unregister a tool by ID."""
    if tool_id in _tools:
        del _tools[tool_id]
        logger.debug("Tool unregistered: %s", tool_id)
        return True
    return False


# Provider registry
_providers: dict[str, Any] = {}


def register_provider(name: str, provider: Any) -> None:
    """Register a provider (e.g., LLM, embedding) with the kernel."""
    _providers[name] = provider
    logger.debug("Provider registered: %s", name)


def get_provider(name: str) -> Optional[Any]:
    """Get a provider by name."""
    return _providers.get(name)


def list_providers() -> list[str]:
    """List all registered provider names."""
    return list(_providers.keys())


def unregister_provider(name: str) -> bool:
    """Unregister a provider by name."""
    if name in _providers:
        del _providers[name]
        logger.debug("Provider unregistered: %s", name)
        return True
    return False