"""Integration tests for the full user profile memory flow.

Verifies that:
  1. User messages with personal information are extracted
  2. Extracted data is merged into the user profile
  3. Profile is persisted and reloaded
  4. Profile is injected into the agent's context
  5. LLMAgent includes the profile as a system message
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.routes.kernel import ExecuteRequest
from app.kernel import create_session, get_kernel
from app.kernel.registry import register_agent


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


class FakeProfileMemory:
    """In-memory fake that implements ProfileProvider."""

    def __init__(self):
        self.profiles: dict[str, dict] = {}

    async def create_profile(
        self, profile_id, name=None, bio=None, preferences=None, goals=None, facts=None
    ):
        pid = str(profile_id)
        p = {
            "id": pid,
            "name": name,
            "bio": bio,
            "preferences": preferences or {},
            "goals": goals or [],
            "facts": facts or [],
        }
        self.profiles[pid] = p
        return dict(p)

    async def get_profile(self, profile_id):
        pid = str(profile_id)
        p = self.profiles.get(pid)
        return dict(p) if p else None

    async def update_profile(
        self, profile_id, name=None, bio=None, preferences=None, goals=None, facts=None
    ):
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


class FakeGoalManager:
    """In-memory fake that implements GoalProvider."""

    def __init__(self):
        self.goals: dict[str, list[dict]] = {}
        self._next_id = 0

    async def create_goal(self, user_id, title, description=None, priority=3):
        uid = str(user_id)
        if uid not in self.goals:
            self.goals[uid] = []
        self._next_id += 1
        goal = {
            "id": f"00000000-0000-0000-0000-{self._next_id:012d}",
            "user_id": uid,
            "title": title,
            "description": description,
            "status": "active",
            "priority": priority,
            "progress": 0,
            "block_reason": None,
            "created_at": None,
            "updated_at": None,
        }
        self.goals[uid].append(goal)
        return dict(goal)

    async def get_goal(self, goal_id):
        for uid, goals in self.goals.items():
            for g in goals:
                if g["id"] == str(goal_id):
                    return dict(g)
        return None

    async def list_goals(self, user_id, status=None):
        uid = str(user_id)
        goals = self.goals.get(uid, [])
        if status:
            goals = [g for g in goals if g["status"] == status]
        return [dict(g) for g in goals]

    async def update_goal(self, goal_id, **kwargs):
        for uid, goals in self.goals.items():
            for g in goals:
                if g["id"] == str(goal_id):
                    for k, v in kwargs.items():
                        if v is not None:
                            g[k] = v
                    return dict(g)
        return None

    async def delete_goal(self, goal_id):
        for uid, goals in self.goals.items():
            for g in goals:
                if g["id"] == str(goal_id):
                    self.goals[uid] = [x for x in self.goals[uid] if x["id"] != str(goal_id)]
                    return True
        return False

    async def get_next_actions(self, user_id, limit=3):
        uid = str(user_id)
        active = [
            g for g in self.goals.get(uid, [])
            if g["status"] == "active" and g["progress"] < 100
        ]
        active.sort(key=lambda g: (-g["priority"], g["progress"], g["title"]))
        return [dict(g) for g in active[:limit]]

    async def get_blocked_goals(self, user_id):
        uid = str(user_id)
        return [dict(g) for g in self.goals.get(uid, []) if g["status"] == "blocked"]

    async def analyze_progress(self, user_id):
        uid = str(user_id)
        goals = self.goals.get(uid, [])
        total = len(goals)
        active = sum(1 for g in goals if g["status"] == "active" and g["progress"] < 100)
        blocked = sum(1 for g in goals if g["status"] == "blocked")
        completed = sum(1 for g in goals if g["status"] == "completed" or g["progress"] >= 100)
        abandoned = sum(1 for g in goals if g["status"] == "abandoned")
        avg_progress = sum(g["progress"] for g in goals) / total if total else 0.0
        next_actions = await self.get_next_actions(uid, limit=3)
        return {
            "total": total,
            "active": active,
            "blocked": blocked,
            "completed": completed,
            "abandoned": abandoned,
            "avg_progress": round(avg_progress, 1),
            "next_actions": next_actions,
        }


class FakeSemanticMemory:
    def __init__(self):
        self.stored: list[dict] = []

    async def store(self, session_id, content):
        self.stored.append({"session_id": str(session_id), "content": content})

    async def search(self, query, top_k=None):
        return []


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
def fake_profile_memory():
    return FakeProfileMemory()


@pytest.fixture
def fake_semantic_memory():
    return FakeSemanticMemory()


@pytest.fixture
def fake_goal_manager():
    return FakeGoalManager()


@pytest.fixture
def request_mock(fake_memory, fake_profile_memory, fake_semantic_memory, fake_goal_manager):
    req = MagicMock()
    req.app.state.memory = fake_memory
    req.app.state.profile_memory = fake_profile_memory
    req.app.state.semantic_memory = fake_semantic_memory
    req.app.state.goal_manager = fake_goal_manager
    kernel = get_kernel()
    req.app.state.kernel = kernel
    return req


class TestUserProfileIntegration:
    """End-to-end tests for the profile extraction → persistence → injection flow."""

    @pytest.mark.asyncio
    async def test_profile_created_and_injected_on_first_message(
        self, request_mock, fake_memory, fake_profile_memory, agent, fake_gateway
    ):
        """User sends a message with their name and the profile gets injected."""
        from app.api.v1.routes.kernel import execute

        user_id = "00000000-0000-0000-0000-000000000001"
        session_id = "00000000-0000-0000-0000-000000000010"

        body = ExecuteRequest(
            task="My name is Ariel and I want to build NOVA CORE",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        result = await execute(request_mock, body)

        # Profile should be created in FakeProfileMemory
        profile = await fake_profile_memory.get_profile(user_id)
        assert profile is not None
        assert profile["name"] == "Ariel"
        assert "build NOVA CORE" in profile.get("goals", [])

        # The agent must have received the profile as a system message
        assert len(fake_gateway.calls) == 1
        messages = fake_gateway.calls[0]["messages"]
        roles = [m["role"] for m in messages]
        contents = [m["content"] for m in messages]

        # System prompt, profile, goals, then user message
        assert len(roles) == 4
        assert roles[0] == "system"
        assert roles[1] == "system"
        assert roles[2] == "system"
        assert roles[3] == "user"
        # Second system message is the profile
        assert "## User Profile" in contents[1]
        assert "Name: Ariel" in contents[1]
        assert "Goals: ['build NOVA CORE']" in contents[1]

    @pytest.mark.asyncio
    async def test_profile_extracted_from_multiple_messages(
        self, request_mock, fake_memory, fake_profile_memory, agent, fake_gateway
    ):
        """Information accumulates across multiple messages in the same session."""
        from app.api.v1.routes.kernel import execute

        user_id = "00000000-0000-0000-0000-000000000002"
        session_id = "00000000-0000-0000-0000-000000000020"

        # Message 1: name
        body1 = ExecuteRequest(
            task="Me llamo Carla",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body1)

        profile = await fake_profile_memory.get_profile(user_id)
        assert profile["name"] == "Carla"

        # Message 2: goal
        body2 = ExecuteRequest(
            task="Voy a crear un chatbot",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body2)

        profile = await fake_profile_memory.get_profile(user_id)
        assert profile["name"] == "Carla"
        assert any("crear un chatbot" in g for g in profile.get("goals", []))

        # Second call: profile + history should both be in the messages
        assert len(fake_gateway.calls) == 2
        call2_msgs = fake_gateway.calls[1]["messages"]
        call2_roles = [m["role"] for m in call2_msgs]
        call2_contents = [m["content"] for m in call2_msgs]

        assert call2_roles[0] == "system"  # system prompt
        assert call2_roles[1] == "system"  # profile
        assert "## User Profile" in call2_contents[1]
        assert "Carla" in call2_contents[1]

    @pytest.mark.asyncio
    async def test_no_profile_when_no_user_id(
        self, request_mock, fake_memory, fake_profile_memory, agent, fake_gateway
    ):
        """Omitting user_id means no profile is created or injected."""
        from app.api.v1.routes.kernel import execute

        session_id = "00000000-0000-0000-0000-000000000030"

        body = ExecuteRequest(
            task="Hello",
            agent_id="assistant",
            session_id=session_id,
        )
        result = await execute(request_mock, body)

        # Only system prompt + user message (no profile)
        msgs = fake_gateway.calls[0]["messages"]
        roles = [m["role"] for m in msgs]
        assert roles == ["system", "user"]

    @pytest.mark.asyncio
    async def test_profile_facts_accumulate(
        self, request_mock, fake_memory, fake_profile_memory, agent, fake_gateway
    ):
        """Facts extracted across calls are accumulated, not replaced."""
        from app.api.v1.routes.kernel import execute

        user_id = "00000000-0000-0000-0000-000000000003"
        session_id = "00000000-0000-0000-0000-000000000040"

        body1 = ExecuteRequest(
            task="I work at Google and I live in San Francisco",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body1)

        profile = await fake_profile_memory.get_profile(user_id)
        assert any("Google" in f for f in profile.get("facts", []))
        assert any("San Francisco" in f for f in profile.get("facts", []))

        body2 = ExecuteRequest(
            task="I work at Microsoft part-time",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body2)

        profile = await fake_profile_memory.get_profile(user_id)
        facts = profile.get("facts", [])
        assert any("Google" in f for f in facts)
        assert any("Microsoft" in f for f in facts)
        # No duplicates
        assert len(facts) == len(set(facts))

    @pytest.mark.asyncio
    async def test_profile_injected_even_without_new_data(
        self, request_mock, fake_memory, fake_profile_memory, agent, fake_gateway
    ):
        """If no new data is extracted, the existing profile is still injected."""
        from app.api.v1.routes.kernel import execute

        user_id = "00000000-0000-0000-0000-000000000004"
        session_id = "00000000-0000-0000-0000-000000000050"

        # First message establishes profile
        body1 = ExecuteRequest(
            task="My name is Pedro",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body1)

        # Second message with no personal info
        body2 = ExecuteRequest(
            task="What is the weather like?",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body2)

        # Profile must still be injected
        call2_msgs = fake_gateway.calls[1]["messages"]
        profile_systems = [m for m in call2_msgs if "## User Profile" in m.get("content", "")]
        assert len(profile_systems) == 1
        assert "Pedro" in profile_systems[0]["content"]

    @pytest.mark.asyncio
    async def test_invalid_user_id_does_not_crash(
        self, request_mock, fake_memory, fake_profile_memory, agent, fake_gateway
    ):
        """A malformed user_id is handled gracefully."""
        from app.api.v1.routes.kernel import execute

        session_id = "00000000-0000-0000-0000-000000000060"

        body = ExecuteRequest(
            task="Hello",
            agent_id="assistant",
            session_id=session_id,
            user_id="not-a-uuid",
        )
        result = await execute(request_mock, body)

        # Should still succeed
        assert result["session_id"] == session_id
        msgs = fake_gateway.calls[0]["messages"]
        assert msgs[0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_acceptance_criteria_full_flow(
        self, request_mock, fake_memory, fake_profile_memory, agent, fake_gateway
    ):
        """Acceptance criteria: name → fact → persist → survive in profile across calls.

        Flow:
          msg1: "Me llamo Ariel."
          msg2: "Estoy desarrollando NOVA CORE."
          GET /profile/ → name=Ariel, facts contain NOVA CORE
          msg3: "¿Cuál es mi proyecto?" → profile still injected
        """
        from app.api.v1.routes.kernel import execute

        user_id = "00000000-0000-0000-0000-000000000005"
        session_id = "00000000-0000-0000-0000-000000000070"

        # ── Message 1: name ─────────────────────────────────────────────
        body1 = ExecuteRequest(
            task="Me llamo Ariel.",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        res1 = await execute(request_mock, body1)
        assert res1["session_id"] == session_id

        profile = await fake_profile_memory.get_profile(user_id)
        assert profile["name"] == "Ariel"

        # ── Message 2: fact about current project ───────────────────────
        body2 = ExecuteRequest(
            task="Estoy desarrollando NOVA CORE.",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        res2 = await execute(request_mock, body2)
        assert res2["session_id"] == session_id

        profile = await fake_profile_memory.get_profile(user_id)
        assert profile["name"] == "Ariel"

        # The profile must contain the project info in facts or goals
        all_profile_text = str(profile)
        assert "NOVA CORE" in all_profile_text or "desarrollando" in all_profile_text

        # ── Message 3: ask about the project ────────────────────────────
        body3 = ExecuteRequest(
            task="¿Cuál es mi proyecto?",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        res3 = await execute(request_mock, body3)
        assert res3["session_id"] == session_id

        # The profile must still be injected in the third call
        assert len(fake_gateway.calls) == 3
        call3_msgs = fake_gateway.calls[2]["messages"]
        profile_systems = [m for m in call3_msgs if "## User Profile" in m.get("content", "")]
        assert len(profile_systems) == 1
        assert "Ariel" in profile_systems[0]["content"]
        assert "NOVA CORE" in profile_systems[0]["content"]

        # The history must also be available
        history_contents = [m["content"] for m in call3_msgs if m["role"] != "system"]
        assert any("Me llamo Ariel" in c for c in history_contents)
        assert any("NOVA CORE" in c for c in history_contents)
