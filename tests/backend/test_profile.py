"""Tests for the Profile v1.1 module."""

from __future__ import annotations

import pytest

from app.profile import (
    HistoryManager,
    ObjectivesManager,
    PreferencesManager,
    PrioritiesManager,
    ProfileManager,
    ProjectsManager,
    RoadmapManager,
)
from app.profile.schemas import (
    HistoryEntry,
    Objective,
    PriorityEntry,
    Project,
    Roadmap,
    RoadmapPhase,
    UserPreference,
    UserProfile,
)


# ---------------------------------------------------------------------------
# ProfileManager
# ---------------------------------------------------------------------------


class TestProfileManager:
    @pytest.fixture
    def manager(self) -> ProfileManager:
        return ProfileManager()

    @pytest.mark.asyncio
    async def test_create_profile(self, manager: ProfileManager) -> None:
        p = manager.create_profile("u1", "alice", email="a@b.com", display_name="Alice", role="admin")
        assert p["id"] == "u1"
        assert p["username"] == "alice"
        assert p["email"] == "a@b.com"
        assert p["role"] == "admin"

    @pytest.mark.asyncio
    async def test_get_profile(self, manager: ProfileManager) -> None:
        manager.create_profile("u1", "alice")
        p = manager.get_profile("u1")
        assert p is not None
        assert p["username"] == "alice"

    @pytest.mark.asyncio
    async def test_get_profile_nonexistent(self, manager: ProfileManager) -> None:
        assert manager.get_profile("nope") is None

    @pytest.mark.asyncio
    async def test_update_profile(self, manager: ProfileManager) -> None:
        manager.create_profile("u1", "alice")
        updated = manager.update_profile("u1", username="bob")
        assert updated is not None
        assert updated["username"] == "bob"

    @pytest.mark.asyncio
    async def test_update_profile_nonexistent(self, manager: ProfileManager) -> None:
        assert manager.update_profile("nope", username="x") is None

    @pytest.mark.asyncio
    async def test_delete_profile(self, manager: ProfileManager) -> None:
        manager.create_profile("u1", "alice")
        assert manager.delete_profile("u1") is True
        assert manager.get_profile("u1") is None

    @pytest.mark.asyncio
    async def test_delete_profile_nonexistent(self, manager: ProfileManager) -> None:
        assert manager.delete_profile("nope") is False

    @pytest.mark.asyncio
    async def test_list_profiles(self, manager: ProfileManager) -> None:
        manager.create_profile("u1", "alice")
        manager.create_profile("u2", "bob")
        profiles = manager.list_profiles()
        assert len(profiles) == 2

    @pytest.mark.asyncio
    async def test_list_profiles_empty(self, manager: ProfileManager) -> None:
        assert manager.list_profiles() == []

    @pytest.mark.asyncio
    async def test_to_dict(self, manager: ProfileManager) -> None:
        manager.create_profile("u1", "alice")
        d = manager.to_dict()
        assert "u1" in d


# ---------------------------------------------------------------------------
# PreferencesManager
# ---------------------------------------------------------------------------


class TestPreferencesManager:
    @pytest.fixture
    def manager(self) -> PreferencesManager:
        return PreferencesManager()

    @pytest.mark.asyncio
    async def test_set_preference(self, manager: PreferencesManager) -> None:
        pref = manager.set_preference("u1", "theme", "dark", category="appearance")
        assert pref["key"] == "theme"
        assert pref["value"] == "dark"
        assert pref["category"] == "appearance"

    @pytest.mark.asyncio
    async def test_update_preference(self, manager: PreferencesManager) -> None:
        manager.set_preference("u1", "theme", "dark")
        updated = manager.set_preference("u1", "theme", "light")
        assert updated["value"] == "light"

    @pytest.mark.asyncio
    async def test_get_preference(self, manager: PreferencesManager) -> None:
        manager.set_preference("u1", "theme", "dark")
        assert manager.get_preference("u1", "theme") == "dark"

    @pytest.mark.asyncio
    async def test_get_preference_default(self, manager: PreferencesManager) -> None:
        assert manager.get_preference("u1", "missing", default="fallback") == "fallback"

    @pytest.mark.asyncio
    async def test_get_all_preferences(self, manager: PreferencesManager) -> None:
        manager.set_preference("u1", "a", 1)
        manager.set_preference("u1", "b", 2)
        all_prefs = manager.get_all_preferences("u1")
        assert len(all_prefs) == 2

    @pytest.mark.asyncio
    async def test_get_all_preferences_by_category(self, manager: PreferencesManager) -> None:
        manager.set_preference("u1", "theme", "dark", category="appearance")
        manager.set_preference("u1", "lang", "en", category="locale")
        result = manager.get_all_preferences("u1", category="appearance")
        assert len(result) == 1
        assert result[0]["key"] == "theme"

    @pytest.mark.asyncio
    async def test_delete_preference(self, manager: PreferencesManager) -> None:
        manager.set_preference("u1", "theme", "dark")
        assert manager.delete_preference("u1", "theme") is True
        assert manager.get_preference("u1", "theme") is None

    @pytest.mark.asyncio
    async def test_delete_preference_nonexistent(self, manager: PreferencesManager) -> None:
        assert manager.delete_preference("u1", "missing") is False

    @pytest.mark.asyncio
    async def test_get_categories(self, manager: PreferencesManager) -> None:
        manager.set_preference("u1", "a", 1, category="alpha")
        manager.set_preference("u1", "b", 2, category="beta")
        cats = manager.get_categories("u1")
        assert cats == ["alpha", "beta"]

    @pytest.mark.asyncio
    async def test_to_dict(self, manager: PreferencesManager) -> None:
        manager.set_preference("u1", "a", 1)
        d = manager.to_dict()
        assert "u1" in d


# ---------------------------------------------------------------------------
# ProjectsManager
# ---------------------------------------------------------------------------


class TestProjectsManager:
    @pytest.fixture
    def manager(self) -> ProjectsManager:
        return ProjectsManager()

    @pytest.mark.asyncio
    async def test_create_project(self, manager: ProjectsManager) -> None:
        p = manager.create_project("Nova", description="AI system", owner_id="u1", priority=5, tags=["ai"])
        assert p["name"] == "Nova"
        assert p["owner_id"] == "u1"
        assert "ai" in p["tags"]

    @pytest.mark.asyncio
    async def test_get_project(self, manager: ProjectsManager) -> None:
        p = manager.create_project("X")
        fetched = manager.get_project(p["id"])
        assert fetched is not None
        assert fetched["name"] == "X"

    @pytest.mark.asyncio
    async def test_get_project_nonexistent(self, manager: ProjectsManager) -> None:
        assert manager.get_project("nope") is None

    @pytest.mark.asyncio
    async def test_update_project(self, manager: ProjectsManager) -> None:
        p = manager.create_project("X")
        updated = manager.update_project(p["id"], name="Y")
        assert updated is not None
        assert updated["name"] == "Y"

    @pytest.mark.asyncio
    async def test_update_project_nonexistent(self, manager: ProjectsManager) -> None:
        assert manager.update_project("nope", name="x") is None

    @pytest.mark.asyncio
    async def test_archive_project(self, manager: ProjectsManager) -> None:
        p = manager.create_project("X")
        archived = manager.archive_project(p["id"])
        assert archived is not None
        assert archived["status"] == "archived"

    @pytest.mark.asyncio
    async def test_archive_project_nonexistent(self, manager: ProjectsManager) -> None:
        assert manager.archive_project("nope") is None

    @pytest.mark.asyncio
    async def test_delete_project(self, manager: ProjectsManager) -> None:
        p = manager.create_project("X")
        assert manager.delete_project(p["id"]) is True
        assert manager.get_project(p["id"]) is None

    @pytest.mark.asyncio
    async def test_delete_project_nonexistent(self, manager: ProjectsManager) -> None:
        assert manager.delete_project("nope") is False

    @pytest.mark.asyncio
    async def test_list_projects(self, manager: ProjectsManager) -> None:
        manager.create_project("A")
        manager.create_project("B")
        assert len(manager.list_projects()) == 2

    @pytest.mark.asyncio
    async def test_list_projects_by_status(self, manager: ProjectsManager) -> None:
        p = manager.create_project("A")
        manager.archive_project(p["id"])
        manager.create_project("B")
        assert len(manager.list_projects(status="active")) == 1
        assert len(manager.list_projects(status="archived")) == 1

    @pytest.mark.asyncio
    async def test_list_projects_by_owner(self, manager: ProjectsManager) -> None:
        manager.create_project("A", owner_id="u1")
        manager.create_project("B", owner_id="u2")
        assert len(manager.list_projects(owner_id="u1")) == 1

    @pytest.mark.asyncio
    async def test_to_dict(self, manager: ProjectsManager) -> None:
        manager.create_project("X")
        d = manager.to_dict()
        assert len(d) == 1


# ---------------------------------------------------------------------------
# ObjectivesManager (profile)
# ---------------------------------------------------------------------------


class TestProfileObjectivesManager:
    @pytest.fixture
    def manager(self) -> ObjectivesManager:
        return ObjectivesManager()

    @pytest.mark.asyncio
    async def test_create_objective(self, manager: ObjectivesManager) -> None:
        o = manager.create_objective("Build API", description="REST API", project_id="p1", priority=5)
        assert o["title"] == "Build API"
        assert o["project_id"] == "p1"

    @pytest.mark.asyncio
    async def test_get_objective(self, manager: ObjectivesManager) -> None:
        o = manager.create_objective("X")
        fetched = manager.get_objective(o["id"])
        assert fetched is not None
        assert fetched["title"] == "X"

    @pytest.mark.asyncio
    async def test_get_objective_nonexistent(self, manager: ObjectivesManager) -> None:
        assert manager.get_objective("nope") is None

    @pytest.mark.asyncio
    async def test_update_objective(self, manager: ObjectivesManager) -> None:
        o = manager.create_objective("X")
        updated = manager.update_objective(o["id"], title="Y")
        assert updated is not None
        assert updated["title"] == "Y"

    @pytest.mark.asyncio
    async def test_update_objective_nonexistent(self, manager: ObjectivesManager) -> None:
        assert manager.update_objective("nope", title="x") is None

    @pytest.mark.asyncio
    async def test_complete_objective(self, manager: ObjectivesManager) -> None:
        o = manager.create_objective("X")
        completed = manager.complete_objective(o["id"])
        assert completed is not None
        assert completed["status"] == "completed"
        assert completed["progress"] == 1.0

    @pytest.mark.asyncio
    async def test_complete_objective_nonexistent(self, manager: ObjectivesManager) -> None:
        assert manager.complete_objective("nope") is None

    @pytest.mark.asyncio
    async def test_cancel_objective(self, manager: ObjectivesManager) -> None:
        o = manager.create_objective("X")
        cancelled = manager.cancel_objective(o["id"])
        assert cancelled is not None
        assert cancelled["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_objective_nonexistent(self, manager: ObjectivesManager) -> None:
        assert manager.cancel_objective("nope") is None

    @pytest.mark.asyncio
    async def test_update_progress(self, manager: ObjectivesManager) -> None:
        o = manager.create_objective("X")
        updated = manager.update_progress(o["id"], 0.7)
        assert updated is not None
        assert updated["progress"] == 0.7

    @pytest.mark.asyncio
    async def test_update_progress_clamped(self, manager: ObjectivesManager) -> None:
        o = manager.create_objective("X")
        manager.update_progress(o["id"], 2.0)
        fetched = manager.get_objective(o["id"])
        assert fetched["progress"] == 1.0
        manager.update_progress(o["id"], -1.0)
        fetched = manager.get_objective(o["id"])
        assert fetched["progress"] == 0.0

    @pytest.mark.asyncio
    async def test_update_progress_nonexistent(self, manager: ObjectivesManager) -> None:
        assert manager.update_progress("nope", 0.5) is None

    @pytest.mark.asyncio
    async def test_list_objectives(self, manager: ObjectivesManager) -> None:
        manager.create_objective("A")
        manager.create_objective("B")
        assert len(manager.list_objectives()) == 2

    @pytest.mark.asyncio
    async def test_list_objectives_by_status(self, manager: ObjectivesManager) -> None:
        o = manager.create_objective("A")
        manager.complete_objective(o["id"])
        manager.create_objective("B")
        assert len(manager.list_objectives(status="completed")) == 1
        assert len(manager.list_objectives(status="active")) == 1

    @pytest.mark.asyncio
    async def test_list_objectives_by_project(self, manager: ObjectivesManager) -> None:
        manager.create_objective("A", project_id="p1")
        manager.create_objective("B", project_id="p2")
        assert len(manager.list_objectives(project_id="p1")) == 1

    @pytest.mark.asyncio
    async def test_to_dict(self, manager: ObjectivesManager) -> None:
        manager.create_objective("X")
        d = manager.to_dict()
        assert len(d) == 1


# ---------------------------------------------------------------------------
# PrioritiesManager (profile)
# ---------------------------------------------------------------------------


class TestProfilePrioritiesManager:
    @pytest.fixture
    def manager(self) -> PrioritiesManager:
        return PrioritiesManager()

    @pytest.mark.asyncio
    async def test_create_priority(self, manager: PrioritiesManager) -> None:
        p = manager.create_priority("P0", level=0, description="Critical")
        assert p["name"] == "P0"
        assert p["level"] == 0

    @pytest.mark.asyncio
    async def test_get_priority(self, manager: PrioritiesManager) -> None:
        p = manager.create_priority("P1", 1)
        fetched = manager.get_priority(p["id"])
        assert fetched is not None
        assert fetched["level"] == 1

    @pytest.mark.asyncio
    async def test_get_priority_nonexistent(self, manager: PrioritiesManager) -> None:
        assert manager.get_priority("nope") is None

    @pytest.mark.asyncio
    async def test_update_priority(self, manager: PrioritiesManager) -> None:
        p = manager.create_priority("X", 1)
        updated = manager.update_priority(p["id"], level=9)
        assert updated is not None
        assert updated["level"] == 9

    @pytest.mark.asyncio
    async def test_update_priority_nonexistent(self, manager: PrioritiesManager) -> None:
        assert manager.update_priority("nope", level=1) is None

    @pytest.mark.asyncio
    async def test_delete_priority(self, manager: PrioritiesManager) -> None:
        p = manager.create_priority("X", 1)
        assert manager.delete_priority(p["id"]) is True
        assert manager.get_priority(p["id"]) is None

    @pytest.mark.asyncio
    async def test_delete_priority_nonexistent(self, manager: PrioritiesManager) -> None:
        assert manager.delete_priority("nope") is False

    @pytest.mark.asyncio
    async def test_list_priorities_sorted(self, manager: PrioritiesManager) -> None:
        manager.create_priority("Low", 1)
        manager.create_priority("High", 10)
        manager.create_priority("Med", 5)
        items = manager.list_priorities()
        assert items[0]["level"] >= items[1]["level"] >= items[2]["level"]

    @pytest.mark.asyncio
    async def test_get_top(self, manager: PrioritiesManager) -> None:
        for i in range(5):
            manager.create_priority(f"P{i}", i)
        top = manager.get_top(n=2)
        assert len(top) == 2
        assert top[0]["level"] >= top[1]["level"]

    @pytest.mark.asyncio
    async def test_get_top_empty(self, manager: PrioritiesManager) -> None:
        assert manager.get_top() == []

    @pytest.mark.asyncio
    async def test_to_dict(self, manager: PrioritiesManager) -> None:
        manager.create_priority("X", 1)
        d = manager.to_dict()
        assert len(d) == 1


# ---------------------------------------------------------------------------
# HistoryManager
# ---------------------------------------------------------------------------


class TestHistoryManager:
    @pytest.fixture
    def manager(self) -> HistoryManager:
        return HistoryManager()

    @pytest.mark.asyncio
    async def test_record(self, manager: HistoryManager) -> None:
        entry = manager.record("login", {"ip": "127.0.0.1"})
        assert entry["action"] == "login"
        assert entry["details"]["ip"] == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_record_no_details(self, manager: HistoryManager) -> None:
        entry = manager.record("click")
        assert entry["details"] == {}

    @pytest.mark.asyncio
    async def test_get_history(self, manager: HistoryManager) -> None:
        manager.record("a")
        manager.record("b")
        manager.record("c")
        history = manager.get_history(limit=2)
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_history_by_action(self, manager: HistoryManager) -> None:
        manager.record("login")
        manager.record("click")
        manager.record("login")
        result = manager.get_history(action="login")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_recent(self, manager: HistoryManager) -> None:
        for i in range(5):
            manager.record(f"action_{i}")
        recent = manager.get_recent(limit=3)
        assert len(recent) == 3
        assert recent[0]["action"] == "action_2"

    @pytest.mark.asyncio
    async def test_clear(self, manager: HistoryManager) -> None:
        manager.record("a")
        manager.record("b")
        count = manager.clear()
        assert count == 2
        assert manager.get_history() == []

    @pytest.mark.asyncio
    async def test_clear_empty(self, manager: HistoryManager) -> None:
        assert manager.clear() == 0

    @pytest.mark.asyncio
    async def test_stats(self, manager: HistoryManager) -> None:
        manager.record("login")
        manager.record("login")
        manager.record("click")
        s = manager.stats()
        assert s["total"] == 3
        assert s["actions"]["login"] == 2
        assert s["actions"]["click"] == 1

    @pytest.mark.asyncio
    async def test_stats_empty(self, manager: HistoryManager) -> None:
        s = manager.stats()
        assert s["total"] == 0

    @pytest.mark.asyncio
    async def test_max_entries_cap(self, manager: HistoryManager) -> None:
        mgr = HistoryManager(max_entries=5)
        for i in range(10):
            mgr.record(f"a{i}")
        assert len(mgr.entries) == 5

    @pytest.mark.asyncio
    async def test_to_dict(self, manager: HistoryManager) -> None:
        manager.record("a")
        d = manager.to_dict()
        assert "max_entries" in d
        assert "entries" in d
        assert len(d["entries"]) == 1


# ---------------------------------------------------------------------------
# RoadmapManager (profile)
# ---------------------------------------------------------------------------


class TestProfileRoadmapManager:
    @pytest.fixture
    def manager(self) -> RoadmapManager:
        return RoadmapManager()

    @pytest.mark.asyncio
    async def test_create_roadmap(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("Q4 Plan", description="End of year")
        assert r["name"] == "Q4 Plan"
        assert r["description"] == "End of year"
        assert r["status"] == "draft"

    @pytest.mark.asyncio
    async def test_create_roadmap_with_phases(self, manager: RoadmapManager) -> None:
        phase = RoadmapPhase(title="Phase 1", order=0)
        r = manager.create_roadmap("Plan", phases=[phase])
        assert len(r["phases"]) == 1

    @pytest.mark.asyncio
    async def test_get_roadmap(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        fetched = manager.get_roadmap(r["id"])
        assert fetched is not None
        assert fetched["name"] == "X"

    @pytest.mark.asyncio
    async def test_get_roadmap_nonexistent(self, manager: RoadmapManager) -> None:
        assert manager.get_roadmap("nope") is None

    @pytest.mark.asyncio
    async def test_update_roadmap(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        updated = manager.update_roadmap(r["id"], name="Y")
        assert updated is not None
        assert updated["name"] == "Y"

    @pytest.mark.asyncio
    async def test_update_roadmap_nonexistent(self, manager: RoadmapManager) -> None:
        assert manager.update_roadmap("nope", name="x") is None

    @pytest.mark.asyncio
    async def test_delete_roadmap(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        assert manager.delete_roadmap(r["id"]) is True
        assert manager.get_roadmap(r["id"]) is None

    @pytest.mark.asyncio
    async def test_delete_roadmap_nonexistent(self, manager: RoadmapManager) -> None:
        assert manager.delete_roadmap("nope") is False

    @pytest.mark.asyncio
    async def test_list_roadmaps(self, manager: RoadmapManager) -> None:
        manager.create_roadmap("A")
        manager.create_roadmap("B")
        assert len(manager.list_roadmaps()) == 2

    @pytest.mark.asyncio
    async def test_list_roadmaps_by_status(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("A")
        manager.update_roadmap(r["id"], status="active")
        manager.create_roadmap("B")
        assert len(manager.list_roadmaps(status="active")) == 1
        assert len(manager.list_roadmaps(status="draft")) == 1

    @pytest.mark.asyncio
    async def test_add_phase(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        result = manager.add_phase(r["id"], "Phase 1", description="First", duration_months=3, order=0)
        assert result is not None
        assert len(result["phases"]) == 1
        assert result["phases"][0]["title"] == "Phase 1"

    @pytest.mark.asyncio
    async def test_add_phase_auto_order(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        manager.add_phase(r["id"], "Phase 1")
        result = manager.add_phase(r["id"], "Phase 2")
        assert result is not None
        assert result["phases"][1]["title"] == "Phase 2"

    @pytest.mark.asyncio
    async def test_add_phase_nonexistent_roadmap(self, manager: RoadmapManager) -> None:
        assert manager.add_phase("nope", "Phase") is None

    @pytest.mark.asyncio
    async def test_complete_phase(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        result_with_phase = manager.add_phase(r["id"], "Phase 1")
        phase_id = result_with_phase["phases"][0]["id"]
        completed = manager.complete_phase(r["id"], phase_id)
        assert completed is not None
        assert completed["phases"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_complete_phase_nonexistent_roadmap(self, manager: RoadmapManager) -> None:
        assert manager.complete_phase("nope", "phase_id") is None

    @pytest.mark.asyncio
    async def test_complete_phase_nonexistent_phase(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        assert manager.complete_phase(r["id"], "bad-phase") is None

    @pytest.mark.asyncio
    async def test_update_phase(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        r2 = manager.add_phase(r["id"], "Phase 1")
        phase_id = r2["phases"][0]["id"]
        updated = manager.update_phase(r["id"], phase_id, title="Updated Phase")
        assert updated is not None
        assert updated["phases"][0]["title"] == "Updated Phase"

    @pytest.mark.asyncio
    async def test_update_phase_nonexistent_roadmap(self, manager: RoadmapManager) -> None:
        assert manager.update_phase("nope", "pid", title="X") is None

    @pytest.mark.asyncio
    async def test_update_phase_nonexistent_phase(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        assert manager.update_phase(r["id"], "bad", title="X") is None

    @pytest.mark.asyncio
    async def test_to_dict(self, manager: RoadmapManager) -> None:
        manager.create_roadmap("X")
        d = manager.to_dict()
        assert len(d) == 1


# ---------------------------------------------------------------------------
# Schema dataclass basics
# ---------------------------------------------------------------------------


class TestProfileSchemas:
    @pytest.mark.asyncio
    async def test_user_profile_defaults(self) -> None:
        p = UserProfile()
        assert p.role == "user"
        assert p.preferences == {}

    @pytest.mark.asyncio
    async def test_user_profile_to_dict(self) -> None:
        p = UserProfile(id="u1", username="alice")
        d = p.to_dict()
        assert d["id"] == "u1"
        assert d["username"] == "alice"
        assert "created_at" in d

    @pytest.mark.asyncio
    async def test_user_preference_defaults(self) -> None:
        up = UserPreference()
        assert up.category == "general"

    @pytest.mark.asyncio
    async def test_project_defaults(self) -> None:
        proj = Project()
        assert proj.status == "active"
        assert proj.priority == 3
        assert proj.tags == []

    @pytest.mark.asyncio
    async def test_objective_defaults(self) -> None:
        obj = Objective()
        assert obj.status == "active"
        assert obj.progress == 0.0

    @pytest.mark.asyncio
    async def test_priority_entry_defaults(self) -> None:
        pe = PriorityEntry()
        assert pe.level == 3
        assert pe.active is True

    @pytest.mark.asyncio
    async def test_history_entry_defaults(self) -> None:
        he = HistoryEntry()
        assert he.action == ""
        assert he.details == {}

    @pytest.mark.asyncio
    async def test_roadmap_phase_defaults(self) -> None:
        rp = RoadmapPhase()
        assert rp.status == "pending"
        assert rp.objectives == []

    @pytest.mark.asyncio
    async def test_roadmap_defaults(self) -> None:
        r = Roadmap()
        assert r.status == "draft"
        assert r.phases == []

    @pytest.mark.asyncio
    async def test_roadmap_to_dict_includes_phases(self) -> None:
        phase = RoadmapPhase(title="P1")
        r = Roadmap(name="R1", phases=[phase])
        d = r.to_dict()
        assert len(d["phases"]) == 1
        assert d["phases"][0]["title"] == "P1"
