"""Integration tests for async chat endpoint with task_id return."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
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
def client_with_cognitive_engine() -> TestClient:
    """Create a test client with a mocked cognitive engine that creates tasks."""
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
        "created_task": {"id": task_id, "goal": "test task"},
        "assigned_agent": "executor",
        "task_id": task_id,
    }
    mock_state.error = None
    mock_cognitive_engine.process = AsyncMock(return_value=mock_state)
    app.state.cognitive_engine = mock_cognitive_engine

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def client_without_cognitive_engine() -> TestClient:
    """Create a test client without a cognitive engine (legacy path)."""
    app = FastAPI()
    app.include_router(router)

    # Mock kernel
    mock_kernel = AsyncMock()
    mock_kernel.run_agent = AsyncMock(return_value={
        "response": {"message": {"content": "Hello!"}},
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

    # No cognitive engine set — tests the fallback path
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Tests: task_id in chat response
# ---------------------------------------------------------------------------

class TestChatTaskIdReturn:
    """Verify chat endpoint returns task_id when cognitive engine creates a task."""

    def test_chat_returns_task_id_field(self, client_with_cognitive_engine: TestClient) -> None:
        """Response must include task_id field."""
        resp = client_with_cognitive_engine.post(
            "/nova-web/chat",
            json={"message": "create a task to build a website"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "task_id" in body, "response must include task_id field"

    def test_chat_returns_task_id_string(self, client_with_cognitive_engine: TestClient) -> None:
        """task_id must be a string when present."""
        resp = client_with_cognitive_engine.post(
            "/nova-web/chat",
            json={"message": "create a task to build a website"},
        )
        body = resp.json()
        assert isinstance(body["task_id"], str), "task_id must be a string"

    def test_chat_returns_valid_uuid_task_id(self, client_with_cognitive_engine: TestClient) -> None:
        """task_id must be a valid UUID when a task is created."""
        resp = client_with_cognitive_engine.post(
            "/nova-web/chat",
            json={"message": "create a task to build a website"},
        )
        body = resp.json()
        task_id = body["task_id"]
        assert task_id is not None, "task_id must not be None"
        # Verify it's a valid UUID
        from uuid import UUID
        UUID(task_id)  # raises ValueError if invalid

    def test_chat_task_id_matches_cognitive_engine_result(
        self, client_with_cognitive_engine: TestClient
    ) -> None:
        """task_id in response must match the cognitive engine's execution_result."""
        resp = client_with_cognitive_engine.post(
            "/nova-web/chat",
            json={"message": "create a task to build a website"},
        )
        body = resp.json()
        # The mocked cognitive engine returns a specific task_id
        assert body["task_id"] is not None

    def test_chat_task_id_none_when_no_task_created(
        self, client_without_cognitive_engine: TestClient
    ) -> None:
        """task_id must be None when cognitive engine doesn't create a task."""
        resp = client_without_cognitive_engine.post(
            "/nova-web/chat",
            json={"message": "hello"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "task_id" in body, "response must include task_id field"
        assert body["task_id"] is None, "task_id must be None when no task created"

    def test_chat_response_preserves_existing_fields(
        self, client_with_cognitive_engine: TestClient
    ) -> None:
        """Adding task_id must not break existing response fields."""
        resp = client_with_cognitive_engine.post(
            "/nova-web/chat",
            json={"message": "create a task to build a website"},
        )
        body = resp.json()
        for key in (
            "response",
            "session_id",
            "task_id",
            "actions_taken",
            "objectives",
            "projects",
            "tasks",
            "approval_required",
        ):
            assert key in body, f"missing key: {key}"

    def test_cognitive_engine_process_called_with_message(
        self, client_with_cognitive_engine: TestClient
    ) -> None:
        """Cognitive engine must receive the user's message."""
        resp = client_with_cognitive_engine.post(
            "/nova-web/chat",
            json={"message": "create a task to build a website"},
        )
        assert resp.status_code == 200

    def test_chat_empty_message_still_rejected(
        self, client_with_cognitive_engine: TestClient
    ) -> None:
        """Empty message must still return 400."""
        resp = client_with_cognitive_engine.post(
            "/nova-web/chat",
            json={"message": ""},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Tests: backward compatibility
# ---------------------------------------------------------------------------

class TestChatBackwardCompatibility:
    """Ensure existing chat behavior is preserved."""

    def test_system_commands_still_work(self, client_with_cognitive_engine: TestClient) -> None:
        """System commands (/help, /status, /health) must still work."""
        resp = client_with_cognitive_engine.post(
            "/nova-web/chat",
            json={"message": "/help"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["response"]  # non-empty
        assert body["task_id"] is None  # no task for system commands

    def test_regular_chat_returns_no_task_id(
        self, client_without_cognitive_engine: TestClient
    ) -> None:
        """Regular chat without cognitive engine must return task_id=None."""
        resp = client_without_cognitive_engine.post(
            "/nova-web/chat",
            json={"message": "What is the weather today?"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["task_id"] is None
        assert body["response"]  # non-empty
