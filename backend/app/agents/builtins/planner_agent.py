"""PlannerAgent - decomposes goals into actionable plans and subtasks."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="planner",
    name="Planner Agent",
    role="planner",
    description="Decomposes high-level goals into structured plans and orchestrates their execution.",
    system_prompt="You are a strategic planner. Break down complex goals into manageable steps.",
    allowed_tools=["goal_analysis", "task_decomposition", "dependency_mapping"],
    memory_scope="session",
    permissions={"can_create_tasks": True, "can_delegate": True},
    supported_models=["qwen2.5-coder:7b"],
)


class PlannerAgent(BaseAgent):
    """Agent that decomposes goals into plans and creates subtasks."""

    def __init__(self) -> None:
        super().__init__(agent_id="planner")

    @property
    def definition(self) -> AgentDefinition:
        return _DEFINITION

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        goal = context.get("goal", task)
        existing_plan = context.get("plan")

        if existing_plan:
            return {
                "agent": self.agent_id,
                "status": "completed",
                "plan": existing_plan,
                "steps": existing_plan.get("steps", []),
                "summary": f"Plan already exists for goal: {goal[:60]}",
            }

        steps = [
            f"Research requirements for: {goal[:50]}",
            f"Design solution architecture for: {goal[:50]}",
            f"Implement core components for: {goal[:50]}",
            f"Review and validate: {goal[:50]}",
            f"Deploy and verify: {goal[:50]}",
        ]

        plan = {
            "goal": goal,
            "steps": steps,
            "dependencies": [],
            "estimated_complexity": "medium",
        }

        return {
            "agent": self.agent_id,
            "status": "completed",
            "plan": plan,
            "steps": steps,
            "summary": f"Created {len(steps)}-step plan for: {goal[:60]}",
        }
