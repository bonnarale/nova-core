"""PlannerAgent — LLM-powered planning agent."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent
from app.models.gateway import ModelGateway

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="planner",
    name="Planner Agent",
    role="planner",
    description="Creates structured execution plans from high-level objectives using LLM reasoning.",
    system_prompt=(
        "You are a planning agent. Given a high-level objective, create a detailed "
        "execution plan with concrete steps. Return your plan as JSON with the "
        "following structure:\n"
        '  {"plan": "overview of the plan", "steps": ["step 1", "step 2", ...], '
        '"summary": "brief summary"}\n'
        "Always respond with valid JSON."
    ),
    allowed_tools=[],
    memory_scope="session",
    permissions={},
    supported_models=["qwen2.5-coder:7b"],
)


class PlannerAgent(BaseAgent):
    """Agent that creates execution plans using LLM reasoning."""

    def __init__(
        self,
        gateway: ModelGateway,
        model: str = "qwen2.5-coder:7b",
    ) -> None:
        super().__init__(agent_id="planner")
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
        """Execute a planning task using LLM.

        Args:
            task: The objective to plan for.
            context: Runtime context (may include history).

        Returns:
            Dict with agent, status, plan, steps, summary.
        """
        history = context.get("history", [])

        messages: list[dict[str, str]] = [
            {"role": "system", "content": _DEFINITION.system_prompt},
        ]
        messages.extend(history)
        # Add the task as user message if not already in history
        if not history or history[-1].get("content") != task:
            messages.append({"role": "user", "content": task})

        try:
            response = await self._gateway.chat(
                model=self._model,
                messages=messages,
            )

            # Extract content from response
            content = ""
            if isinstance(response, dict):
                choices = response.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")

            # Try to parse as JSON
            try:
                plan_data = json.loads(content)
                plan = plan_data.get("plan", content)
                steps = plan_data.get("steps", [])
                summary = plan_data.get("summary", "Plan created successfully")
            except (json.JSONDecodeError, AttributeError):
                # If not valid JSON, treat entire response as plan
                plan = content
                steps = [line.strip() for line in content.split("\n") if line.strip()]
                summary = "Plan created from LLM response"

            return {
                "agent": self.agent_id,
                "status": "completed",
                "plan": plan,
                "steps": steps,
                "summary": summary,
            }

        except Exception as exc:
            logger.exception("PlannerAgent: LLM call failed")
            return {
                "agent": self.agent_id,
                "status": "failed",
                "error": str(exc),
                "plan": "",
                "steps": [],
                "summary": f"Planning failed: {exc}",
            }