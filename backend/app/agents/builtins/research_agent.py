"""ResearchAgent — LLM-powered research agent."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent
from app.models.gateway import ModelGateway

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="researcher",
    name="Research Agent",
    role="researcher",
    description="Conducts research using LLM capabilities and returns findings with sources.",
    system_prompt=(
        "You are a research agent. Given a research topic, gather and analyze "
        "information. Return your response as JSON with the following structure:\n"
        '  {"findings": "detailed research findings", "sources": ["source1", ...], '
        '"summary": "brief summary"}\n'
        "Always respond with valid JSON."
    ),
    allowed_tools=[],
    memory_scope="session",
    permissions={},
    supported_models=["qwen2.5-coder:7b"],
)


class ResearchAgent(BaseAgent):
    """Agent that conducts research using LLM."""

    def __init__(
        self,
        gateway: ModelGateway,
        model: str = "qwen2.5-coder:7b",
    ) -> None:
        super().__init__(agent_id="researcher")
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
        """Conduct research using LLM.

        Args:
            task: The research topic.
            context: Runtime context.

        Returns:
            Dict with agent, status, findings, sources, summary.
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
                research_data = json.loads(content)
                findings = research_data.get("findings", content)
                sources = research_data.get("sources", [])
                summary = research_data.get("summary", "Research completed successfully")
            except (json.JSONDecodeError, AttributeError):
                findings = content
                sources = []
                summary = "Research completed from LLM response"

            return {
                "agent": self.agent_id,
                "status": "completed",
                "findings": findings,
                "sources": sources,
                "summary": summary,
            }

        except Exception as exc:
            logger.exception("ResearchAgent: LLM call failed")
            return {
                "agent": self.agent_id,
                "status": "failed",
                "error": str(exc),
                "findings": "",
                "sources": [],
                "summary": f"Research failed: {exc}",
            }