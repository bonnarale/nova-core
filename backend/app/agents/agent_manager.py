"""AgentManager — manages agent registration and dispatch."""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class Agent(Protocol):
    """Protocol for agents that can execute tasks."""

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute a task and return results."""
        ...


class AgentManager:
    """Manages agent registration and task dispatch."""

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, agent_id: str, agent: Agent) -> None:
        """Register an agent."""
        self._agents[agent_id] = agent
        logger.info("AgentManager: registered agent %s", agent_id)

    def unregister(self, agent_id: str) -> None:
        """Unregister an agent."""
        self._agents.pop(agent_id, None)
        logger.info("AgentManager: unregistered agent %s", agent_id)

    def get_agent(self, agent_id: str) -> Agent | None:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    async def dispatch(
        self,
        agent_id: str,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Dispatch a task to an agent."""
        agent = self._agents.get(agent_id)
        if agent is None:
            logger.warning("AgentManager: agent %s not found", agent_id)
            return {
                "status": "failed",
                "error": f"Agent {agent_id} not found",
            }

        try:
            result = await agent.execute(task, context or {})
            return result
        except Exception as exc:
            logger.exception("AgentManager: agent %s failed", agent_id)
            return {
                "status": "failed",
                "error": str(exc),
            }
