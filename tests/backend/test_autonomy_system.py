"""Tests for the Autonomy v1.1 system module."""

from __future__ import annotations

import pytest

from app.autonomy import (
    ApprovalEngine,
    AutonomyEngine,
    DelegationEngine,
    ObjectiveManager,
    OptimizationEngine,
    ProjectManager,
    RecommendationEngine,
    ResearchManager,
    RoadmapManager,
    SelfImprovementEngine,
)
from app.autonomy.schemas import (
    DelegationTask,
    ObjectivePlan,
    OptimizationResult,
    ProjectOrchestration,
    Recommendation,
    ResearchQuery,
    SelfImprovementItem,
)


# ---------------------------------------------------------------------------
# AutonomyEngine
# ---------------------------------------------------------------------------


class TestAutonomyEngine:
    @pytest.fixture
    def engine(self) -> AutonomyEngine:
        return AutonomyEngine()

    @pytest.mark.asyncio
    async def test_default_level(self, engine: AutonomyEngine) -> None:
        assert engine.get_level() == 0.5

    @pytest.mark.asyncio
    async def test_set_level(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.9)
        assert engine.get_level() == 0.9

    @pytest.mark.asyncio
    async def test_set_level_clamped_high(self, engine: AutonomyEngine) -> None:
        engine.set_level(5.0)
        assert engine.get_level() == 1.0

    @pytest.mark.asyncio
    async def test_set_level_clamped_low(self, engine: AutonomyEngine) -> None:
        engine.set_level(-5.0)
        assert engine.get_level() == 0.0

    @pytest.mark.asyncio
    async def test_can_autonomously_low_risk(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.5)
        assert engine.can_autonomously("read") is True

    @pytest.mark.asyncio
    async def test_can_autonomously_medium_risk(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.5)
        assert engine.can_autonomously("execute_task") is True

    @pytest.mark.asyncio
    async def test_can_autonomously_high_risk(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.5)
        assert engine.can_autonomously("modify_code") is False

    @pytest.mark.asyncio
    async def test_can_autonomously_critical_risk(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.8)
        assert engine.can_autonomously("system_modification") is False

    @pytest.mark.asyncio
    async def test_can_autonomously_full_level(self, engine: AutonomyEngine) -> None:
        engine.set_level(1.0)
        assert engine.can_autonomously("system_modification") is True

    @pytest.mark.asyncio
    async def test_can_autonomously_unknown_action(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.5)
        assert engine.can_autonomously("unknown_action") is True

    @pytest.mark.asyncio
    async def test_requires_approval(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.5)
        assert engine.requires_approval("read") is False
        assert engine.requires_approval("modify_code") is True

    @pytest.mark.asyncio
    async def test_get_capabilities_level_0(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.0)
        assert engine.get_capabilities() == []

    @pytest.mark.asyncio
    async def test_get_capabilities_level_01(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.1)
        caps = engine.get_capabilities()
        assert "read" in caps
        assert "analyze" in caps
        assert "research" in caps

    @pytest.mark.asyncio
    async def test_get_capabilities_level_03(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.3)
        caps = engine.get_capabilities()
        assert "recommend" in caps

    @pytest.mark.asyncio
    async def test_get_capabilities_level_05(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.5)
        caps = engine.get_capabilities()
        assert "execute_task" in caps
        assert "delegate" in caps
        assert "create_project" in caps

    @pytest.mark.asyncio
    async def test_get_capabilities_level_08(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.8)
        caps = engine.get_capabilities()
        assert "modify_code" in caps
        assert "self_improve" in caps

    @pytest.mark.asyncio
    async def test_get_capabilities_level_10(self, engine: AutonomyEngine) -> None:
        engine.set_level(1.0)
        caps = engine.get_capabilities()
        assert "system_modification" in caps

    @pytest.mark.asyncio
    async def test_evaluate_action(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.5)
        result = engine.evaluate_action("read", "low")
        assert result["allowed"] is True
        assert result["requires_approval"] is False
        assert "within autonomy bounds" in result["reason"]

    @pytest.mark.asyncio
    async def test_evaluate_action_disallowed(self, engine: AutonomyEngine) -> None:
        engine.set_level(0.3)
        result = engine.evaluate_action("modify_code", "high")
        assert result["allowed"] is False
        assert result["requires_approval"] is True
        assert "exceeds autonomy bounds" in result["reason"]

    @pytest.mark.asyncio
    async def test_to_dict(self, engine: AutonomyEngine) -> None:
        d = engine.to_dict()
        assert "level" in d
        assert "capabilities" in d
        assert "action_risks" in d


# ---------------------------------------------------------------------------
# ObjectiveManager (autonomy)
# ---------------------------------------------------------------------------


class TestAutonomyObjectiveManager:
    @pytest.fixture
    def manager(self) -> ObjectiveManager:
        return ObjectiveManager(max_active=3)

    @pytest.mark.asyncio
    async def test_analyze_objective_feature(self, manager: ObjectiveManager) -> None:
        result = manager.analyze_objective("Implement a new login feature")
        assert result["category"] == "feature"
        assert result["complexity"] == "low"

    @pytest.mark.asyncio
    async def test_analyze_objective_optimization(self, manager: ObjectiveManager) -> None:
        result = manager.analyze_objective("Optimize performance of the database")
        assert result["category"] == "optimization"

    @pytest.mark.asyncio
    async def test_analyze_objective_security(self, manager: ObjectiveManager) -> None:
        result = manager.analyze_objective("Add authentication and auth checks")
        assert result["category"] == "security"

    @pytest.mark.asyncio
    async def test_analyze_objective_refactoring(self, manager: ObjectiveManager) -> None:
        result = manager.analyze_objective("Refactor and clean up the codebase")
        assert result["category"] == "refactoring"

    @pytest.mark.asyncio
    async def test_analyze_objective_bugfix(self, manager: ObjectiveManager) -> None:
        result = manager.analyze_objective("Fix the login bug and patch error")
        assert result["category"] == "bugfix"

    @pytest.mark.asyncio
    async def test_analyze_objective_general(self, manager: ObjectiveManager) -> None:
        result = manager.analyze_objective("Do something")
        assert result["category"] == "general"

    @pytest.mark.asyncio
    async def test_analyze_complexity_low(self, manager: ObjectiveManager) -> None:
        result = manager.analyze_objective("Short text")
        assert result["complexity"] == "low"

    @pytest.mark.asyncio
    async def test_analyze_complexity_medium(self, manager: ObjectiveManager) -> None:
        text = " ".join(["word"] * 20)
        result = manager.analyze_objective(text)
        assert result["complexity"] == "medium"

    @pytest.mark.asyncio
    async def test_analyze_complexity_high(self, manager: ObjectiveManager) -> None:
        text = " ".join(["word"] * 40)
        result = manager.analyze_objective(text)
        assert result["complexity"] == "high"

    @pytest.mark.asyncio
    async def test_create_plan(self, manager: ObjectiveManager) -> None:
        analysis = manager.analyze_objective("Implement feature X")
        plan = manager.create_plan("Implement feature X", analysis)
        assert isinstance(plan, ObjectivePlan)
        assert plan.title == "Implement feature X"
        assert len(plan.milestones) > 0
        assert len(plan.tasks) > 0

    @pytest.mark.asyncio
    async def test_create_plan_high_complexity(self, manager: ObjectiveManager) -> None:
        text = " ".join(["word"] * 40)
        analysis = manager.analyze_objective(text)
        plan = manager.create_plan(text, analysis)
        assert len(plan.tasks) == 8
        assert plan.requires_human_approval is True

    @pytest.mark.asyncio
    async def test_add_objective_active(self, manager: ObjectiveManager) -> None:
        obj = manager.add_objective("Obj1", "Desc1")
        assert obj["status"] == "active"
        assert len(manager.list_active()) == 1

    @pytest.mark.asyncio
    async def test_add_objective_backlog(self, manager: ObjectiveManager) -> None:
        for i in range(4):
            manager.add_objective(f"O{i}", f"D{i}")
        assert len(manager.list_active()) == 3
        assert len(manager.list_backlog()) == 1

    @pytest.mark.asyncio
    async def test_update_objective(self, manager: ObjectiveManager) -> None:
        obj = manager.add_objective("X", "x")
        updated = manager.update_objective(obj["id"], title="Y")
        assert updated is not None
        assert updated["title"] == "Y"

    @pytest.mark.asyncio
    async def test_update_objective_backlog(self, manager: ObjectiveManager) -> None:
        for i in range(4):
            manager.add_objective(f"O{i}", f"D{i}")
        backlog = manager.list_backlog()
        updated = manager.update_objective(backlog[0]["id"], title="Updated")
        assert updated is not None
        assert updated["title"] == "Updated"

    @pytest.mark.asyncio
    async def test_update_objective_nonexistent(self, manager: ObjectiveManager) -> None:
        assert manager.update_objective("nope", title="x") is None

    @pytest.mark.asyncio
    async def test_complete_objective(self, manager: ObjectiveManager) -> None:
        obj = manager.add_objective("X", "x")
        completed = manager.complete_objective(obj["id"])
        assert completed is not None
        assert completed["status"] == "completed"
        assert "completed_at" in completed

    @pytest.mark.asyncio
    async def test_complete_objective_promotes(self, manager: ObjectiveManager) -> None:
        for i in range(4):
            manager.add_objective(f"O{i}", f"D{i}")
        active_ids = [o["id"] for o in manager.list_active()]
        manager.complete_objective(active_ids[0])
        assert len(manager.list_active()) == 3
        assert len(manager.list_backlog()) == 0

    @pytest.mark.asyncio
    async def test_complete_objective_nonexistent(self, manager: ObjectiveManager) -> None:
        assert manager.complete_objective("nope") is None

    @pytest.mark.asyncio
    async def test_promote_from_backlog(self, manager: ObjectiveManager) -> None:
        for i in range(4):
            manager.add_objective(f"O{i}", f"D{i}")
        active_ids = [o["id"] for o in manager.list_active()]
        manager.update_objective(active_ids[0], status="completed")
        manager._objectives.pop(active_ids[0])
        backlog_id = manager.list_backlog()[0]["id"]
        promoted = manager.promote_from_backlog(backlog_id)
        assert promoted is not None
        assert promoted["status"] == "active"

    @pytest.mark.asyncio
    async def test_promote_from_backlog_full(self, manager: ObjectiveManager) -> None:
        for i in range(3):
            manager.add_objective(f"O{i}", f"D{i}")
        for i in range(2):
            manager.add_objective(f"B{i}", f"Bd{i}")
        backlog_id = manager.list_backlog()[0]["id"]
        assert manager.promote_from_backlog(backlog_id) is None

    @pytest.mark.asyncio
    async def test_promote_nonexistent(self, manager: ObjectiveManager) -> None:
        assert manager.promote_from_backlog("nope") is None

    @pytest.mark.asyncio
    async def test_list_active(self, manager: ObjectiveManager) -> None:
        manager.add_objective("A", "a")
        assert len(manager.list_active()) == 1

    @pytest.mark.asyncio
    async def test_list_backlog(self, manager: ObjectiveManager) -> None:
        for i in range(4):
            manager.add_objective(f"O{i}", f"D{i}")
        assert len(manager.list_backlog()) == 1

    @pytest.mark.asyncio
    async def test_to_dict(self, manager: ObjectiveManager) -> None:
        manager.add_objective("X", "x")
        d = manager.to_dict()
        assert "max_active" in d
        assert "objectives" in d
        assert "backlog" in d


# ---------------------------------------------------------------------------
# ProjectManager (autonomy)
# ---------------------------------------------------------------------------


class TestAutonomyProjectManager:
    @pytest.fixture
    def manager(self) -> ProjectManager:
        return ProjectManager()

    @pytest.mark.asyncio
    async def test_create_project(self, manager: ProjectManager) -> None:
        project = manager.create_project("Build a REST API for user management")
        assert project["objective"] == "Build a REST API for user management"
        assert project["status"] == "analyzing"
        assert project["progress"] == 0.0
        assert "plan" in project
        assert "analysis" in project

    @pytest.mark.asyncio
    async def test_get_project(self, manager: ProjectManager) -> None:
        project = manager.create_project("Test project")
        fetched = manager.get_project(project["id"])
        assert fetched is not None
        assert fetched["id"] == project["id"]

    @pytest.mark.asyncio
    async def test_get_project_nonexistent(self, manager: ProjectManager) -> None:
        assert manager.get_project("nope") is None

    @pytest.mark.asyncio
    async def test_update_project(self, manager: ProjectManager) -> None:
        project = manager.create_project("Test")
        updated = manager.update_project(project["id"], status="in_progress", progress=0.5)
        assert updated is not None
        assert updated["status"] == "in_progress"
        assert updated["progress"] == 0.5

    @pytest.mark.asyncio
    async def test_update_project_nonexistent(self, manager: ProjectManager) -> None:
        assert manager.update_project("nope", status="x") is None

    @pytest.mark.asyncio
    async def test_list_projects(self, manager: ProjectManager) -> None:
        manager.create_project("A")
        manager.create_project("B")
        assert len(manager.list_projects()) == 2

    @pytest.mark.asyncio
    async def test_list_projects_by_status(self, manager: ProjectManager) -> None:
        p = manager.create_project("A")
        manager.update_project(p["id"], status="completed")
        manager.create_project("B")
        assert len(manager.list_projects(status="completed")) == 1
        assert len(manager.list_projects(status="analyzing")) == 1

    @pytest.mark.asyncio
    async def test_get_project_status(self, manager: ProjectManager) -> None:
        project = manager.create_project("Test")
        status = manager.get_project_status(project["id"])
        assert status is not None
        assert status["status"] == "analyzing"
        assert "tasks_completed" in status
        assert "tasks_total" in status

    @pytest.mark.asyncio
    async def test_get_project_status_nonexistent(self, manager: ProjectManager) -> None:
        assert manager.get_project_status("nope") is None

    @pytest.mark.asyncio
    async def test_to_dict(self, manager: ProjectManager) -> None:
        manager.create_project("X")
        d = manager.to_dict()
        assert "projects" in d


# ---------------------------------------------------------------------------
# RoadmapManager (autonomy)
# ---------------------------------------------------------------------------


class TestAutonomyRoadmapManager:
    @pytest.fixture
    def manager(self) -> RoadmapManager:
        return RoadmapManager()

    @pytest.mark.asyncio
    async def test_create_roadmap(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("Build AI platform", duration_years=1)
        assert r["objective"] == "Build AI platform"
        assert r["duration_years"] == 1
        assert r["status"] == "active"
        assert len(r["phases"]) > 0

    @pytest.mark.asyncio
    async def test_create_roadmap_phases(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X", duration_years=2)
        assert len(r["phases"]) == 5
        assert r["phases"][0]["title"] == "Discovery & Research"

    @pytest.mark.asyncio
    async def test_get_roadmap(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        fetched = manager.get_roadmap(r["id"])
        assert fetched is not None

    @pytest.mark.asyncio
    async def test_get_roadmap_nonexistent(self, manager: RoadmapManager) -> None:
        assert manager.get_roadmap("nope") is None

    @pytest.mark.asyncio
    async def test_update_roadmap(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        updated = manager.update_roadmap(r["id"], status="completed")
        assert updated is not None
        assert updated["status"] == "completed"

    @pytest.mark.asyncio
    async def test_update_roadmap_nonexistent(self, manager: RoadmapManager) -> None:
        assert manager.update_roadmap("nope", status="x") is None

    @pytest.mark.asyncio
    async def test_list_roadmaps(self, manager: RoadmapManager) -> None:
        manager.create_roadmap("A")
        manager.create_roadmap("B")
        assert len(manager.list_roadmaps()) == 2

    @pytest.mark.asyncio
    async def test_add_phase(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        phase = manager.add_phase(r["id"], "Custom Phase", description="Extra", duration_months=4)
        assert phase is not None
        assert phase["title"] == "Custom Phase"
        assert phase["duration_months"] == 4

    @pytest.mark.asyncio
    async def test_add_phase_nonexistent(self, manager: RoadmapManager) -> None:
        assert manager.add_phase("nope", "Phase") is None

    @pytest.mark.asyncio
    async def test_complete_phase(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        phase_id = r["phases"][0]["id"]
        completed = manager.complete_phase(r["id"], phase_id)
        assert completed is not None
        assert completed["status"] == "completed"
        assert "completed_at" in completed

    @pytest.mark.asyncio
    async def test_complete_phase_nonexistent_roadmap(self, manager: RoadmapManager) -> None:
        assert manager.complete_phase("nope", "pid") is None

    @pytest.mark.asyncio
    async def test_complete_phase_nonexistent_phase(self, manager: RoadmapManager) -> None:
        r = manager.create_roadmap("X")
        assert manager.complete_phase(r["id"], "bad-phase") is None

    @pytest.mark.asyncio
    async def test_to_dict(self, manager: RoadmapManager) -> None:
        manager.create_roadmap("X")
        d = manager.to_dict()
        assert "roadmaps" in d


# ---------------------------------------------------------------------------
# RecommendationEngine
# ---------------------------------------------------------------------------


class TestRecommendationEngine:
    @pytest.fixture
    def engine(self) -> RecommendationEngine:
        return RecommendationEngine()

    @pytest.mark.asyncio
    async def test_generate_recommendation(self, engine: RecommendationEngine) -> None:
        rec = engine.generate_recommendation(
            category="performance",
            title="Add caching",
            description="Implement Redis caching for API responses",
            priority="high",
            impact="Reduce latency by 50%",
            effort="Medium",
        )
        assert rec["title"] == "Add caching"
        assert rec["priority"] == "high"
        assert rec["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_recommendation(self, engine: RecommendationEngine) -> None:
        rec = engine.generate_recommendation("perf", "X", "x")
        fetched = engine.get_recommendation(rec["id"])
        assert fetched is not None
        assert fetched["title"] == "X"

    @pytest.mark.asyncio
    async def test_get_recommendation_nonexistent(self, engine: RecommendationEngine) -> None:
        assert engine.get_recommendation("nope") is None

    @pytest.mark.asyncio
    async def test_list_recommendations(self, engine: RecommendationEngine) -> None:
        engine.generate_recommendation("a", "A", "a")
        engine.generate_recommendation("b", "B", "b")
        assert len(engine.list_recommendations()) == 2

    @pytest.mark.asyncio
    async def test_list_recommendations_by_status(self, engine: RecommendationEngine) -> None:
        rec = engine.generate_recommendation("a", "A", "a")
        engine.accept_recommendation(rec["id"])
        engine.generate_recommendation("b", "B", "b")
        assert len(engine.list_recommendations(status="accepted")) == 1
        assert len(engine.list_recommendations(status="pending")) == 1

    @pytest.mark.asyncio
    async def test_list_recommendations_by_category(self, engine: RecommendationEngine) -> None:
        engine.generate_recommendation("perf", "A", "a")
        engine.generate_recommendation("sec", "B", "b")
        assert len(engine.list_recommendations(category="perf")) == 1

    @pytest.mark.asyncio
    async def test_accept_recommendation(self, engine: RecommendationEngine) -> None:
        rec = engine.generate_recommendation("a", "X", "x")
        accepted = engine.accept_recommendation(rec["id"])
        assert accepted is not None
        assert accepted["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_accept_recommendation_nonexistent(self, engine: RecommendationEngine) -> None:
        assert engine.accept_recommendation("nope") is None

    @pytest.mark.asyncio
    async def test_accept_recommendation_not_pending(self, engine: RecommendationEngine) -> None:
        rec = engine.generate_recommendation("a", "X", "x")
        engine.accept_recommendation(rec["id"])
        assert engine.accept_recommendation(rec["id"]) is None

    @pytest.mark.asyncio
    async def test_reject_recommendation(self, engine: RecommendationEngine) -> None:
        rec = engine.generate_recommendation("a", "X", "x")
        rejected = engine.reject_recommendation(rec["id"])
        assert rejected is not None
        assert rejected["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_reject_recommendation_nonexistent(self, engine: RecommendationEngine) -> None:
        assert engine.reject_recommendation("nope") is None

    @pytest.mark.asyncio
    async def test_reject_recommendation_not_pending(self, engine: RecommendationEngine) -> None:
        rec = engine.generate_recommendation("a", "X", "x")
        engine.reject_recommendation(rec["id"])
        assert engine.reject_recommendation(rec["id"]) is None

    @pytest.mark.asyncio
    async def test_implement_recommendation(self, engine: RecommendationEngine) -> None:
        rec = engine.generate_recommendation("a", "X", "x")
        impl = engine.implement_recommendation(rec["id"])
        assert impl is not None
        assert impl["status"] == "implemented"

    @pytest.mark.asyncio
    async def test_implement_from_accepted(self, engine: RecommendationEngine) -> None:
        rec = engine.generate_recommendation("a", "X", "x")
        engine.accept_recommendation(rec["id"])
        impl = engine.implement_recommendation(rec["id"])
        assert impl is not None
        assert impl["status"] == "implemented"

    @pytest.mark.asyncio
    async def test_implement_nonexistent(self, engine: RecommendationEngine) -> None:
        assert engine.implement_recommendation("nope") is None

    @pytest.mark.asyncio
    async def test_implement_rejected(self, engine: RecommendationEngine) -> None:
        rec = engine.generate_recommendation("a", "X", "x")
        engine.reject_recommendation(rec["id"])
        assert engine.implement_recommendation(rec["id"]) is None

    @pytest.mark.asyncio
    async def test_get_pending(self, engine: RecommendationEngine) -> None:
        engine.generate_recommendation("a", "A", "a")
        engine.generate_recommendation("b", "B", "b")
        rec = engine.generate_recommendation("c", "C", "c")
        engine.accept_recommendation(rec["id"])
        assert len(engine.get_pending()) == 2

    @pytest.mark.asyncio
    async def test_to_dict(self, engine: RecommendationEngine) -> None:
        engine.generate_recommendation("a", "X", "x")
        d = engine.to_dict()
        assert "recommendations" in d


# ---------------------------------------------------------------------------
# OptimizationEngine
# ---------------------------------------------------------------------------


class TestOptimizationEngine:
    @pytest.fixture
    def engine(self) -> OptimizationEngine:
        return OptimizationEngine()

    @pytest.mark.asyncio
    async def test_analyze(self, engine: OptimizationEngine) -> None:
        result = engine.analyze(
            category="performance",
            current_state="No caching",
            proposed_state="Redis caching",
            improvement="50% latency reduction",
            priority=8,
            estimated_impact="high",
        )
        assert result["category"] == "performance"
        assert result["priority"] == 8
        assert result["estimated_impact"] == "high"

    @pytest.mark.asyncio
    async def test_get_result(self, engine: OptimizationEngine) -> None:
        result = engine.analyze("cat", "cur", "prop", "imp")
        fetched = engine.get_result(result["id"])
        assert fetched is not None

    @pytest.mark.asyncio
    async def test_get_result_nonexistent(self, engine: OptimizationEngine) -> None:
        assert engine.get_result("nope") is None

    @pytest.mark.asyncio
    async def test_list_results(self, engine: OptimizationEngine) -> None:
        engine.analyze("a", "c", "p", "i")
        engine.analyze("b", "c", "p", "i")
        assert len(engine.list_results()) == 2

    @pytest.mark.asyncio
    async def test_list_results_by_category(self, engine: OptimizationEngine) -> None:
        engine.analyze("perf", "c", "p", "i")
        engine.analyze("sec", "c", "p", "i")
        assert len(engine.list_results(category="perf")) == 1

    @pytest.mark.asyncio
    async def test_prioritize(self, engine: OptimizationEngine) -> None:
        engine.analyze("a", "c", "p", "i", priority=1)
        engine.analyze("b", "c", "p", "i", priority=10)
        engine.analyze("c", "c", "p", "i", priority=5)
        prioritized = engine.prioritize()
        assert prioritized[0]["priority"] >= prioritized[1]["priority"] >= prioritized[2]["priority"]

    @pytest.mark.asyncio
    async def test_to_dict(self, engine: OptimizationEngine) -> None:
        engine.analyze("a", "c", "p", "i")
        d = engine.to_dict()
        assert "results" in d


# ---------------------------------------------------------------------------
# SelfImprovementEngine
# ---------------------------------------------------------------------------


class TestSelfImprovementEngine:
    @pytest.fixture
    def engine(self) -> SelfImprovementEngine:
        return SelfImprovementEngine()

    @pytest.mark.asyncio
    async def test_identify(self, engine: SelfImprovementEngine) -> None:
        item = engine.identify("performance", "Add caching", "Implement Redis", priority=7)
        assert item["category"] == "performance"
        assert item["status"] == "identified"
        assert item["priority"] == 7

    @pytest.mark.asyncio
    async def test_propose(self, engine: SelfImprovementEngine) -> None:
        item = engine.identify("workflow", "X", "x")
        proposed = engine.propose(item["id"])
        assert proposed is not None
        assert proposed["status"] == "proposed"

    @pytest.mark.asyncio
    async def test_propose_nonexistent(self, engine: SelfImprovementEngine) -> None:
        assert engine.propose("nope") is None

    @pytest.mark.asyncio
    async def test_propose_wrong_status(self, engine: SelfImprovementEngine) -> None:
        item = engine.identify("workflow", "X", "x")
        engine.propose(item["id"])
        assert engine.propose(item["id"]) is None

    @pytest.mark.asyncio
    async def test_approve(self, engine: SelfImprovementEngine) -> None:
        item = engine.identify("workflow", "X", "x")
        engine.propose(item["id"])
        approved = engine.approve(item["id"])
        assert approved is not None
        assert approved["status"] == "approved"

    @pytest.mark.asyncio
    async def test_approve_nonexistent(self, engine: SelfImprovementEngine) -> None:
        assert engine.approve("nope") is None

    @pytest.mark.asyncio
    async def test_approve_wrong_status(self, engine: SelfImprovementEngine) -> None:
        item = engine.identify("workflow", "X", "x")
        assert engine.approve(item["id"]) is None

    @pytest.mark.asyncio
    async def test_start(self, engine: SelfImprovementEngine) -> None:
        item = engine.identify("workflow", "X", "x")
        engine.propose(item["id"])
        engine.approve(item["id"])
        started = engine.start(item["id"])
        assert started is not None
        assert started["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_start_nonexistent(self, engine: SelfImprovementEngine) -> None:
        assert engine.start("nope") is None

    @pytest.mark.asyncio
    async def test_start_wrong_status(self, engine: SelfImprovementEngine) -> None:
        item = engine.identify("workflow", "X", "x")
        assert engine.start(item["id"]) is None

    @pytest.mark.asyncio
    async def test_complete(self, engine: SelfImprovementEngine) -> None:
        item = engine.identify("workflow", "X", "x")
        engine.propose(item["id"])
        engine.approve(item["id"])
        engine.start(item["id"])
        completed = engine.complete(item["id"])
        assert completed is not None
        assert completed["status"] == "completed"

    @pytest.mark.asyncio
    async def test_complete_nonexistent(self, engine: SelfImprovementEngine) -> None:
        assert engine.complete("nope") is None

    @pytest.mark.asyncio
    async def test_complete_wrong_status(self, engine: SelfImprovementEngine) -> None:
        item = engine.identify("workflow", "X", "x")
        assert engine.complete(item["id"]) is None

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, engine: SelfImprovementEngine) -> None:
        item = engine.identify("security", "Auth upgrade", "Upgrade auth", priority=9)
        assert item["status"] == "identified"
        proposed = engine.propose(item["id"])
        assert proposed["status"] == "proposed"
        approved = engine.approve(item["id"])
        assert approved["status"] == "approved"
        started = engine.start(item["id"])
        assert started["status"] == "in_progress"
        completed = engine.complete(item["id"])
        assert completed["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_item(self, engine: SelfImprovementEngine) -> None:
        item = engine.identify("workflow", "X", "x")
        fetched = engine.get_item(item["id"])
        assert fetched is not None
        assert fetched["title"] == "X"

    @pytest.mark.asyncio
    async def test_get_item_nonexistent(self, engine: SelfImprovementEngine) -> None:
        assert engine.get_item("nope") is None

    @pytest.mark.asyncio
    async def test_list_items(self, engine: SelfImprovementEngine) -> None:
        engine.identify("workflow", "A", "a")
        engine.identify("security", "B", "b")
        assert len(engine.list_items()) == 2

    @pytest.mark.asyncio
    async def test_list_items_by_status(self, engine: SelfImprovementEngine) -> None:
        item = engine.identify("workflow", "A", "a")
        engine.propose(item["id"])
        engine.identify("security", "B", "b")
        assert len(engine.list_items(status="identified")) == 1
        assert len(engine.list_items(status="proposed")) == 1

    @pytest.mark.asyncio
    async def test_list_items_by_category(self, engine: SelfImprovementEngine) -> None:
        engine.identify("workflow", "A", "a")
        engine.identify("security", "B", "b")
        assert len(engine.list_items(category="workflow")) == 1
        assert len(engine.list_items(category="security")) == 1

    @pytest.mark.asyncio
    async def test_get_improvement_opportunities(self, engine: SelfImprovementEngine) -> None:
        engine.identify("workflow", "Low", "l", priority=1)
        engine.identify("security", "High", "h", priority=10)
        opps = engine.get_improvement_opportunities()
        assert len(opps) == 2
        assert opps[0]["priority"] >= opps[1]["priority"]

    @pytest.mark.asyncio
    async def test_get_improvement_opportunities_only_identified(self, engine: SelfImprovementEngine) -> None:
        item = engine.identify("workflow", "X", "x")
        engine.propose(item["id"])
        engine.identify("security", "Y", "y")
        opps = engine.get_improvement_opportunities()
        assert len(opps) == 1

    @pytest.mark.asyncio
    async def test_categories(self) -> None:
        assert "architectural" in SelfImprovementEngine.CATEGORIES
        assert "performance" in SelfImprovementEngine.CATEGORIES
        assert "security" in SelfImprovementEngine.CATEGORIES
        assert len(SelfImprovementEngine.CATEGORIES) == 9

    @pytest.mark.asyncio
    async def test_to_dict(self, engine: SelfImprovementEngine) -> None:
        engine.identify("workflow", "X", "x")
        d = engine.to_dict()
        assert "items" in d


# ---------------------------------------------------------------------------
# ApprovalEngine
# ---------------------------------------------------------------------------


class TestApprovalEngine:
    @pytest.fixture
    def engine(self) -> ApprovalEngine:
        return ApprovalEngine()

    @pytest.mark.asyncio
    async def test_default_policies_count(self, engine: ApprovalEngine) -> None:
        assert len(engine._policies) == 8

    @pytest.mark.asyncio
    async def test_default_policy_autonomous_execution(self, engine: ApprovalEngine) -> None:
        p = engine.get_policy("autonomous_execution")
        assert p is not None
        assert p["require_approval"] is True
        assert p["risk_level"] == "medium"

    @pytest.mark.asyncio
    async def test_default_policy_workflow_execution(self, engine: ApprovalEngine) -> None:
        p = engine.get_policy("workflow_execution")
        assert p is not None
        assert p["require_approval"] is False

    @pytest.mark.asyncio
    async def test_default_policy_system_modification(self, engine: ApprovalEngine) -> None:
        p = engine.get_policy("system_modification")
        assert p is not None
        assert p["require_approval"] is True
        assert p["risk_level"] == "critical"

    @pytest.mark.asyncio
    async def test_default_policy_self_improvement(self, engine: ApprovalEngine) -> None:
        p = engine.get_policy("self_improvement")
        assert p is not None
        assert p["require_approval"] is True
        assert p["risk_level"] == "high"

    @pytest.mark.asyncio
    async def test_set_policy(self, engine: ApprovalEngine) -> None:
        p = engine.set_policy("custom", require_approval=True, timeout_seconds=120, risk_level="high")
        assert p["action_type"] == "custom"
        assert p["timeout_seconds"] == 120

    @pytest.mark.asyncio
    async def test_get_policy(self, engine: ApprovalEngine) -> None:
        engine.set_policy("custom", require_approval=False)
        p = engine.get_policy("custom")
        assert p is not None
        assert p["require_approval"] is False

    @pytest.mark.asyncio
    async def test_get_policy_nonexistent(self, engine: ApprovalEngine) -> None:
        assert engine.get_policy("nope") is None

    @pytest.mark.asyncio
    async def test_request_approval(self, engine: ApprovalEngine) -> None:
        req = engine.request_approval("task_execution", "Run task", metadata={"key": "val"})
        assert req["status"] == "pending"
        assert req["action_type"] == "task_execution"
        assert req["metadata"]["key"] == "val"

    @pytest.mark.asyncio
    async def test_approve(self, engine: ApprovalEngine) -> None:
        req = engine.request_approval("task_execution", "Run task")
        approved = engine.approve(req["id"], reviewer="admin", reason="OK")
        assert approved is not None
        assert approved["status"] == "approved"
        assert approved["reviewer"] == "admin"

    @pytest.mark.asyncio
    async def test_approve_nonexistent(self, engine: ApprovalEngine) -> None:
        assert engine.approve("nope") is None

    @pytest.mark.asyncio
    async def test_reject(self, engine: ApprovalEngine) -> None:
        req = engine.request_approval("task_execution", "Run task")
        rejected = engine.reject(req["id"], reviewer="admin", reason="Too risky")
        assert rejected is not None
        assert rejected["status"] == "rejected"
        assert rejected["reason"] == "Too risky"

    @pytest.mark.asyncio
    async def test_reject_nonexistent(self, engine: ApprovalEngine) -> None:
        assert engine.reject("nope") is None

    @pytest.mark.asyncio
    async def test_get_pending(self, engine: ApprovalEngine) -> None:
        engine.request_approval("a", "desc1")
        engine.request_approval("b", "desc2")
        assert len(engine.get_pending()) == 2

    @pytest.mark.asyncio
    async def test_get_resolved(self, engine: ApprovalEngine) -> None:
        req = engine.request_approval("a", "desc")
        engine.approve(req["id"])
        assert len(engine.get_resolved()) == 1

    @pytest.mark.asyncio
    async def test_requires_approval(self, engine: ApprovalEngine) -> None:
        assert engine.requires_approval("system_modification") is True
        assert engine.requires_approval("workflow_execution") is False

    @pytest.mark.asyncio
    async def test_requires_approval_unknown(self, engine: ApprovalEngine) -> None:
        assert engine.requires_approval("unknown_type") is True

    @pytest.mark.asyncio
    async def test_to_dict(self, engine: ApprovalEngine) -> None:
        d = engine.to_dict()
        assert "policies" in d
        assert "pending" in d
        assert "resolved" in d


# ---------------------------------------------------------------------------
# DelegationEngine
# ---------------------------------------------------------------------------


class TestDelegationEngine:
    @pytest.fixture
    def engine(self) -> DelegationEngine:
        return DelegationEngine()

    @pytest.mark.asyncio
    async def test_delegate(self, engine: DelegationEngine) -> None:
        task = engine.delegate("Write unit tests", delegation_type="agent", context={"suite": "auth"})
        assert task["task_description"] == "Write unit tests"
        assert task["delegation_type"] == "agent"
        assert task["status"] == "pending"
        assert task["context"]["suite"] == "auth"

    @pytest.mark.asyncio
    async def test_get_task(self, engine: DelegationEngine) -> None:
        task = engine.delegate("X")
        fetched = engine.get_task(task["id"])
        assert fetched is not None

    @pytest.mark.asyncio
    async def test_get_task_nonexistent(self, engine: DelegationEngine) -> None:
        assert engine.get_task("nope") is None

    @pytest.mark.asyncio
    async def test_update_task(self, engine: DelegationEngine) -> None:
        task = engine.delegate("X")
        updated = engine.update_task(task["id"], assigned_to="reviewer")
        assert updated is not None
        assert updated["assigned_to"] == "reviewer"

    @pytest.mark.asyncio
    async def test_update_task_nonexistent(self, engine: DelegationEngine) -> None:
        assert engine.update_task("nope", assigned_to="x") is None

    @pytest.mark.asyncio
    async def test_complete_task(self, engine: DelegationEngine) -> None:
        task = engine.delegate("X")
        completed = engine.complete_task(task["id"], result="Done!")
        assert completed is not None
        assert completed["status"] == "completed"
        assert completed["context"]["result"] == "Done!"

    @pytest.mark.asyncio
    async def test_complete_task_no_result(self, engine: DelegationEngine) -> None:
        task = engine.delegate("X")
        completed = engine.complete_task(task["id"])
        assert completed is not None
        assert completed["status"] == "completed"

    @pytest.mark.asyncio
    async def test_complete_task_nonexistent(self, engine: DelegationEngine) -> None:
        assert engine.complete_task("nope") is None

    @pytest.mark.asyncio
    async def test_fail_task(self, engine: DelegationEngine) -> None:
        task = engine.delegate("X")
        failed = engine.fail_task(task["id"], error="Timeout")
        assert failed is not None
        assert failed["status"] == "failed"
        assert failed["context"]["error"] == "Timeout"

    @pytest.mark.asyncio
    async def test_fail_task_no_error(self, engine: DelegationEngine) -> None:
        task = engine.delegate("X")
        failed = engine.fail_task(task["id"])
        assert failed is not None
        assert failed["status"] == "failed"

    @pytest.mark.asyncio
    async def test_fail_task_nonexistent(self, engine: DelegationEngine) -> None:
        assert engine.fail_task("nope") is None

    @pytest.mark.asyncio
    async def test_list_tasks(self, engine: DelegationEngine) -> None:
        engine.delegate("A", delegation_type="agent")
        engine.delegate("B", delegation_type="workflow")
        assert len(engine.list_tasks()) == 2

    @pytest.mark.asyncio
    async def test_list_tasks_by_status(self, engine: DelegationEngine) -> None:
        task = engine.delegate("A")
        engine.complete_task(task["id"])
        engine.delegate("B")
        assert len(engine.list_tasks(status="completed")) == 1
        assert len(engine.list_tasks(status="pending")) == 1

    @pytest.mark.asyncio
    async def test_list_tasks_by_type(self, engine: DelegationEngine) -> None:
        engine.delegate("A", delegation_type="agent")
        engine.delegate("B", delegation_type="open_code")
        assert len(engine.list_tasks(delegation_type="agent")) == 1

    @pytest.mark.asyncio
    async def test_recommend_delegation_code(self, engine: DelegationEngine) -> None:
        rec = engine.recommend_delegation("Implement the login feature")
        assert rec["recommended_type"] == "open_code"

    @pytest.mark.asyncio
    async def test_recommend_delegation_research(self, engine: DelegationEngine) -> None:
        rec = engine.recommend_delegation("Search for best practices")
        assert rec["recommended_type"] == "workflow"

    @pytest.mark.asyncio
    async def test_recommend_delegation_review(self, engine: DelegationEngine) -> None:
        rec = engine.recommend_delegation("Review the pull request")
        assert rec["recommended_type"] == "agent"

    @pytest.mark.asyncio
    async def test_recommend_delegation_manual(self, engine: DelegationEngine) -> None:
        rec = engine.recommend_delegation("Schedule a meeting")
        assert rec["recommended_type"] == "manual"

    @pytest.mark.asyncio
    async def test_recommend_delegation_alternatives(self, engine: DelegationEngine) -> None:
        rec = engine.recommend_delegation("Implement code")
        assert len(rec["alternatives"]) == 3
        assert "open_code" not in rec["alternatives"]

    @pytest.mark.asyncio
    async def test_to_dict(self, engine: DelegationEngine) -> None:
        engine.delegate("X")
        d = engine.to_dict()
        assert "tasks" in d


# ---------------------------------------------------------------------------
# ResearchManager
# ---------------------------------------------------------------------------


class TestResearchManager:
    @pytest.fixture
    def manager(self) -> ResearchManager:
        return ResearchManager()

    @pytest.mark.asyncio
    async def test_submit_research(self, manager: ResearchManager) -> None:
        rq = manager.submit_research("Best caching strategies?", depth="deep")
        assert rq["query"] == "Best caching strategies?"
        assert rq["depth"] == "deep"
        assert rq["findings"] == []

    @pytest.mark.asyncio
    async def test_submit_research_default_depth(self, manager: ResearchManager) -> None:
        rq = manager.submit_research("Query")
        assert rq["depth"] == "standard"

    @pytest.mark.asyncio
    async def test_get_research(self, manager: ResearchManager) -> None:
        rq = manager.submit_research("X")
        fetched = manager.get_research(rq["id"])
        assert fetched is not None
        assert fetched["query"] == "X"

    @pytest.mark.asyncio
    async def test_get_research_nonexistent(self, manager: ResearchManager) -> None:
        assert manager.get_research("nope") is None

    @pytest.mark.asyncio
    async def test_complete_research(self, manager: ResearchManager) -> None:
        rq = manager.submit_research("X")
        findings = [{"title": "Finding 1", "source": "docs"}]
        completed = manager.complete_research(rq["id"], findings=findings, summary="Use Redis", confidence=0.9)
        assert completed is not None
        assert completed["findings"] == findings
        assert completed["summary"] == "Use Redis"
        assert completed["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_complete_research_nonexistent(self, manager: ResearchManager) -> None:
        assert manager.complete_research("nope", findings=[], summary="x") is None

    @pytest.mark.asyncio
    async def test_list_research(self, manager: ResearchManager) -> None:
        manager.submit_research("A")
        manager.submit_research("B")
        assert len(manager.list_research()) == 2

    @pytest.mark.asyncio
    async def test_list_research_limit(self, manager: ResearchManager) -> None:
        for i in range(5):
            manager.submit_research(f"Q{i}")
        assert len(manager.list_research(limit=2)) == 2

    @pytest.mark.asyncio
    async def test_to_dict(self, manager: ResearchManager) -> None:
        manager.submit_research("X")
        d = manager.to_dict()
        assert "queries" in d


# ---------------------------------------------------------------------------
# Schema dataclass basics
# ---------------------------------------------------------------------------


class TestAutonomySchemas:
    @pytest.mark.asyncio
    async def test_objective_plan_defaults(self) -> None:
        p = ObjectivePlan()
        assert p.title == ""
        assert p.requires_human_approval is True
        assert p.requires_open_code is False
        assert p.tasks == []

    @pytest.mark.asyncio
    async def test_project_orchestration_defaults(self) -> None:
        po = ProjectOrchestration()
        assert po.status == "analyzing"
        assert po.progress == 0.0

    @pytest.mark.asyncio
    async def test_recommendation_defaults(self) -> None:
        r = Recommendation()
        assert r.priority == "medium"
        assert r.status == "pending"

    @pytest.mark.asyncio
    async def test_optimization_result_defaults(self) -> None:
        o = OptimizationResult()
        assert o.priority == 3
        assert o.category == ""

    @pytest.mark.asyncio
    async def test_self_improvement_item_defaults(self) -> None:
        s = SelfImprovementItem()
        assert s.status == "identified"
        assert s.priority == 3

    @pytest.mark.asyncio
    async def test_delegation_task_defaults(self) -> None:
        dt = DelegationTask()
        assert dt.delegation_type == "agent"
        assert dt.status == "pending"
        assert dt.context == {}

    @pytest.mark.asyncio
    async def test_research_query_defaults(self) -> None:
        rq = ResearchQuery()
        assert rq.depth == "standard"
        assert rq.findings == []
        assert rq.confidence == 0.0
