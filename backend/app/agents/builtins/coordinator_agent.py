"""CoordinatorAgent - orchestrates multi-agent collaboration."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="coordinator",
    name="Coordinator Agent",
    role="coordinator",
    description="Orchestrates multi-agent workflows, delegates subtasks, and aggregates results.",
    system_prompt=(
        "You are a coordinator. Break down complex tasks, delegate to the "
        "right agents, and synthesize results into a coherent output."
    ),
    allowed_tools=[
        "delegation", "aggregation", "task_tracking", "result_synthesis",
        "parallel_orchestration", "arbitration",
    ],
    memory_scope="session",
    permissions={
        "can_create_tasks": True,
        "can_delegate": True,
        "can_coordinate": True,
        "can_cancel": True,
    },
    supported_models=["qwen2.5-coder:7b"],
)


class CoordinatorAgent(BaseAgent):
    """Agent that coordinates multi-agent workflows."""

    def __init__(self) -> None:
        super().__init__(agent_id="coordinator")

    @property
    def definition(self) -> AgentDefinition:
        return _DEFINITION

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        goal = context.get("goal", task)
        pattern = context.get("pattern", "sequential")
        steps = context.get("steps", [])

        if steps:
            summary = (
                f"Coordinated {len(steps)} steps using '{pattern}' pattern "
                f"for: {goal[:60]}"
            )
        else:
            steps = [
                {"agent": "researcher", "task": f"Research: {goal[:50]}"},
                {"agent": "coder", "task": f"Implement: {goal[:50]}"},
                {"agent": "reviewer", "task": f"Review: {goal[:50]}"},
            ]
            summary = (
                f"Created default 3-step coordination plan for: {goal[:60]}"
            )

        return {
            "agent": self.agent_id,
            "status": "completed",
            "pattern": pattern,
            "steps": steps,
            "summary": summary,
        }
