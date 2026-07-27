"""ExecutorAgent — LLM-powered task execution agent."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent
from app.models.gateway import ModelGateway

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="executor",
    name="Executor Agent",
    role="executor",
    description="Executes tasks using LLM reasoning and returns structured results.",
    system_prompt=(
        "You are an execution agent. Given a task, perform it using your capabilities "
        "and return the result. Return your response as JSON with the following structure:\n"
        '  {"result": "the execution result", "summary": "brief summary of what was done"}\n'
        "Always respond with valid JSON."
    ),
    allowed_tools=[],
    memory_scope="session",
    permissions={},
    supported_models=["qwen2.5-coder:7b"],
)


class ExecutorAgent(BaseAgent):
    """Agent that executes tasks using LLM reasoning."""

    def __init__(
        self,
        gateway: ModelGateway,
        model: str = "qwen2.5-coder:7b",
    ) -> None:
        super().__init__(agent_id="executor")
        self._gateway = gateway
        self._model = model

    @property
    def definition(self) -> AgentDefinition:
        return _DEFINITION

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a task using LLM.

        Args:
            task: The task to execute.
            context: Runtime context.

        Returns:
            Dict with agent, status, result, summary.
        """
        history = context.get("history", [])

        messages: list[dict[str, str]] = [
            {"role": "system", "content": _DEFINITION.system_prompt},
        ]
        messages.extend(history)
        if not history or history[-1].get("content") != task:
            messages.append({"role": "user", "content": task})

        try:
            response = await self._gateway.chat(
                model=self._model,
                messages=messages,
            )

            content = ""
            if isinstance(response, dict):
                choices = response.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")

            try:
                result_data = json.loads(content)
                result = result_data.get("result", content)
                summary = result_data.get("summary", "Task executed successfully")
            except (json.JSONDecodeError, AttributeError):
                result = content
                summary = "Task executed from LLM response"

            return {
                "agent": self.agent_id,
                "status": "completed",
                "result": result,
                "summary": summary,
            }

        except Exception as exc:
            logger.exception("ExecutorAgent: LLM call failed")
            return {
                "agent": self.agent_id,
                "status": "failed",
                "error": str(exc),
                "result": "",
                "summary": f"Execution failed: {exc}",
            }