"""Enhanced agent registry with capability-aware lookup."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.agents.capabilities import AgentCapability, CapabilityRegistry
from app.agents.lifecycle import AgentLifecycle, AgentState

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Central registry for agent instances, their capabilities, and lifecycle states.

    This complements the existing AgentManager by providing capability-aware
    lookup, lifecycle tracking, and health monitoring.
    """

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._capabilities = CapabilityRegistry()
        self._lifecycles: dict[str, AgentLifecycle] = {}

    @property
    def capabilities(self) -> CapabilityRegistry:
        return self._capabilities

    def register(
        self,
        agent: BaseAgent,
        capability: AgentCapability | None = None,
    ) -> None:
        self._agents[agent.agent_id] = agent
        lc = AgentLifecycle(agent.agent_id)
        lc.register()
        lc.initialize()
        self._lifecycles[agent.agent_id] = lc

        if capability is None:
            capability = self._extract_capability(agent)
        self._capabilities.register(agent.agent_id, capability)
        logger.info("AgentRegistry: registered %s with policy=%s", agent.agent_id, capability.execution_policy)

    def unregister(self, agent_id: str) -> None:
        lc = self._lifecycles.get(agent_id)
        if lc:
            lc.shutdown()
        self._agents.pop(agent_id, None)
        self._capabilities.unregister(agent_id)
        self._lifecycles.pop(agent_id, None)

    def get(self, agent_id: str) -> BaseAgent | None:
        return self._agents.get(agent_id)

    def get_capability(self, agent_id: str) -> AgentCapability | None:
        return self._capabilities.get(agent_id)

    def get_lifecycle(self, agent_id: str) -> AgentLifecycle | None:
        return self._lifecycles.get(agent_id)

    def list_agents(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def list_agent_ids(self) -> list[str]:
        return list(self._agents.keys())

    def find_capable(
        self,
        intent: str | None = None,
        task_type: str | None = None,
        tool: str | None = None,
        tags: list[str] | None = None,
    ) -> list[tuple[str, AgentCapability]]:
        return self._capabilities.find_capable(intent, task_type, tool, tags)

    def get_ready_agents(self) -> list[str]:
        ready = []
        for agent_id, lc in self._lifecycles.items():
            if lc.state == AgentState.READY:
                ready.append(agent_id)
        return ready

    def get_running_agents(self) -> list[str]:
        running = []
        for agent_id, lc in self._lifecycles.items():
            if lc.state == AgentState.RUNNING:
                running.append(agent_id)
        return running

    def get_busy_count(self, agent_id: str) -> int:
        cap = self._capabilities.get(agent_id)
        if cap is None:
            return 0
        running = len([a for a in self._lifecycles if self._lifecycles[a].state == AgentState.RUNNING])
        return min(running, cap.concurrency_limit)

    def has_capacity(self, agent_id: str) -> bool:
        cap = self._capabilities.get(agent_id)
        lc = self._lifecycles.get(agent_id)
        if cap is None or lc is None:
            return False
        if lc.state not in (AgentState.READY, AgentState.COMPLETED):
            return False
        running_count = sum(
            1 for aid, l in self._lifecycles.items()
            if aid == agent_id and l.state == AgentState.RUNNING
        )
        return running_count < cap.concurrency_limit

    def to_dict(self) -> dict[str, Any]:
        result = {}
        for agent_id, agent in self._agents.items():
            cap = self._capabilities.get(agent_id)
            lc = self._lifecycles.get(agent_id)
            result[agent_id] = {
                "metadata": agent.metadata,
                "capability": cap.to_dict() if cap else None,
                "lifecycle": lc.to_dict() if lc else None,
            }
        return result

    @staticmethod
    def _extract_capability(agent: BaseAgent) -> AgentCapability:
        defn = agent.definition
        return AgentCapability(
            supported_intents=[defn.role],
            supported_task_types=[defn.role],
            supported_tools=list(defn.allowed_tools),
            priority=5,
            concurrency_limit=5,
            execution_policy="immediate",
        )
