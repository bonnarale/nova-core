"""End-to-end test for task execution flow: chat → task created → agent executes → result stored."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routes.nova_web import router


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    """Reset module-level singletons so each test gets fresh state."""
    import app.api.v1.routes.nova_web as mod
    mod._components = None
    yield
    mod._components = None


@pytest.fixture()
def client_with_full_stack() -> TestClient:
    """Create a test client with mocked dependencies for full flow."""
    app = FastAPI()
    app.include_router(router)

    # Mock kernel
    mock_kernel = AsyncMock()
    mock_kernel.run_agent = AsyncMock(return_value={
        "response": {"message": {"content": "Task created successfully."}},
    })
    app.state.kernel = mock_kernel

    # Mock conversation memory
    mock_memory = AsyncMock()
    mock_memory.ensure_session = AsyncMock()
    mock_memory.add_message = AsyncMock()
    mock_memory.get_history = AsyncMock(return_value=[])
    app.state.memory = mock_memory

    # Mock semantic memory
    mock_semantic_memory = AsyncMock()
    mock_semantic_memory.search = AsyncMock(return_value=[])
    mock_semantic_memory.store = AsyncMock()
    app.state.semantic_memory = mock_semantic_memory

    # Mock cognitive engine that returns CREATE_TASK with task_id
    mock_cognitive_engine = AsyncMock()
    task_id = str(uuid4())
    mock_state = MagicMock()
    mock_state.decision = MagicMock()
    mock_state.decision.action = "CREATE_TASK"
    mock_state.decision.agent_id = None
    mock_state.execution_result = {
        "created_task": {"id": task_id, "goal": "Build a web app"},
        "assigned_agent": "executor",
        "task_id": task_id,
    }
    mock_state.error = None
    mock_cognitive_engine.process = AsyncMock(return_value=mock_state)
    app.state.cognitive_engine = mock_cognitive_engine

    return TestClient(app, raise_server_exceptions=False)


class TestE2EExecution:
    """End-to-end tests for task execution flow."""

    def test_chat_returns_task_id(self, client_with_full_stack: TestClient) -> None:
        """Chat endpoint should return a task_id when cognitive engine creates a task."""
        response = client_with_full_stack.post(
            "/nova-web/chat",
            json={"message": "Build a web app", "session_id": "test-session"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["task_id"] is not None

    def test_cognitive_engine_called(self, client_with_full_stack: TestClient) -> None:
        """Cognitive engine should be called with the message."""
        client_with_full_stack.post(
            "/nova-web/chat",
            json={"message": "Build a web app", "session_id": "test-session"},
        )
        mock_cognitive_engine = client_with_full_stack.app.state.cognitive_engine
        mock_cognitive_engine.process.assert_called_once()

    def test_chat_returns_response_field(self, client_with_full_stack: TestClient) -> None:
        """Response should include response field."""
        response = client_with_full_stack.post(
            "/nova-web/chat",
            json={"message": "Build a web app", "session_id": "test-session"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data


class TestAgentExecution:
    """Test that LLM agents can execute tasks end-to-end."""

    @pytest.fixture
    def mock_gateway(self):
        """Mock ModelGateway."""
        gateway = AsyncMock()
        gateway.chat = AsyncMock(return_value={
            "choices": [{"message": {"content": '{"result": "done", "summary": "completed"}'}}],
            "model": "qwen2.5-coder:7b",
        })
        return gateway

    @pytest.mark.asyncio
    async def test_planner_agent_full_flow(self, mock_gateway):
        """PlannerAgent should create a plan from objective."""
        from app.agents.builtins.planner_agent import PlannerAgent
        agent = PlannerAgent(gateway=mock_gateway)
        result = await agent.execute(
            task="Create a plan for building a REST API",
            context={"history": []},
        )
        assert result["agent"] == "planner"
        assert result["status"] == "completed"
        assert "plan" in result
        assert "steps" in result

    @pytest.mark.asyncio
    async def test_executor_agent_full_flow(self, mock_gateway):
        """ExecutorAgent should execute a task."""
        from app.agents.builtins.executor_agent import ExecutorAgent
        agent = ExecutorAgent(gateway=mock_gateway)
        result = await agent.execute(
            task="Execute the deployment script",
            context={"history": []},
        )
        assert result["agent"] == "executor"
        assert result["status"] == "completed"
        assert "result" in result

    @pytest.mark.asyncio
    async def test_coder_agent_full_flow(self, mock_gateway):
        """CoderAgent should generate code."""
        mock_gateway.chat.return_value = {
            "choices": [{"message": {"content": '{"code": "print(42)", "language": "python", "summary": "Simple program"}'}}],
            "model": "qwen2.5-coder:7b",
        }
        from app.agents.builtins.coder_agent import CoderAgent
        agent = CoderAgent(gateway=mock_gateway)
        result = await agent.execute(
            task="Write a program to print 42",
            context={"history": []},
        )
        assert result["agent"] == "coder"
        assert result["status"] == "completed"
        assert result["code"] == "print(42)"
        assert result["language"] == "python"

    @pytest.mark.asyncio
    async def test_research_agent_full_flow(self, mock_gateway):
        """ResearchAgent should conduct research."""
        from app.agents.builtins.research_agent import ResearchAgent
        agent = ResearchAgent(gateway=mock_gateway)
        result = await agent.execute(
            task="Research Python web frameworks",
            context={"history": []},
        )
        assert result["agent"] == "researcher"
        assert result["status"] == "completed"
        assert "findings" in result
        assert "sources" in result