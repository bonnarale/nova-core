"""LLM-backed agent implementation."""

import json
import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent
from app.models.gateway import ModelGateway

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Answer the user's questions "
    "based on the conversation history and the current request."
)


class LLMAgent(BaseAgent):
    """Agent that delegates reasoning to a language model.

    The agent receives conversation history via the ``context`` dict
    (populated upstream by the route handler).  It builds the final
    message list as::

        [system prompt] + [conversation history]

    The current user message is already the last entry in the history,
    so it is **not** appended separately.
    """

    def __init__(
        self,
        agent_id: str,
        gateway: ModelGateway,
        model: str = "qwen2.5-coder:7b",
        system_prompt: str | None = None,
    ) -> None:
        super().__init__(agent_id)
        self._gateway = gateway
        self._model = model
        self._system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self._definition = AgentDefinition(
            agent_id=agent_id,
            name=agent_id.title(),
            role="assistant",
            description="General-purpose LLM-powered assistant agent.",
            system_prompt=self._system_prompt,
            allowed_tools=["chat", "reasoning"],
            supported_models=[model],
        )

    @property
    def definition(self) -> AgentDefinition:
        return self._definition

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        history = context.get("history", [])
        user_profile = context.get("user_profile", {})
        semantic_memories = context.get("semantic_memories", [])
        goals_data = context.get("goals", {})

        messages: list[dict[str, str]] = []
        messages.append({"role": "system", "content": self._system_prompt})

        if user_profile:
            profile_text = self._format_profile(user_profile)
            if profile_text:
                messages.append({"role": "system", "content": profile_text})

        if semantic_memories:
            messages.append({"role": "system", "content": self._format_memories(semantic_memories)})

        if goals_data:
            goals_text = self._format_goals(goals_data)
            if goals_text:
                messages.append({"role": "system", "content": goals_text})

        messages.extend(history)

        logger.info("=== MEMORY_AUDIT [LLMAgent] messages sent to gateway ===")
        logger.info("model=%s  messages=%d", self._model, len(messages))
        logger.info("messages=%s", json.dumps(messages, indent=2, ensure_ascii=False))

        response = await self._gateway.chat(
            model=self._model,
            messages=messages,
        )

        return {
            "agent": self.agent_id,
            "model": self._model,
            "response": response,
        }

    @staticmethod
    def _format_goals(goals_data: dict) -> str:
        """Format goals, next actions, and analysis into a system message fragment."""
        parts: list[str] = ["## Current Goals"]
        goals = goals_data.get("goals", [])
        if goals:
            for g in goals:
                status_mark = "✓" if g.get("progress", 0) >= 100 else "●" if g.get("status") == "active" else "✗" if g.get("status") == "blocked" else "○"
                parts.append(f"- [{status_mark}] (P{g.get('priority', 3)}/{g.get('progress', 0)}%) {g.get('title', '')}")
        else:
            parts.append("(no goals defined yet)")

        next_actions = goals_data.get("next_actions", [])
        if next_actions:
            parts.append("")
            parts.append("## Recommended Next Actions")
            for i, g in enumerate(next_actions, 1):
                parts.append(f"{i}. {g.get('title', '')} (priority {g.get('priority', 3)}, {g.get('progress', 0)}% complete)")

        analysis = goals_data.get("analysis", {})
        if analysis:
            parts.append("")
            parts.append("## Progress Overview")
            parts.append(f"- Total: {analysis.get('total', 0)} goals")
            parts.append(f"- Active: {analysis.get('active', 0)}")
            parts.append(f"- Blocked: {analysis.get('blocked', 0)}")
            parts.append(f"- Completed: {analysis.get('completed', 0)}")
            parts.append(f"- Average progress: {analysis.get('avg_progress', 0)}%")

        return "\n".join(parts)

    @staticmethod
    def _format_memories(memories: list[dict]) -> str:
        """Format semantic memories into a system message fragment."""
        parts: list[str] = ["## Relevant Past Memories"]
        for mem in memories:
            parts.append(f"- {mem.get('content', '')}")
        return "\n".join(parts)

    @staticmethod
    def _format_profile(profile: dict) -> str:
        """Format a user profile dict into a system message fragment."""
        parts: list[str] = ["## User Profile"]
        if profile.get("name"):
            parts.append(f"Name: {profile['name']}")
        if profile.get("bio"):
            parts.append(f"Bio: {profile['bio']}")
        prefs = profile.get("preferences")
        if prefs:
            parts.append(f"Preferences: {prefs}")
        goals = profile.get("goals")
        if goals:
            parts.append(f"Goals: {goals}")
        facts = profile.get("facts")
        if facts:
            parts.append(f"Known facts: {facts}")
        if len(parts) == 1:
            return ""
        return "\n".join(parts)
