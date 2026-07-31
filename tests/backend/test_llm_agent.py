"""Tests for LLMAgent."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.llm_agent import DEFAULT_SYSTEM_PROMPT, LLMAgent


@pytest.fixture
def gateway():
    return MagicMock()


@pytest.fixture
def agent(gateway):
    return LLMAgent(
        agent_id="test-agent",
        gateway=gateway,
        model="test-model",
        system_prompt="You are a test assistant.",
    )


@pytest.fixture
def agent_default_prompt(gateway):
    return LLMAgent(
        agent_id="default-agent",
        gateway=gateway,
    )


class TestLLMAgentInit:
    def test_default_system_prompt(self, agent_default_prompt):
        assert agent_default_prompt._system_prompt == DEFAULT_SYSTEM_PROMPT

    def test_custom_system_prompt(self, agent):
        assert agent._system_prompt == "You are a test assistant."

    def test_agent_id(self, agent):
        assert agent.agent_id == "test-agent"


class TestLLMAgentExecute:
    @pytest.mark.asyncio
    async def test_builds_system_prompt_and_history(self, agent, gateway):
        gateway.chat = AsyncMock(
            return_value={"message": {"content": "hello back"}}
        )
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]

        result = await agent.execute("Hi", {"history": history})

        gateway.chat.assert_awaited_once_with(
            model="test-model",
            messages=[
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
            ],
        )
        assert result["agent"] == "test-agent"
        assert result["model"] == "test-model"

    @pytest.mark.asyncio
    async def test_empty_history_fallback(self, agent, gateway):
        gateway.chat = AsyncMock(
            return_value={"message": {"content": "ok"}}
        )

        result = await agent.execute("Hello", {"history": []})

        gateway.chat.assert_awaited_once_with(
            model="test-model",
            messages=[
                {"role": "system", "content": "You are a test assistant."},
            ],
        )
        assert result["agent"] == "test-agent"

    @pytest.mark.asyncio
    async def test_forwards_gateway_response_unchanged(self, agent, gateway):
        raw_response = {
            "message": {"content": "assistant reply", "role": "assistant"},
            "model": "test-model",
        }
        gateway.chat = AsyncMock(return_value=raw_response)

        result = await agent.execute("hello", {"history": []})

        assert result["response"] is raw_response

    @pytest.mark.asyncio
    async def test_default_system_prompt_used_when_not_provided(
        self, agent_default_prompt, gateway
    ):
        gateway.chat = AsyncMock(
            return_value={"message": {"content": "ok"}}
        )

        await agent_default_prompt.execute("test", {"history": []})

        gateway.chat.assert_awaited_once()
        messages = gateway.chat.call_args[1]["messages"]
        assert messages[0] == {
            "role": "system",
            "content": DEFAULT_SYSTEM_PROMPT,
        }

    @pytest.mark.asyncio
    async def test_history_not_modified_by_agent(self, agent, gateway):
        gateway.chat = AsyncMock(
            return_value={"message": {"content": "ok"}}
        )
        original_history = [
            {"role": "user", "content": "first"},
        ]
        history_copy = list(original_history)

        await agent.execute("first", {"history": original_history})

        assert original_history == history_copy
