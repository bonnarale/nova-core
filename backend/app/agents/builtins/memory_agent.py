"""MemoryAgent - manages persistent memory and context retrieval."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="memory",
    name="Memory Agent",
    role="memory",
    description="Manages long-term and short-term memory, stores and retrieves contextual information.",
    system_prompt="You are a memory management specialist. Store and retrieve information efficiently.",
    allowed_tools=["store_memory", "retrieve_memory", "search_memories", "forget_memory"],
    memory_scope="global",
    permissions={"can_read_all_memory": True, "can_write_all_memory": True},
    supported_models=["qwen2.5-coder:7b"],
)


class MemoryAgent(BaseAgent):
    """Agent that manages memory storage and retrieval."""

    def __init__(self) -> None:
        super().__init__(agent_id="memory")

    @property
    def definition(self) -> AgentDefinition:
        return _DEFINITION

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        goal = context.get("goal", task)
        memory_action = context.get("memory_action", "recall")

        memories = [
            {"key": f"context_{goal[:20]}", "value": f"Stored context for {goal[:40]}"},
        ]

        return {
            "agent": self.agent_id,
            "status": "completed",
            "action": memory_action,
            "memories": memories,
            "summary": f"Performed '{memory_action}' for: {goal[:60]}",
        }
