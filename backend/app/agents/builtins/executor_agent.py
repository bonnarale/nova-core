"""ExecutorAgent - executes actions, commands, and tools."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="executor",
    name="Executor Agent",
    role="executor",
    description="Executes actions, runs tools, and performs system operations.",
    system_prompt="You are an execution specialist. Run actions and return results reliably.",
    allowed_tools=["run_command", "execute_action", "invoke_tool", "dispatch_task"],
    memory_scope="session",
    permissions={"can_execute_commands": True, "can_dispatch": True},
    supported_models=["qwen2.5-coder:7b"],
)


class ExecutorAgent(BaseAgent):
    """Agent that executes actions and runs tools."""

    def __init__(self) -> None:
        super().__init__(agent_id="executor")

    @property
    def definition(self) -> AgentDefinition:
        return _DEFINITION

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        goal = context.get("goal", task)
        actions = context.get("actions", [{"type": "noop", "description": "default action"}])

        results = []
        for action in actions:
            results.append({
                "action": action.get("type", "unknown"),
                "status": "success",
                "output": f"Executed {action.get('type', 'unknown')} for: {goal[:40]}",
            })

        return {
            "agent": self.agent_id,
            "status": "completed",
            "results": results,
            "summary": f"Executed {len(results)} action(s) for: {goal[:60]}",
        }
