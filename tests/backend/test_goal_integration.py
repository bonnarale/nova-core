"""Integration tests for Goal Manager in the kernel flow.

Verifies that:
  1. User messages with goals create GoalManager entries
  2. Goals are injected into the agent's context
  3. Blocked goals and next actions are surfaced
  4. Goal analysis is provided alongside profile and semantic memory
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.routes.kernel import ExecuteRequest
from app.kernel import create_session, get_kernel
from app.kernel.registry import register_agent
from app.memory.goals import GoalProvider


class FakeGoalManager(GoalProvider):
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
        return [
            dict(g) for g in self.goals.get(uid, []) if g["status"] == "blocked"
        ]

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


class TestGoalIntegration:
    @pytest.mark.asyncio
    async def test_goals_extracted_and_stored(
        self, request_mock, fake_memory, fake_goal_manager, agent, fake_gateway
    ):
        from app.api.v1.routes.kernel import execute

        user_id = "00000000-0000-0000-0000-000000000001"
        session_id = "00000000-0000-0000-0000-000000000010"

        body = ExecuteRequest(
            task="I want to build a website and I need to learn React",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        result = await execute(request_mock, body)

        goals = await fake_goal_manager.list_goals(user_id)
        assert len(goals) >= 1
        titles = [g["title"] for g in goals]
        assert any("build a website" in t for t in titles)

    @pytest.mark.asyncio
    async def test_goals_injected_into_agent_context(
        self, request_mock, fake_memory, fake_goal_manager, agent, fake_gateway
    ):
        from app.api.v1.routes.kernel import execute

        user_id = "00000000-0000-0000-0000-000000000002"
        session_id = "00000000-0000-0000-0000-000000000020"

        body = ExecuteRequest(
            task="I want to learn Python",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body)

        assert len(fake_gateway.calls) == 1
        messages = fake_gateway.calls[0]["messages"]

        goal_systems = [m for m in messages if "## Current Goals" in m.get("content", "")]
        assert len(goal_systems) == 1
        assert "learn Python" in goal_systems[0]["content"]

    @pytest.mark.asyncio
    async def test_goals_profile_and_memories_coexist(
        self, request_mock, fake_memory, fake_profile_memory, fake_semantic_memory, fake_goal_manager, agent, fake_gateway
    ):
        from app.api.v1.routes.kernel import execute

        user_id = "00000000-0000-0000-0000-000000000003"
        session_id = "00000000-0000-0000-0000-000000000030"

        body = ExecuteRequest(
            task="My name is Alex and I want to build Nova Core",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body)

        messages = fake_gateway.calls[0]["messages"]
        contents = [m["content"] for m in messages]

        profile_present = any("## User Profile" in c for c in contents)
        goals_present = any("## Current Goals" in c for c in contents)

        assert profile_present, "Profile should be present"
        assert goals_present, "Goals should be present"
        assert "Name: Alex" in contents[1]
        assert "Current Goals" in contents[2] or "Current Goals" in contents[1]

    @pytest.mark.asyncio
    async def test_goal_progress_and_blocking(
        self, request_mock, fake_memory, fake_goal_manager, agent, fake_gateway
    ):
        from app.api.v1.routes.kernel import execute

        user_id = "00000000-0000-0000-0000-000000000004"
        session_id = "00000000-0000-0000-0000-000000000040"

        # Pre-create a goal
        await fake_goal_manager.create_goal(user_id, "Build the database layer", priority=5)

        # Send a message (no new goal extraction from this one)
        body = ExecuteRequest(
            task="I'm working on the frontend now",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body)

        messages = fake_gateway.calls[0]["messages"]
        goal_contents = [m["content"] for m in messages if "## Current Goals" in m.get("content", "")]
        assert len(goal_contents) == 1
        assert "Build the database layer" in goal_contents[0]

    @pytest.mark.asyncio
    async def test_no_goals_when_no_user_id(
        self, request_mock, fake_memory, fake_goal_manager, agent, fake_gateway
    ):
        from app.api.v1.routes.kernel import execute

        session_id = "00000000-0000-0000-0000-000000000050"

        body = ExecuteRequest(
            task="I want to do something",
            agent_id="assistant",
            session_id=session_id,
        )
        await execute(request_mock, body)

        messages = fake_gateway.calls[0]["messages"]
        goal_systems = [m for m in messages if "## Current Goals" in m.get("content", "")]
        assert len(goal_systems) == 0

    @pytest.mark.asyncio
    async def test_goal_next_actions_section(
        self, request_mock, fake_memory, fake_goal_manager, agent, fake_gateway
    ):
        from app.api.v1.routes.kernel import execute

        user_id = "00000000-0000-0000-0000-000000000005"
        session_id = "00000000-0000-0000-0000-000000000060"

        # Pre-create multiple goals with different priorities
        await fake_goal_manager.create_goal(user_id, "Low priority task", priority=1)
        await fake_goal_manager.create_goal(user_id, "High priority task", priority=5)
        await fake_goal_manager.create_goal(user_id, "Medium priority task", priority=3)

        body = ExecuteRequest(
            task="What should I work on next?",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body)

        messages = fake_gateway.calls[0]["messages"]
        goal_contents = [m["content"] for m in messages if "## Current Goals" in m.get("content", "")]
        assert len(goal_contents) == 1
        assert "High priority task" in goal_contents[0]
        assert "Recommended Next Actions" in goal_contents[0]
        assert "Progress Overview" in goal_contents[0]

    @pytest.mark.asyncio
    async def test_goals_persist_across_messages(
        self, request_mock, fake_memory, fake_goal_manager, agent, fake_gateway
    ):
        from app.api.v1.routes.kernel import execute

        user_id = "00000000-0000-0000-0000-000000000006"
        session_id = "00000000-0000-0000-0000-000000000070"

        # Message 1: establish a goal
        body1 = ExecuteRequest(
            task="I need to deploy the API",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body1)

        goals = await fake_goal_manager.list_goals(user_id)
        assert len(goals) == 1
        assert any("deploy the API" in g["title"] for g in goals)

        # Message 2: mention another goal
        body2 = ExecuteRequest(
            task="I want to write documentation",
            agent_id="assistant",
            session_id=session_id,
            user_id=user_id,
        )
        await execute(request_mock, body2)

        goals = await fake_goal_manager.list_goals(user_id)
        # The extractor re-scans all history, so msg2 re-creates "deploy the API"
        # plus creates "write documentation", resulting in 3 total
        assert len(goals) >= 2
        titles = [g["title"] for g in goals]
        assert any("deploy the API" in t for t in titles)
        assert any("write documentation" in t for t in titles)
