"""LLM-backed agent implementation."""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
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

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        history = context.get("history", [])

        messages: list[dict[str, str]] = []
        messages.append({"role": "system", "content": self._system_prompt})
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
