"""Agent factory — automatic registration and lifecycle management."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.agents.capabilities import AgentCapability, CapabilityRegistry
from app.agents.runtime import AgentRuntime

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating, registering, and managing agent instances."""

    def __init__(self, runtime: AgentRuntime | None = None) -> None:
        self._runtime = runtime or AgentRuntime()
        self._templates: dict[str, type[BaseAgent]] = {}
        self._capabilities: dict[str, AgentCapability] = {}

    @property
    def runtime(self) -> AgentRuntime:
        return self._runtime

    def register_template(
        self,
        agent_class: type[BaseAgent],
        capability: AgentCapability | None = None,
    ) -> None:
        dummy = agent_class.__new__(agent_class)
        agent_id = getattr(dummy, "agent_id", agent_class.__name__)
        self._templates[agent_id] = agent_class
        if capability:
            self._capabilities[agent_id] = capability

    def create_and_register(
        self,
        agent_class: type[BaseAgent],
        capability: AgentCapability | None = None,
        **kwargs: Any,
    ) -> BaseAgent:
        agent = agent_class(**kwargs) if kwargs else agent_class()
        cap = capability or self._capabilities.get(agent.agent_id)
        self._runtime.register(agent, cap)
        return agent

    def create_from_template(
        self,
        agent_id: str,
        overrides: dict[str, Any] | None = None,
    ) -> BaseAgent | None:
        cls = self._templates.get(agent_id)
        if cls is None:
            logger.warning("Factory: no template for '%s'", agent_id)
            return None

        kwargs = dict(overrides or {})
        try:
            agent = cls(**kwargs)
        except TypeError:
            agent = cls()

        cap = self._capabilities.get(agent_id)
        self._runtime.register(agent, cap)
        return agent

    def register_all_builtins(self, **kwargs: Any) -> list[BaseAgent]:
        from app.agents.builtins import (
            CoderAgent,
            ExecutorAgent,
            MemoryAgent,
            PlannerAgent,
            ResearchAgent,
            ReviewerAgent,
        )

        builtins: list[tuple[type[BaseAgent], AgentCapability | None]] = [
            (PlannerAgent, AgentCapability(
                supported_intents=["planning", "decomposition"],
                supported_task_types=["plan", "decompose"],
                supported_tools=["goal_analysis", "task_decomposition", "dependency_mapping"],
                priority=3,
                concurrency_limit=3,
                execution_policy="sequential",
            )),
            (ResearchAgent, AgentCapability(
                supported_intents=["research", "search", "lookup"],
                supported_task_types=["research", "search", "analyze"],
                supported_tools=["memory_search", "document_lookup", "web_search"],
                priority=5,
                concurrency_limit=5,
                execution_policy="parallel",
            )),
            (CoderAgent, AgentCapability(
                supported_intents=["coding", "implementation", "write"],
                supported_task_types=["code", "implement", "refactor"],
                supported_tools=["file_read", "file_write", "code_search"],
                priority=4,
                concurrency_limit=3,
                execution_policy="exclusive",
            )),
            (ReviewerAgent, AgentCapability(
                supported_intents=["review", "validate", "check"],
                supported_task_types=["review", "validate", "audit"],
                supported_tools=["code_analysis", "quality_check"],
                priority=6,
                concurrency_limit=4,
                execution_policy="immediate",
            )),
            (MemoryAgent, AgentCapability(
                supported_intents=["memory", "recall", "store"],
                supported_task_types=["memory", "store", "retrieve"],
                supported_tools=["store_memory", "retrieve_memory", "search_memories"],
                priority=7,
                concurrency_limit=5,
                execution_policy="idempotent",
            )),
            (ExecutorAgent, AgentCapability(
                supported_intents=["execution", "run", "deploy"],
                supported_task_types=["execute", "run", "deploy"],
                supported_tools=["run_command", "execute_action", "dispatch_task"],
                priority=4,
                concurrency_limit=5,
                execution_policy="retryable",
            )),
        ]

        agents = []
        for agent_cls, cap in builtins:
            agent = agent_cls()
            self._runtime.register(agent, cap)
            agents.append(agent)

        logger.info("Factory: registered %d built-in agents", len(agents))
        return agents

    def get_template_ids(self) -> list[str]:
        return list(self._templates.keys())

    def to_dict(self) -> dict[str, Any]:
        return {
            "templates": list(self._templates.keys()),
            "runtime_agents": self._runtime.registry.list_agent_ids(),
        }
