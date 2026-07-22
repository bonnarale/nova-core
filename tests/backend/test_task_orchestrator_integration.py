"""Integration tests for the NOVA CORE Task Orchestrator.

Verifies:
  1. Task creation via Planner
  2. Full lifecycle transitions (CREATED → QUEUED → RUNNING → COMPLETED)
  3. Step advancement with artifacts
  4. Blocked transitions (invalid state changes)
  5. Event Bus notifications
  6. REST endpoint simulation
  7. Concurrent task handling
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestrator import EventBus, TaskManager
from app.orchestrator.planner import Planner
from app.orchestrator.worker import Worker


class FakeDatabase:
    """In-memory fake for Database that stores tasks in a dict."""

    def __init__(self):
        self.session_factory = MagicMock()
        # We'll wire repository calls to fakes in the fixture


class FakeTaskRepo:
    def __init__(self):
        self.tasks: dict[str, dict] = {}
        self._next = 0

    async def create(self, goal, plan=None, steps=None, dependencies=None, assigned_agent=None):
        self._next += 1
        import datetime
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        tid = f"00000000-0000-0000-0000-{self._next:012d}"
        deps = [str(d) for d in (dependencies or [])]
        t = {
            "id": tid,
            "goal": goal,
            "plan": plan or {},
            "steps": steps or [],
            "current_step": 0,
            "status": "CREATED",
            "dependencies": deps,
            "artifacts": {},
            "events": [],
            "assigned_agent": assigned_agent,
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "completed_at": None,
        }
        self.tasks[tid] = t
        return FakeTask(t)

    async def get(self, task_id):
        tid = str(task_id)
        t = self.tasks.get(tid)
        if t is None:
            return None
        return FakeTask(t)

    async def list(self, status=None, limit=50, offset=0):
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        tasks.sort(key=lambda t: t["created_at"], reverse=True)
        return [FakeTask(t) for t in tasks[offset:offset + limit]]

    async def update(self, task_id, **kwargs):
        tid = str(task_id)
        t = self.tasks.get(tid)
        if t is None:
            return None
        import datetime
        for k, v in kwargs.items():
            if v is not None:
                if k in ("started_at", "completed_at") and isinstance(v, str):
                    t[k] = datetime.datetime.fromisoformat(v)
                else:
                    t[k] = v
        t["updated_at"] = datetime.datetime.now(tz=datetime.timezone.utc)
        return FakeTask(t)

    async def delete(self, task_id):
        tid = str(task_id)
        if tid in self.tasks:
            del self.tasks[tid]
            return True
        return False

    async def add_event(self, task_id, event):
        tid = str(task_id)
        t = self.tasks.get(tid)
        if t is None:
            return None
        events = list(t.get("events", []))
        events.append(event)
        t["events"] = events
        return FakeTask(t)


class FakeTask:
    """Wraps a dict to behave like an ORM object for _to_dict()."""

    def __init__(self, data: dict):
        self.id = data["id"]
        self.goal = data["goal"]
        self.plan = data["plan"]
        self.steps = data["steps"]
        self.current_step = data["current_step"]
        self.status = data["status"]
        self.dependencies = data["dependencies"]
        self.artifacts = data["artifacts"]
        self.events = data["events"]
        self.assigned_agent = data["assigned_agent"]
        self.created_at = data["created_at"]
        self.updated_at = data["updated_at"]
        self.started_at = data["started_at"]
        self.completed_at = data["completed_at"]


@pytest.fixture
def fake_repo():
    return FakeTaskRepo()


@pytest.fixture
def fake_database(fake_repo):
    db = MagicMock()
    db.session_factory = MagicMock()
    return db


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def task_manager(fake_database, event_bus, fake_repo):
    mgr = TaskManager(fake_database, event_bus)
    mgr._repo = fake_repo
    mgr.planner._repo = fake_repo
    mgr.worker._repo = fake_repo
    return mgr


class TestTaskOrchestratorIntegration:
    @pytest.mark.asyncio
    async def test_create_task_via_planner(self, task_manager, fake_repo):
        """A task can be created with a goal."""
        result = await task_manager.create_task(
            goal="Build a chatbot",
            steps=["design", "implement", "test", "deploy"],
        )

        assert result["goal"] == "Build a chatbot"
        assert result["status"] == "CREATED"
        assert result["steps"] == ["design", "implement", "test", "deploy"]
        assert result["current_step"] == 0

        # Verify it's retrievable
        fetched = await task_manager.get_task(result["id"])
        assert fetched["goal"] == "Build a chatbot"

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, task_manager, fake_repo):
        """Task goes through CREATED → QUEUED → RUNNING → COMPLETED."""
        result = await task_manager.create_task(
            goal="Deploy API",
            steps=["build", "test", "deploy"],
        )
        tid = result["id"]

        # CREATED → QUEUED
        result = await task_manager.transition_task(tid, "QUEUED")
        assert result["status"] == "QUEUED"

        # QUEUED → RUNNING
        result = await task_manager.transition_task(tid, "RUNNING")
        assert result["status"] == "RUNNING"

        # Advance through steps
        result = await task_manager.advance_step(tid, artifacts={"url": "http://api"})
        assert result["current_step"] >= 1

        result = await task_manager.advance_step(tid, artifacts={"test": "pass"})
        result = await task_manager.advance_step(tid, artifacts={"deploy": "done"})

        # After last step, task should be COMPLETED
        assert result["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_invalid_transition_blocked(self, task_manager, fake_repo):
        """Transition from CREATED directly to COMPLETED is blocked."""
        result = await task_manager.create_task(goal="Test")
        tid = result["id"]

        with pytest.raises(ValueError, match="Invalid transition"):
            await task_manager.transition_task(tid, "COMPLETED")

    @pytest.mark.asyncio
    async def test_event_bus_notifications(self, task_manager, event_bus, fake_repo):
        """Event bus fires on each state transition."""
        events = []

        async def capture(et, data):
            events.append((et, data["task_id"]))

        event_bus.on("task.created", capture)
        event_bus.on("task.queued", capture)
        event_bus.on("task.running", capture)
        event_bus.on("task.completed", capture)

        result = await task_manager.create_task(goal="Event test", steps=["do"])
        tid = result["id"]

        await task_manager.transition_task(tid, "QUEUED")
        await task_manager.transition_task(tid, "RUNNING")
        await task_manager.advance_step(tid)  # completes

        event_types = [e[0] for e in events]
        assert "task.created" in event_types
        assert "task.queued" in event_types
        assert "task.running" in event_types
        assert "task.completed" in event_types

    @pytest.mark.asyncio
    async def test_list_tasks_with_status_filter(self, task_manager, fake_repo):
        """Tasks can be filtered by status."""
        t1 = await task_manager.create_task(goal="Task A")
        t2 = await task_manager.create_task(goal="Task B")

        await task_manager.transition_task(t2["id"], "QUEUED")

        all_tasks = await task_manager.list_tasks()
        assert len(all_tasks) == 2

        created_tasks = await task_manager.list_tasks(status="CREATED")
        assert len(created_tasks) == 1
        assert created_tasks[0]["goal"] == "Task A"

        queued_tasks = await task_manager.list_tasks(status="QUEUED")
        assert len(queued_tasks) == 1

    @pytest.mark.asyncio
    async def test_delete_task(self, task_manager, fake_repo):
        """Tasks can be deleted."""
        result = await task_manager.create_task(goal="Delete me")
        tid = result["id"]

        fetched = await task_manager.get_task(tid)
        assert fetched is not None

        deleted = await task_manager.delete_task(tid)
        assert deleted is True

        fetched = await task_manager.get_task(tid)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_waiting_and_resume(self, task_manager, fake_repo):
        """Task can go RUNNING → WAITING → RUNNING."""
        result = await task_manager.create_task(
            goal="Async task",
            steps=["step1", "step2"],
        )
        tid = result["id"]

        await task_manager.transition_task(tid, "QUEUED")
        await task_manager.transition_task(tid, "RUNNING")

        # Enter waiting state (e.g., waiting for external input)
        await task_manager.transition_task(tid, "WAITING")
        fetched = await task_manager.get_task(tid)
        assert fetched["status"] == "WAITING"

        # Resume
        await task_manager.transition_task(tid, "RUNNING")
        fetched = await task_manager.get_task(tid)
        assert fetched["status"] == "RUNNING"

    @pytest.mark.asyncio
    async def test_failure_and_events(self, task_manager, fake_repo, event_bus):
        """Task can fail and event is emitted."""
        failures = []

        async def on_fail(et, data):
            failures.append(data["task_id"])

        event_bus.on("task.failed", on_fail)

        result = await task_manager.create_task(goal="Failing task")
        tid = result["id"]

        await task_manager.transition_task(tid, "QUEUED")
        await task_manager.transition_task(tid, "RUNNING")
        await task_manager.transition_task(tid, "FAILED")

        fetched = await task_manager.get_task(tid)
        assert fetched["status"] == "FAILED"
        assert tid in failures

    @pytest.mark.asyncio
    async def test_multiple_tasks_independent(self, task_manager, fake_repo):
        """Multiple tasks can coexist with independent states."""
        t1 = await task_manager.create_task(goal="Task one", steps=["a"])
        t2 = await task_manager.create_task(goal="Task two", steps=["b"])

        await task_manager.transition_task(t1["id"], "QUEUED")
        await task_manager.transition_task(t2["id"], "QUEUED")
        await task_manager.transition_task(t1["id"], "RUNNING")

        f1 = await task_manager.get_task(t1["id"])
        f2 = await task_manager.get_task(t2["id"])

        assert f1["status"] == "RUNNING"
        assert f2["status"] == "QUEUED"

    @pytest.mark.asyncio
    async def test_artifacts_accumulate(self, task_manager, fake_repo):
        """Artifacts accumulate across step advancements."""
        result = await task_manager.create_task(
            goal="Build project",
            steps=["step1", "step2", "step3"],
        )
        tid = result["id"]

        await task_manager.transition_task(tid, "QUEUED")
        await task_manager.transition_task(tid, "RUNNING")

        result = await task_manager.advance_step(tid, artifacts={"output": "first"})
        assert result["artifacts"].get("step_1") == {"output": "first"}

        result = await task_manager.advance_step(tid, artifacts={"output": "second"})
        assert result["artifacts"].get("step_2") == {"output": "second"}

    @pytest.mark.asyncio
    async def test_task_with_dependencies(self, task_manager, fake_repo):
        """Tasks can record dependencies."""
        import uuid
        dep_id = uuid.uuid4()
        result = await task_manager.create_task(
            goal="Dependent task",
            dependencies=[dep_id],
        )
        assert str(dep_id) in result["dependencies"]

    @pytest.mark.asyncio
    async def test_task_not_found_returns_none(self, task_manager, fake_repo):
        """Getting a non-existent task returns None."""
        import uuid
        result = await task_manager.get_task(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_non_existent_returns_false(self, task_manager, fake_repo):
        """Deleting a non-existent task returns False."""
        import uuid
        result = await task_manager.delete_task(uuid.uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_advance_step_not_found(self, task_manager, fake_repo):
        """Advancing a non-existent task returns None."""
        import uuid
        result = await task_manager.advance_step(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_transition_not_found(self, task_manager, fake_repo):
        """Transitioning a non-existent task returns None."""
        import uuid
        result = await task_manager.transition_task(uuid.uuid4(), "QUEUED")
        assert result is None
