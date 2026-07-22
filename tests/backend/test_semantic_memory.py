"""Integration tests for SemanticMemory orchestration.

Verifies that:
  1. Every user message is stored in semantic memory
  2. Relevant past memories are retrieved and injected into the prompt
  3. Semantic memories are formatted as a system message
  4. Conversation history and semantic memories are independen
"""

from unittest.mock import MagicMock

import pytest

from app.api.v1.routes.kernel import ExecuteRequest
from app.kernel import get_kernel
from app.kernel.registry import register_agent
from app.memory.semantic import SemanticMemory


class FakeChromaCollection:
    """Replaces the real Chroma collection for unit-testing SemanticMemory."""

    def __init__(self):
        self._docs: dict[str, dict] = {}

    def get_or_create_collection(self, name, metadata=None):
        return self

    def add(self, ids, embeddings, metadatas, documents):
        for i, doc_id in enumerate(ids):
            self._docs[doc_id] = {
                "embedding": embeddings[i],
                "metadata": metadatas[i],
                "document": documents[i],
            }

    def query(self, query_embeddings, n_results):
        # Return all stored documents (order doesn't matter for fakes)
        entries = list(self._docs.values())[:n_results]
        return {
            "ids": [[e["metadata"]["session_id"] for e in entries]],
            "documents": [[e["document"] for e in entries]],
            "metadatas": [[e["metadata"] for e in entries]],
            "distances": [[0.1 * (i + 1) for i in range(len(entries))]],
        }

    def count(self):
        return len(self._docs)

    def delete(self, ids):
        for doc_id in ids:
            self._docs.pop(doc_id, None)

    def get(self):
        return {"ids": list(self._docs.keys())}


class FakeOllama:
    def __init__(self):
        self.embedded_texts: list[str] = []

    async def embed(self, text):
        self.embedded_texts.append(text)
        # Return a simple deterministic embedding
        return [float(ord(c)) for c in text[:8]] + [0.0] * (8 - min(len(text), 8))


class FakeMemory:
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


class FakeGoalManager:
    def __init__(self):
        self.goals: dict[str, list[dict]] = {}

    async def create_goal(self, user_id, title, description=None, priority=3):
        uid = str(user_id)
        if uid not in self.goals:
            self.goals[uid] = []
        goal = {"title": title, "priority": priority, "status": "active", "progress": 0}
        self.goals[uid].append(goal)
        return dict(goal)

    async def get_goal(self, goal_id):
        return None

    async def list_goals(self, user_id, status=None):
        uid = str(user_id)
        return [dict(g) for g in self.goals.get(uid, [])]

    async def update_goal(self, goal_id, **kwargs):
        return None

    async def delete_goal(self, goal_id):
        return True

    async def get_next_actions(self, user_id, limit=3):
        return []

    async def get_blocked_goals(self, user_id):
        return []

    async def analyze_progress(self, user_id):
        uid = str(user_id)
        goals = self.goals.get(uid, [])
        return {"total": len(goals), "active": 0, "blocked": 0, "completed": 0, "abandoned": 0, "avg_progress": 0.0, "next_actions": []}


class FakeGateway:
    def __init__(self):
        self.calls: list[dict] = []

    async def chat(self, model, messages, **kwargs):
        self.calls.append({"model": model, "messages": list(messages)})
        last = messages[-1]["content"]
        return {"message": {"content": f"Echo: {last}"}}


@pytest.fixture(autouse=True)
def _clean_kernel_registry():
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
def semantic_memory():
    ollama = FakeOllama()
    chroma = FakeChromaCollection()
    return SemanticMemory(chroma, ollama, top_k=3)


@pytest.fixture
def fake_goal_manager():
    return FakeGoalManager()


@pytest.fixture
def request_mock(fake_memory, semantic_memory, fake_goal_manager):
    req = MagicMock()
    req.app.state.memory = fake_memory
    req.app.state.semantic_memory = semantic_memory
    req.app.state.goal_manager = fake_goal_manager
    kernel = get_kernel()
    req.app.state.kernel = kernel
    return req


class TestSemanticMemoryStore:
    """Verify that messages are stored in semantic memory."""

    @pytest.mark.asyncio
    async def test_user_message_stored(self, request_mock, semantic_memory, agent):
        from app.api.v1.routes.kernel import execute

        session_id = "00000000-0000-0000-0000-000000000100"
        body = ExecuteRequest(
            task="Hello, who are you?",
            agent_id="assistant",
            session_id=session_id,
        )
        await execute(request_mock, body)

        # The message should have been stored in semantic memory
        count = await semantic_memory.count()
        assert count >= 1


class TestSemanticMemoryRetrieval:
    """Verify that relevant memories are retrieved and injected."""

    @pytest.mark.asyncio
    async def test_relevant_memories_injected(
        self, request_mock, semantic_memory, agent, fake_gateway
    ):
        from app.api.v1.routes.kernel import execute

        session_id = "00000000-0000-0000-0000-000000000200"

        # First call stores the message
        body1 = ExecuteRequest(
            task="I like Python programming",
            agent_id="assistant",
            session_id=session_id,
        )
        await execute(request_mock, body1)

        # Second call should find the first message as a relevant memory
        body2 = ExecuteRequest(
            task="What do I like?",
            agent_id="assistant",
            session_id=session_id,
        )
        await execute(request_mock, body2)

        # The agent received both calls (2 gateway calls)
        assert len(fake_gateway.calls) == 2

        # Second call should have semantic memories injected
        call2_msgs = fake_gateway.calls[1]["messages"]
        roles = [m["role"] for m in call2_msgs]
        contents = [m["content"] for m in call2_msgs]

        # System prompt + semantic memories + history messages
        assert roles[0] == "system"  # system prompt
        assert roles[1] == "system"  # semantic memories
        assert "## Relevant Past Memories" in contents[1]
        assert "I like Python programming" in contents[1]

    @pytest.mark.asyncio
    async def test_memories_independent_from_history(
        self, request_mock, semantic_memory, agent, fake_gateway
    ):
        """Conversation history and semantic memories are both present."""
        from app.api.v1.routes.kernel import execute

        session_id = "00000000-0000-0000-0000-000000000300"

        body1 = ExecuteRequest(
            task="My name is Ana",
            agent_id="assistant",
            session_id=session_id,
        )
        await execute(request_mock, body1)

        body2 = ExecuteRequest(
            task="What is my name?",
            agent_id="assistant",
            session_id=session_id,
        )
        await execute(request_mock, body2)

        call2_msgs = fake_gateway.calls[1]["messages"]
        contents = [m["content"] for m in call2_msgs]

        # Semantic memories contain "My name is Ana"
        semantic_content = [c for c in contents if "## Relevant Past Memories" in c]
        assert len(semantic_content) == 1
        assert "My name is Ana" in semantic_content[0]

        # History ALSO contains "My name is Ana"  (independent sources)
        history_content = [c for c in contents if c == "My name is Ana" or c == "What is my name?"]
        assert len(history_content) >= 1

    @pytest.mark.asyncio
    async def test_no_memories_when_collection_empty(
        self, request_mock, semantic_memory, agent, fake_gateway
    ):
        """First message should not have past memories, only history."""
        from app.api.v1.routes.kernel import execute

        session_id = "00000000-0000-0000-0000-000000000400"
        body = ExecuteRequest(
            task="First message ever",
            agent_id="assistant",
            session_id=session_id,
        )
        await execute(request_mock, body)

        msgs = fake_gateway.calls[0]["messages"]
        # Only system prompt + user message (no semantic memories block)
        # The semantic memory search returns [] and storage happens after search
        # so the first call has no past memories
        contents = [m["content"] for m in msgs]
        assert not any("## Relevant Past Memories" in c for c in contents)


class FakeProfileMemory:
    """Minimal in-memory fake for ProfileProvider (duplicated to avoid import issues)."""

    def __init__(self):
        self.profiles: dict[str, dict] = {}

    async def create_profile(self, profile_id, name=None, bio=None, preferences=None, goals=None, facts=None):
        pid = str(profile_id)
        p = {"id": pid, "name": name, "bio": bio, "preferences": preferences or {}, "goals": goals or [], "facts": facts or []}
        self.profiles[pid] = p
        return dict(p)

    async def get_profile(self, profile_id):
        pid = str(profile_id)
        p = self.profiles.get(pid)
        return dict(p) if p else None

    async def update_profile(self, profile_id, name=None, bio=None, preferences=None, goals=None, facts=None):
        pid = str(profile_id)
        p = self.profiles.get(pid)
        if p is None:
            return None
        if name is not None:
            p["name"] = name
        if bio is not None:
            p["bio"] = bio
        if preferences is not None:
            p["preferences"] = preferences
        if goals is not None:
            p["goals"] = goals
        if facts is not None:
            p["facts"] = facts
        return dict(p)

    async def add_facts(self, profile_id, new_facts):
        pid = str(profile_id)
        p = self.profiles.get(pid)
        if p is None:
            return None
        existing = set(p.get("facts") or [])
        for f in new_facts:
            if f not in existing:
                p["facts"].append(f)
                existing.add(f)
        return dict(p)


class TestSemanticMemoryIndependence:
    """Verify that semantic memory does not interfere with existing systems."""

    @pytest.mark.asyncio
    async def test_profile_and_memories_coexist(
        self, request_mock, semantic_memory, agent, fake_gateway
    ):
        """Both profile and semantic memories can be injected simultaneously."""
        from app.api.v1.routes.kernel import execute

        fake_profile_memory = FakeProfileMemory()
        request_mock.app.state.profile_memory = fake_profile_memory

        user_id = "00000000-0000-0000-0000-000000000500"
        session_id = "00000000-0000-0000-0000-000000000600"

        # First call: establish name
        body1 = ExecuteRequest(
            task="My name is Carlos and I build APIs",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body1)

        # Second call: both profile and memories should be injected
        body2 = ExecuteRequest(
            task="What do I build?",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body2)

        call2_msgs = fake_gateway.calls[1]["messages"]
        roles = [m["role"] for m in call2_msgs]
        contents = [m["content"] for m in call2_msgs]

        # Order: system prompt, profile, semantic memories, history
        assert roles[0] == "system"
        assert roles[1] == "system"
        assert roles[2] == "system"

        assert "## User Profile" in contents[1]
        assert "Carlos" in contents[1]
        assert "## Relevant Past Memories" in contents[2]
        assert "build APIs" in contents[2]

        # History is also present
        user_msgs = [c for c in contents if "build APIs" in c or "What do I build?" in c]
        assert len(user_msgs) >= 1
