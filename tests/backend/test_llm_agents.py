"""Tests for LLM-powered builtin agents with mocked gateway."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any


class TestPlannerAgent:
    """Tests for PlannerAgent."""

    @pytest.fixture
    def mock_gateway(self):
        """Mock ModelGateway."""
        gateway = AsyncMock()
        gateway.chat = AsyncMock(return_value={
            "choices": [{"message": {"content": "Plan: 1. Step one\n2. Step two"}}],
            "model": "qwen2.5-coder:7b",
        })
        return gateway

    @pytest.fixture
    def agent(self, mock_gateway):
        """Create PlannerAgent with mocked gateway."""
        from app.agents.builtins.planner_agent import PlannerAgent
        return PlannerAgent(gateway=mock_gateway)

    @pytest.mark.asyncio
    async def test_execute_returns_plan(self, agent, mock_gateway):
        """PlannerAgent should return a plan with steps."""
        result = await agent.execute(
            task="Create a plan for building a web app",
            context={"history": []},
        )
        assert result["agent"] == "planner"
        assert result["status"] == "completed"
        assert "plan" in result
        assert "steps" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_execute_calls_gateway(self, agent, mock_gateway):
        """PlannerAgent should call gateway.chat with proper messages."""
        await agent.execute(
            task="Create a plan",
            context={"history": [{"role": "user", "content": "Hello"}]},
        )
        mock_gateway.chat.assert_called_once()
        call_args = mock_gateway.chat.call_args
        assert call_args.kwargs["model"] == "qwen2.5-coder:7b"
        messages = call_args.kwargs["messages"]
        assert len(messages) >= 2  # system + history
        assert messages[0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_execute_handles_llm_error(self, mock_gateway):
        """PlannerAgent should handle LLM errors gracefully."""
        mock_gateway.chat.side_effect = RuntimeError("LLM unavailable")
        from app.agents.builtins.planner_agent import PlannerAgent
        agent = PlannerAgent(gateway=mock_gateway)
        result = await agent.execute(task="Plan", context={})
        assert result["status"] == "failed"
        assert "error" in result


class TestExecutorAgent:
    """Tests for ExecutorAgent."""

    @pytest.fixture
    def mock_gateway(self):
        """Mock ModelGateway."""
        gateway = AsyncMock()
        gateway.chat = AsyncMock(return_value={
            "choices": [{"message": {"content": "Task executed successfully"}}],
            "model": "qwen2.5-coder:7b",
        })
        return gateway

    @pytest.fixture
    def agent(self, mock_gateway):
        """Create ExecutorAgent with mocked gateway."""
        from app.agents.builtins.executor_agent import ExecutorAgent
        return ExecutorAgent(gateway=mock_gateway)

    @pytest.mark.asyncio
    async def test_execute_returns_result(self, agent, mock_gateway):
        """ExecutorAgent should return execution result."""
        result = await agent.execute(
            task="Execute this task",
            context={"history": []},
        )
        assert result["agent"] == "executor"
        assert result["status"] == "completed"
        assert "result" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_execute_calls_gateway(self, agent, mock_gateway):
        """ExecutorAgent should call gateway.chat."""
        await agent.execute(task="Execute", context={})
        mock_gateway.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_handles_llm_error(self, mock_gateway):
        """ExecutorAgent should handle LLM errors gracefully."""
        mock_gateway.chat.side_effect = RuntimeError("LLM error")
        from app.agents.builtins.executor_agent import ExecutorAgent
        agent = ExecutorAgent(gateway=mock_gateway)
        result = await agent.execute(task="Execute", context={})
        assert result["status"] == "failed"


class TestCoderAgent:
    """Tests for CoderAgent."""

    @pytest.fixture
    def mock_gateway(self):
        """Mock ModelGateway."""
        gateway = AsyncMock()
        gateway.chat = AsyncMock(return_value={
            "choices": [{"message": {"content": "```python\nprint('hello')\n```"}}],
            "model": "qwen2.5-coder:7b",
        })
        return gateway

    @pytest.fixture
    def agent(self, mock_gateway):
        """Create CoderAgent with mocked gateway."""
        from app.agents.builtins.coder_agent import CoderAgent
        return CoderAgent(gateway=mock_gateway)

    @pytest.mark.asyncio
    async def test_execute_returns_code(self, agent, mock_gateway):
        """CoderAgent should return generated code."""
        result = await agent.execute(
            task="Write a hello world program",
            context={"history": []},
        )
        assert result["agent"] == "coder"
        assert result["status"] == "completed"
        assert "code" in result
        assert "language" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_execute_calls_gateway(self, agent, mock_gateway):
        """CoderAgent should call gateway.chat."""
        await agent.execute(task="Write code", context={})
        mock_gateway.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_handles_llm_error(self, mock_gateway):
        """CoderAgent should handle LLM errors gracefully."""
        mock_gateway.chat.side_effect = RuntimeError("LLM error")
        from app.agents.builtins.coder_agent import CoderAgent
        agent = CoderAgent(gateway=mock_gateway)
        result = await agent.execute(task="Write code", context={})
        assert result["status"] == "failed"


class TestResearchAgent:
    """Tests for ResearchAgent."""

    @pytest.fixture
    def mock_gateway(self):
        """Mock ModelGateway."""
        gateway = AsyncMock()
        gateway.chat = AsyncMock(return_value={
            "choices": [{"message": {"content": "Research findings: ..."}}],
            "model": "qwen2.5-coder:7b",
        })
        return gateway

    @pytest.fixture
    def agent(self, mock_gateway):
        """Create ResearchAgent with mocked gateway."""
        from app.agents.builtins.research_agent import ResearchAgent
        return ResearchAgent(gateway=mock_gateway)

    @pytest.mark.asyncio
    async def test_execute_returns_findings(self, agent, mock_gateway):
        """ResearchAgent should return research findings."""
        result = await agent.execute(
            task="Research Python frameworks",
            context={"history": []},
        )
        assert result["agent"] == "researcher"
        assert result["status"] == "completed"
        assert "findings" in result
        assert "sources" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_execute_calls_gateway(self, agent, mock_gateway):
        """ResearchAgent should call gateway.chat."""
        await agent.execute(task="Research", context={})
        mock_gateway.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_handles_llm_error(self, mock_gateway):
        """ResearchAgent should handle LLM errors gracefully."""
        mock_gateway.chat.side_effect = RuntimeError("LLM error")
        from app.agents.builtins.research_agent import ResearchAgent
        agent = ResearchAgent(gateway=mock_gateway)
        result = await agent.execute(task="Research", context={})
        assert result["status"] == "failed"