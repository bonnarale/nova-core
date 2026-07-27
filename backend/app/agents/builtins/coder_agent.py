"""CoderAgent — LLM-powered code generation agent."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent
from app.models.gateway import ModelGateway

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="coder",
    name="Coder Agent",
    role="coder",
    description="Generates code using LLM capabilities based on task requirements.",
    system_prompt=(
        "You are a code generation agent. Given a coding task, generate the "
        "appropriate code. Return your response as JSON with the following structure:\n"
        '  {"code": "the generated code", "language": "programming language", '
        '"summary": "brief summary"}\n'
        "Always respond with valid JSON."
    ),
    allowed_tools=[],
    memory_scope="session",
    permissions={},
    supported_models=["qwen2.5-coder:7b"],
)


class CoderAgent(BaseAgent):
    """Agent that generates code using LLM."""

    def __init__(
        self,
        gateway: ModelGateway,
        model: str = "qwen2.5-coder:7b",
    ) -> None:
        super().__init__(agent_id="coder")
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
        """Generate code using LLM.

        Args:
            task: The coding task description.
            context: Runtime context.

        Returns:
            Dict with agent, status, code, language, summary.
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
                code_data = json.loads(content)
                code = code_data.get("code", content)
                language = code_data.get("language", "unknown")
                summary = code_data.get("summary", "Code generated successfully")
            except (json.JSONDecodeError, AttributeError):
                code = content
                language = "unknown"
                summary = "Code generated from LLM response"

            return {
                "agent": self.agent_id,
                "status": "completed",
                "code": code,
                "language": language,
                "summary": summary,
            }

        except Exception as exc:
            logger.exception("CoderAgent: LLM call failed")
            return {
                "agent": self.agent_id,
                "status": "failed",
                "error": str(exc),
                "code": "",
                "language": "unknown",
                "summary": f"Code generation failed: {exc}",
            }