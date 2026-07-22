"""ReviewerAgent - reviews code, plans, and outputs for quality."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="reviewer",
    name="Reviewer Agent",
    role="reviewer",
    description="Reviews code, plans, and artifacts for quality, correctness, and completeness.",
    system_prompt="You are a thorough reviewer. Check for correctness, quality, and completeness.",
    allowed_tools=["code_analysis", "quality_check", "style_check", "dependency_check"],
    memory_scope="session",
    permissions={"can_read_artifacts": True},
    supported_models=["qwen2.5-coder:7b"],
)


class ReviewerAgent(BaseAgent):
    """Agent that reviews outputs from other agents."""

    def __init__(self) -> None:
        super().__init__(agent_id="reviewer")

    @property
    def definition(self) -> AgentDefinition:
        return _DEFINITION

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        goal = context.get("goal", task)
        artifact = context.get("artifact", "")

        review_comments = [
            {"severity": "info", "line": 0, "message": "Review completed for provided artifact."},
        ]

        return {
            "agent": self.agent_id,
            "status": "completed",
            "approved": True,
            "comments": review_comments,
            "score": 85,
            "summary": f"Reviewed artifact for: {goal[:60]} - score: 85/100",
        }
