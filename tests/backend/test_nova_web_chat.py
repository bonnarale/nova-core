"""Integration tests for NOVA Web Chat endpoint."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture(autouse=True)
def mock_app_state():
    """Mock all app.state components needed by the chat endpoint."""
    kernel = AsyncMock()
    kernel.run_agent = AsyncMock(return_value={
        "response": "Test response",
        "actions_taken": [],
        "objectives": [],
        "projects": [],
        "tasks": [],
        "approval_required": False,
    })

    memory = AsyncMock()
    memory.ensure_session = AsyncMock()
    memory.add_message = AsyncMock()
    memory.get_history = AsyncMock(return_value=[
        {"role": "user", "content": "Hello"},
    ])

    semantic_memory = AsyncMock()
    semantic_memory.search = AsyncMock(return_value=[])
    semantic_memory.store = AsyncMock()

    cognitive_engine = AsyncMock()
    cognitive_engine.process = AsyncMock(return_value=MagicMock(
        decision=MagicMock(action="ROUTE_TO_KERNEL"),
    ))

    app.state.kernel = kernel
    app.state.memory = memory
    app.state.semantic_memory = semantic_memory
    app.state.cognitive_engine = cognitive_engine
    yield {
        "kernel": kernel,
        "memory": memory,
        "semantic_memory": semantic_memory,
        "cognitive_engine": cognitive_engine,
    }


@pytest.mark.asyncio
async def test_chat_system_command_help(mock_app_state):
    """System commands return instantly without hitting the kernel."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/nova-web/chat", json={
            "message": "/help",
        })

    assert response.status_code == 200
    data = response.json()
    assert "Available commands" in data["response"]
    mock_app_state["kernel"].run_agent.assert_not_called()


@pytest.mark.asyncio
async def test_chat_system_command_status(mock_app_state):
    """Status command returns system status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/nova-web/chat", json={
            "message": "/status",
        })

    assert response.status_code == 200
    data = response.json()
    assert "System operational" in data["response"]
    mock_app_state["kernel"].run_agent.assert_not_called()


@pytest.mark.asyncio
async def test_chat_empty_message():
    """Empty message returns 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/nova-web/chat", json={
            "message": "",
        })

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_delegates_to_kernel(mock_app_state):
    """Substantive messages go through the kernel."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/nova-web/chat", json={
            "message": "Explain quantum computing",
        })

    assert response.status_code == 200
    mock_app_state["kernel"].run_agent.assert_called_once()


@pytest.mark.asyncio
async def test_chat_returns_session_id(mock_app_state):
    """Chat response includes session_id."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/nova-web/chat", json={
            "message": "Hello",
            "session_id": str(uuid4()),
        })

    assert response.status_code == 200
    data = response.json()
    assert len(data["session_id"]) == 36


@pytest.mark.asyncio
async def test_chat_generates_session_id_if_missing():
    """Session ID is generated if not provided."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/nova-web/chat", json={
            "message": "Hello",
        })

    assert response.status_code == 200
    data = response.json()
    assert len(data["session_id"]) == 36  # UUID format


@pytest.mark.asyncio
async def test_chat_stores_in_conversation_memory(mock_app_state):
    """System commands are stored in conversation memory."""
    memory = mock_app_state["memory"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post("/api/v1/nova-web/chat", json={
            "message": "/help",
        })

    # Memory methods should be called (ensure_session, add_message x2)
    memory.ensure_session.assert_called_once()
    assert memory.add_message.call_count == 2


@pytest.mark.asyncio
async def test_chat_response_format():
    """Response has all required fields."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/nova-web/chat", json={
            "message": "Test",
        })

    data = response.json()
    assert "response" in data
    assert "session_id" in data
    assert "task_id" in data
    assert "actions_taken" in data
    assert "objectives" in data
    assert "projects" in data
    assert "tasks" in data
    assert "approval_required" in data


@pytest.mark.asyncio
async def test_chat_stores_in_semantic_memory(mock_app_state):
    """Substantive messages are stored in semantic memory."""
    sm = mock_app_state["semantic_memory"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post("/api/v1/nova-web/chat", json={
            "message": "What is machine learning?",
        })

    sm.search.assert_called_once()
    sm.store.assert_called_once()


@pytest.mark.asyncio
async def test_chat_uses_cognitive_engine_for_intent(mock_app_state):
    """Cognitive engine is used for intent detection on substantive messages."""
    ce = mock_app_state["cognitive_engine"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post("/api/v1/nova-web/chat", json={
            "message": "Create a Python script",
        })

    ce.process.assert_called_once()
