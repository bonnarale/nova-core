"""CoderAgent - writes and modifies code."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="coder",
    name="Coder Agent",
    role="coder",
    description="Writes, reviews, and modifies source code across the codebase.",
    system_prompt="You are a skilled software engineer. Write clean, maintainable code.",
    allowed_tools=["file_read", "file_write", "code_search", "code_review", "run_tests"],
    memory_scope="session",
    permissions={"can_read_files": True, "can_write_files": True, "can_execute_commands": False},
    supported_models=["qwen2.5-coder:7b"],
)


class CoderAgent(BaseAgent):
    """Agent that writes code as part of task execution."""

    def __init__(self) -> None:
        super().__init__(agent_id="coder")

    @property
    def definition(self) -> AgentDefinition:
        return _DEFINITION

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        goal = context.get("goal", task)

        return {
            "agent": self.agent_id,
            "status": "completed",
            "code": f"# Implementation for: {goal[:60]}\n",
            "language": "python",
            "files_modified": [],
            "summary": f"Generated code for: {goal[:60]}",
        }
