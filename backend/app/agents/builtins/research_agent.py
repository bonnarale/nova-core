"""ResearchAgent - gathers information and context for tasks."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="researcher",
    name="Research Agent",
    role="researcher",
    description="Gathers information, context, and data needed to complete tasks.",
    system_prompt="You are a research specialist. Find relevant information and summarize findings.",
    allowed_tools=["memory_search", "document_lookup", "web_search", "data_analysis"],
    memory_scope="user",
    permissions={"can_read_memory": True, "can_search": True},
    supported_models=["qwen2.5-coder:7b"],
)


class ResearchAgent(BaseAgent):
    """Agent that researches information for tasks."""

    def __init__(self) -> None:
        super().__init__(agent_id="researcher")

    @property
    def definition(self) -> AgentDefinition:
        return _DEFINITION

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        goal = context.get("goal", task)
        existing_data = context.get("research_data")

        findings = {
            f"Finding about {goal[:30]}": f"Relevant context gathered for task execution."
        }

        return {
            "agent": self.agent_id,
            "status": "completed",
            "findings": findings,
            "sources": ["memory", "context"],
            "summary": f"Gathered {len(findings)} findings for: {goal[:60]}",
        }
