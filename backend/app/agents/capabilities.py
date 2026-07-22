"""Agent capability model and dynamic capability registry."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentCapability:
    """Describes what an agent can do, its constraints, and routing hints."""

    supported_intents: list[str] = field(default_factory=list)
    supported_task_types: list[str] = field(default_factory=list)
    supported_tools: list[str] = field(default_factory=list)
    priority: int = 5
    concurrency_limit: int = 5
    execution_policy: str = "immediate"
    confidence_threshold: float = 0.0
    estimated_cost_per_task: float = 0.0
    estimated_duration_seconds: float = 0.0
    tags: list[str] = field(default_factory=list)

    def matches_intent(self, intent: str) -> bool:
        intent_lower = intent.lower()
        return any(intent_lower == s.lower() for s in self.supported_intents)

    def matches_task_type(self, task_type: str) -> bool:
        task_lower = task_type.lower()
        return any(task_lower == s.lower() for s in self.supported_task_types)

    def matches_tool(self, tool: str) -> bool:
        tool_lower = tool.lower()
        return any(tool_lower == s.lower() for s in self.supported_tools)

    def has_tag(self, tag: str) -> bool:
        tag_lower = tag.lower()
        return any(tag_lower == t.lower() for t in self.tags)

    def to_dict(self) -> dict[str, Any]:
        return {
            "supported_intents": list(self.supported_intents),
            "supported_task_types": list(self.supported_task_types),
            "supported_tools": list(self.supported_tools),
            "priority": self.priority,
            "concurrency_limit": self.concurrency_limit,
            "execution_policy": self.execution_policy,
            "confidence_threshold": self.confidence_threshold,
            "estimated_cost_per_task": self.estimated_cost_per_task,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "tags": list(self.tags),
        }


class CapabilityRegistry:
    """Dynamic registry that maps agent IDs to their capabilities.

    Supports querying by intent, task type, tool, and tag.
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, AgentCapability] = {}

    def register(self, agent_id: str, capability: AgentCapability) -> None:
        self._capabilities[agent_id] = capability
        logger.debug("CapabilityRegistry: registered %s", agent_id)

    def unregister(self, agent_id: str) -> None:
        self._capabilities.pop(agent_id, None)

    def get(self, agent_id: str) -> AgentCapability | None:
        return self._capabilities.get(agent_id)

    def find_by_intent(self, intent: str) -> list[tuple[str, AgentCapability]]:
        return [
            (aid, cap) for aid, cap in self._capabilities.items()
            if cap.matches_intent(intent)
        ]

    def find_by_task_type(self, task_type: str) -> list[tuple[str, AgentCapability]]:
        return [
            (aid, cap) for aid, cap in self._capabilities.items()
            if cap.matches_task_type(task_type)
        ]

    def find_by_tool(self, tool: str) -> list[tuple[str, AgentCapability]]:
        return [
            (aid, cap) for aid, cap in self._capabilities.items()
            if cap.matches_tool(tool)
        ]

    def find_by_tag(self, tag: str) -> list[tuple[str, AgentCapability]]:
        return [
            (aid, cap) for aid, cap in self._capabilities.items()
            if cap.has_tag(tag)
        ]

    def find_by_policy(self, policy: str) -> list[tuple[str, AgentCapability]]:
        return [
            (aid, cap) for aid, cap in self._capabilities.items()
            if cap.execution_policy.lower() == policy.lower()
        ]

    def find_capable(
        self,
        intent: str | None = None,
        task_type: str | None = None,
        tool: str | None = None,
        tags: list[str] | None = None,
    ) -> list[tuple[str, AgentCapability]]:
        results: dict[str, AgentCapability] = {}

        if intent:
            for aid, cap in self.find_by_intent(intent):
                results[aid] = cap
        if task_type:
            for aid, cap in self.find_by_task_type(task_type):
                results[aid] = cap
        if tool:
            for aid, cap in self.find_by_tool(tool):
                results[aid] = cap
        if tags:
            for tag in tags:
                for aid, cap in self.find_by_tag(tag):
                    results[aid] = cap

        if not results:
            results = dict(self._capabilities.items())

        return sorted(results.items(), key=lambda x: x[1].priority)

    def list_all(self) -> dict[str, AgentCapability]:
        return dict(self._capabilities)

    def list_agent_ids(self) -> list[str]:
        return list(self._capabilities.keys())

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return {aid: cap.to_dict() for aid, cap in self._capabilities.items()}
