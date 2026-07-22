"""Integration-style tests for the full kernel execute flow with memory.

Simulates two sequential calls with the same ``session_id`` to verify
that the conversation history is persisted between calls and correctly
injected into the agent's context.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.routes.kernel import ExecuteRequest
from app.kernel import create_session, get_kernel
from app.kernel.registry import register_agent


class FakeMemory:
    """An in-memory fake that implements ``MemoryProvider``."""

    def __init__(self):
        self.sessions: set[str] = set()
        self.messages: dict[str, list[dict[str, str]]] = {}

    async def ensure_session(self, session_id, agent_id):
        self.sessions.add(str(session_id))

    async def add_message(self, session_id, role, content):
        sid = str(session_id)
        if sid not in self.messages:
            self.messages[sid] = []
        self.messages[sid].append({"role": role, "content": content})

    async def get_history(self, session_id, limit=20):
        sid = str(session_id)
        return self.messages.get(sid, [])[-limit:]


class FakeSemanticMemory:
    """In-memory fake for SemanticMemory."""

    def __init__(self):
        self.stored: list[dict] = []

    async def store(self, session_id, content):
        self.stored.append({"session_id": str(session_id), "content": content})

    async def search(self, query, top_k=None):
        return []


class FakeGateway:
    """Fake gateway that records every call for later assertion."""

    def __init__(self):
        self.calls: list[dict] = []

    async def chat(self, model, messages, **kwargs):
        self.calls.append({"model": model, "messages": list(messages)})
        last = messages[-1]["content"]
        return {"message": {"content": f"Echo: {last}"}}


@pytest.fixture(autouse=True)
def _clean_kernel_registry():
    """Ensure a clean kernel + agent registry for every test."""
    from app.kernel.registry import _agents

    _agents.clear()
    from app.kernel.engine import _kernel

    _kernel = None
    from app.kernel.session import _sessions

    _sessions.clear()


@pytest.fixture
def fake_gateway():
    return FakeGateway()


@pytest.fixture
def agent(fake_gateway):
    from app.agents.llm_agent import LLMAgent

    agent = LLMAgent(
        agent_id="assistant",
        gateway=fake_gateway,
        system_prompt="You are a helpful assistant.",
    )
    register_agent(agent)
    return agent


@pytest.fixture
def fake_memory():
    return FakeMemory()


@pytest.fixture
def fake_semantic_memory():
    return FakeSemanticMemory()


@pytest.fixture
def request_mock(fake_memory, fake_semantic_memory):
    """Create a mock FastAPI Request with the kernel and memory wired."""
    req = MagicMock()
    req.app.state.memory = fake_memory
    req.app.state.semantic_memory = fake_semantic_memory

    kernel = get_kernel()
    req.app.state.kernel = kernel
    return req


@pytest.mark.asyncio
async def test_full_conversation_two_calls_same_session(
    request_mock, fake_memory, agent, fake_gateway
):
    """Two execute calls with the same session_id must share history."""
    from app.api.v1.routes.kernel import execute

    session_id = "00000000-0000-0000-0000-000000000001"

    # ── Call 1 ────────────────────────────────────────────────────────
    body1 = ExecuteRequest(
        task="Hello, who are you?",
        agent_id="assistant",
        session_id=session_id,
    )
    result1 = await execute(request_mock, body1)

    assert result1["session_id"] == session_id
    assert len(fake_gateway.calls) == 1

    # Call 1 should have: system + user
    msg_roles = [m["role"] for m in fake_gateway.calls[0]["messages"]]
    assert msg_roles == ["system", "user"]
    assert fake_gateway.calls[0]["messages"][1]["content"] == "Hello, who are you?"

    # Memory should contain: user + assistant
    assert len(fake_memory.messages[session_id]) == 2
    assert fake_memory.messages[session_id][0]["role"] == "user"
    assert fake_memory.messages[session_id][0]["content"] == "Hello, who are you?"
    assert fake_memory.messages[session_id][1]["role"] == "assistant"

    # ── Call 2 ────────────────────────────────────────────────────────
    body2 = ExecuteRequest(
        task="What did I just ask you?",
        agent_id="assistant",
        session_id=session_id,
    )
    result2 = await execute(request_mock, body2)
    assert result2["session_id"] == session_id
    assert len(fake_gateway.calls) == 2

    # Call 2 should have: system + history(4 entries) = 5 total messages
    msg_roles_2 = [m["role"] for m in fake_gateway.calls[1]["messages"]]
    assert msg_roles_2 == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    contents = [m["content"] for m in fake_gateway.calls[1]["messages"]]
    assert contents[1] == "Hello, who are you?"  # history preserved
    assert contents[3] == "What did I just ask you?"  # current message

    # Memory should have: user1 + asst1 + user2 + asst2
    assert len(fake_memory.messages[session_id]) == 4
    assert fake_memory.messages[session_id][2]["role"] == "user"
    assert fake_memory.messages[session_id][3]["role"] == "assistant"


@pytest.mark.asyncio
async def test_new_session_when_no_session_id_provided(
    request_mock, fake_memory, agent
):
    """Omitting session_id should create a brand-new session."""
    from app.api.v1.routes.kernel import execute

    body = ExecuteRequest(
        task="First message",
        agent_id="assistant",
    )
    result = await execute(request_mock, body)

    # A new session_id must be returned
    assert result["session_id"] is not None
    sid = result["session_id"]

    # Memory must have one user + one assistant message
    assert len(fake_memory.messages[sid]) == 2


@pytest.mark.asyncio
async def test_invalid_session_id_returns_422(request_mock, fake_memory, agent):
    """A malformed session_id must result in a 422 error."""
    from app.api.v1.routes.kernel import execute

    body = ExecuteRequest(
        task="test",
        agent_id="assistant",
        session_id="not-a-uuid",
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await execute(request_mock, body)

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_session_can_be_reused_after_kernel_restart(
    request_mock, fake_memory, agent, fake_gateway
):
    """Simulates a kernel restart by clearing in-memory sessions.
    The DB-backed memory (fake_memory) retains history."""
    from app.api.v1.routes.kernel import execute

    session_id = "00000000-0000-0000-0000-000000000002"

    # Call 1
    body1 = ExecuteRequest(
        task="First question",
        agent_id="assistant",
        session_id=session_id,
    )
    await execute(request_mock, body1)

    # Simulate kernel restart: clear in-memory sessions
    from app.kernel.session import _sessions

    _sessions.clear()

    # Call 2 — same session_id, now the in-memory session is gone
    body2 = ExecuteRequest(
        task="Second question",
        agent_id="assistant",
        session_id=session_id,
    )
    await execute(request_mock, body2)

    # The fake_memory retains the full history (4 messages)
    assert len(fake_memory.messages[session_id]) == 4
    assert fake_memory.messages[session_id][0]["content"] == "First question"
    assert fake_memory.messages[session_id][2]["content"] == "Second question"

    # The agent received the full history from memory
    assert len(fake_gateway.calls) == 2
    call2_messages = fake_gateway.calls[1]["messages"]
    call2_contents = [m["content"] for m in call2_messages]
    # First question is in the history of the second call
    assert "First question" in call2_contents
    assert "Second question" in call2_contents[-1]
