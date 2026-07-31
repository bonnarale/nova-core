"""Tests for the Command Center subsystem."""

from __future__ import annotations

import pytest

from app.command_center import (
    CommandCenter,
    CommandCenterFactory,
    CommandRequest,
    CommandResponse,
    ObjectivesManager,
    ProjectsManager,
    RoadmapManager,
    BacklogManager,
    MilestonesManager,
    ApprovalsManager,
    AutonomyManager,
    DecisionEngine,
    RecommendationEngine,
    OptimizationEngine,
    Orchestrator,
    SelfImprovementEngine,
    CommandCenterLifecycle,
    MetricsCollector,
    TracingManager,
    ApprovalRequest,
    BacklogItem,
    CommandMetrics,
    GovernorDecision,
    LifecycleState,
    Milestone,
    Objective,
    Optimization,
    Project,
    Recommendation,
    Roadmap,
    RoadmapPhase,
)
from app.command_center.governor import Governor as GovernorCore
from app.command_center.governor import Governor as GovernorOrchestrator


# ── 1. TestCommandCenter ──────────────────────────────────────────────────────


class TestCommandCenter:
    @pytest.mark.asyncio
    async def test_process_analyze(self) -> None:
        cc = CommandCenter()
        req = CommandRequest(command="analyze", parameters={"text": "Build an application"})
        resp = await cc.process_command(req)
        assert resp.status == "completed"
        assert resp.result is not None
        assert "category" in resp.result

    @pytest.mark.asyncio
    async def test_process_plan(self) -> None:
        cc = CommandCenter()
        req = CommandRequest(
            command="plan",
            parameters={"analysis": {"tasks": [{"t": 1}], "milestones": [], "goals": []}},
        )
        resp = await cc.process_command(req)
        assert resp.status == "completed"
        assert "phases" in resp.result

    @pytest.mark.asyncio
    async def test_process_create_objective(self) -> None:
        cc = CommandCenter()
        req = CommandRequest(
            command="create_objective",
            parameters={"title": "Test Objective", "description": "desc", "category": "tech"},
        )
        resp = await cc.process_command(req)
        assert resp.status == "completed"
        assert resp.result["title"] == "Test Objective"

    @pytest.mark.asyncio
    async def test_process_create_project(self) -> None:
        cc = CommandCenter()
        req = CommandRequest(
            command="create_project",
            parameters={"name": "Test Project", "description": "desc"},
        )
        resp = await cc.process_command(req)
        assert resp.status == "completed"
        assert resp.result["name"] == "Test Project"

    @pytest.mark.asyncio
    async def test_process_create_roadmap(self) -> None:
        cc = CommandCenter()
        req = CommandRequest(
            command="create_roadmap", parameters={"name": "Roadmap", "duration_years": 2}
        )
        resp = await cc.process_command(req)
        assert resp.status == "completed"
        assert resp.result["name"] == "Roadmap"
        assert len(resp.result["phases"]) > 0

    @pytest.mark.asyncio
    async def test_process_list_objectives(self) -> None:
        cc = CommandCenter()
        cc.objectives.create(title="A")
        req = CommandRequest(command="list_objectives")
        resp = await cc.process_command(req)
        assert resp.status == "completed"
        assert isinstance(resp.result, list)
        assert len(resp.result) == 1

    @pytest.mark.asyncio
    async def test_process_list_projects(self) -> None:
        cc = CommandCenter()
        cc.projects.create(name="P1")
        req = CommandRequest(command="list_projects")
        resp = await cc.process_command(req)
        assert resp.status == "completed"
        assert len(resp.result) == 1

    @pytest.mark.asyncio
    async def test_process_list_backlog(self) -> None:
        cc = CommandCenter()
        cc.backlog.add(title="Item1")
        req = CommandRequest(command="list_backlog")
        resp = await cc.process_command(req)
        assert resp.status == "completed"
        assert len(resp.result) == 1

    @pytest.mark.asyncio
    async def test_process_approve(self) -> None:
        cc = CommandCenter()
        approval = cc.approvals.request(
            action_type="deploy", description="Deploy v1", risk_level="critical"
        )
        req = CommandRequest(
            command="approve", parameters={"approval_id": approval.id, "reviewer": "admin"}
        )
        resp = await cc.process_command(req)
        assert resp.status == "completed"
        assert resp.result["status"] == "approved"

    @pytest.mark.asyncio
    async def test_process_reject(self) -> None:
        cc = CommandCenter()
        approval = cc.approvals.request(
            action_type="deploy", description="Deploy v2", risk_level="high"
        )
        req = CommandRequest(
            command="reject",
            parameters={"approval_id": approval.id, "reviewer": "admin", "reason": "too risky"},
        )
        resp = await cc.process_command(req)
        assert resp.status == "completed"
        assert resp.result["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_process_approve_not_found(self) -> None:
        cc = CommandCenter()
        req = CommandRequest(command="approve", parameters={"approval_id": "nonexistent"})
        resp = await cc.process_command(req)
        assert resp.status == "failed"
        assert resp.error is not None

    @pytest.mark.asyncio
    async def test_process_recommend(self) -> None:
        cc = CommandCenter()
        req = CommandRequest(command="recommend", parameters={"context": {"active_objectives": 0}})
        resp = await cc.process_command(req)
        assert resp.status == "completed"
        assert "action" in resp.result

    @pytest.mark.asyncio
    async def test_process_optimize(self) -> None:
        cc = CommandCenter()
        req = CommandRequest(command="optimize", parameters={"category": "performance"})
        resp = await cc.process_command(req)
        assert resp.status == "completed"
        assert resp.result["category"] == "performance"

    @pytest.mark.asyncio
    async def test_process_status(self) -> None:
        cc = CommandCenter()
        req = CommandRequest(command="status")
        resp = await cc.process_command(req)
        assert resp.status == "completed"
        assert "lifecycle" in resp.result
        assert "metrics" in resp.result

    @pytest.mark.asyncio
    async def test_process_unknown_command(self) -> None:
        cc = CommandCenter()
        req = CommandRequest(command="nonexistent_cmd")
        resp = await cc.process_command(req)
        assert resp.status == "failed"
        assert resp.error == "Command not recognized"
        assert len(resp.suggestions) > 0
        assert "analyze" in resp.suggestions

    @pytest.mark.asyncio
    async def test_get_status(self) -> None:
        cc = CommandCenter()
        status = await cc.get_status()
        assert "lifecycle" in status
        assert "metrics" in status
        assert "objectives" in status
        assert "projects" in status
        assert "roadmap" in status
        assert "backlog" in status
        assert "milestones" in status
        assert "approvals" in status

    @pytest.mark.asyncio
    async def test_properties_accessible(self) -> None:
        cc = CommandCenter()
        assert isinstance(cc.governor, GovernorCore)
        assert isinstance(cc.objectives, ObjectivesManager)
        assert isinstance(cc.projects, ProjectsManager)
        assert isinstance(cc.roadmap, RoadmapManager)
        assert isinstance(cc.backlog, BacklogManager)
        assert isinstance(cc.milestones, MilestonesManager)
        assert isinstance(cc.approvals, ApprovalsManager)
        assert isinstance(cc.lifecycle, LifecycleState)

    @pytest.mark.asyncio
    async def test_metrics_tracked(self) -> None:
        cc = CommandCenter()
        req = CommandRequest(command="status")
        await cc.process_command(req)
        m = cc.metrics
        assert m.total_commands >= 1

    @pytest.mark.asyncio
    async def test_to_dict(self) -> None:
        cc = CommandCenter()
        d = cc.to_dict()
        assert "lifecycle" in d
        assert "metrics" in d


# ── 2. TestGovernor ───────────────────────────────────────────────────────────


class TestGovernor:
    def _make_governor(self) -> GovernorCore:
        return GovernorCore(ObjectivesManager(), ProjectsManager(), ApprovalsManager())

    @pytest.mark.asyncio
    async def test_analyze_build_application(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective("Build a software application")
        assert result["category"] == "technology"
        assert result["complexity"] in ("low", "medium", "high", "very_high")
        assert "milestones" in result
        assert "goals" in result
        assert "tasks" in result

    @pytest.mark.asyncio
    async def test_analyze_business(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective("Build a company with revenue growth")
        assert result["category"] == "business"

    @pytest.mark.asyncio
    async def test_analyze_education(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective("Learn AI through courses and study")
        assert result["category"] == "education"

    @pytest.mark.asyncio
    async def test_analyze_roadmap(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective("Create a 10 year roadmap")
        assert "category" in result
        assert "estimated_duration" in result

    @pytest.mark.asyncio
    async def test_analyze_technology(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective("Build a software system with API and database")
        assert result["category"] == "technology"
        assert "requires_open_code" in result

    @pytest.mark.asyncio
    async def test_analyze_risks_high_complexity(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective(
            "Build an AI integration system with distributed architecture and machine learning "
            "infrastructure"
        )
        assert result["complexity"] in ("high", "very_high")
        assert len(result["key_risks"]) >= 3

    @pytest.mark.asyncio
    async def test_create_plan(self) -> None:
        g = self._make_governor()
        plan = await g.create_plan(
            {"tasks": [{"t": 1}], "milestones": [], "goals": [], "category": "tech"}
        )
        assert "phases" in plan
        assert "milestones" in plan
        assert "goals" in plan
        assert plan["category"] == "tech"

    @pytest.mark.asyncio
    async def test_make_decision_low_risk(self) -> None:
        g = self._make_governor()
        d = await g.make_decision("deploy", {"description": "deploy v1", "risk": "low"})
        assert isinstance(d, GovernorDecision)
        assert d.confidence == 0.7
        assert d.action_taken == "auto_execute"
        assert d.requires_approval is False

    @pytest.mark.asyncio
    async def test_make_decision_high_risk(self) -> None:
        g = self._make_governor()
        d = await g.make_decision("deploy", {"description": "deploy prod", "risk": "high"})
        assert d.requires_approval is True
        assert d.action_taken == "pending_approval"

    @pytest.mark.asyncio
    async def test_prioritize(self) -> None:
        g = self._make_governor()
        objs = [
            {"priority": 1, "urgency": 1, "impact": 1, "complexity": "high"},
            {"priority": 5, "urgency": 5, "impact": 5, "complexity": "low"},
        ]
        result = await g.prioritize(objs)
        assert result[0]["priority"] == 5

    @pytest.mark.asyncio
    async def test_recommend_no_objectives(self) -> None:
        g = self._make_governor()
        rec = await g.recommend_next_action({"active_objectives": 0})
        assert rec["action"] == "create_objective"

    @pytest.mark.asyncio
    async def test_recommend_pending_approvals(self) -> None:
        g = self._make_governor()
        rec = await g.recommend_next_action(
            {"active_objectives": 2, "pending_approvals": 3}
        )
        assert rec["action"] == "review_approvals"

    @pytest.mark.asyncio
    async def test_recommend_backlog_heavy(self) -> None:
        g = self._make_governor()
        rec = await g.recommend_next_action(
            {"active_objectives": 1, "backlog_count": 5}
        )
        assert rec["action"] == "prioritize_backlog"

    @pytest.mark.asyncio
    async def test_recommend_continue(self) -> None:
        g = self._make_governor()
        rec = await g.recommend_next_action(
            {"active_objectives": 1, "pending_approvals": 0, "backlog_count": 1}
        )
        assert rec["action"] == "continue_execution"

    def test_categorize_business(self) -> None:
        g = self._make_governor()
        assert g._categorize_objective("Grow revenue and market share") == "business"

    def test_categorize_technology(self) -> None:
        g = self._make_governor()
        assert g._categorize_objective("Build software API") == "technology"

    def test_categorize_education(self) -> None:
        g = self._make_governor()
        assert g._categorize_objective("Study and learn through courses") == "education"

    def test_categorize_personal(self) -> None:
        g = self._make_governor()
        assert g._categorize_objective("Go for a run") == "personal"

    def test_categorize_creative(self) -> None:
        g = self._make_governor()
        assert g._categorize_objective("Create art and design") == "creative"

    def test_categorize_financial(self) -> None:
        g = self._make_governor()
        assert g._categorize_objective("Budget and invest profit") == "financial"

    def test_assess_complexity_low(self) -> None:
        g = self._make_governor()
        assert g._assess_complexity("Simple task") == "low"

    def test_assess_complexity_high(self) -> None:
        g = self._make_governor()
        assert g._assess_complexity(
            "Build an AI integration system with distributed architecture and machine learning "
            "infrastructure",
        ) in ("high", "very_high")

    def test_generate_milestones(self) -> None:
        g = self._make_governor()
        ms = g._generate_milestones("technology", "medium")
        assert len(ms) >= 3
        assert ms[0]["title"] == "Discovery & Research"

    def test_generate_goals(self) -> None:
        g = self._make_governor()
        goals = g._generate_goals("general", "medium")
        assert len(goals) >= 3

    def test_generate_tasks(self) -> None:
        g = self._make_governor()
        tasks = g._generate_tasks("general", "medium")
        assert len(tasks) >= 4

    def test_determine_tools_technology(self) -> None:
        g = self._make_governor()
        tools = g._determine_tools("technology", "low")
        assert "compiler" in tools

    def test_determine_agents_high_complexity(self) -> None:
        g = self._make_governor()
        agents = g._determine_agents("general", "high")
        assert "reviewer" in agents

    def test_to_dict(self) -> None:
        g = self._make_governor()
        d = g.to_dict()
        assert d["role"] == "governor"


# ── 3. TestObjectivesManager ──────────────────────────────────────────────────


class TestObjectivesManager:
    def test_create(self) -> None:
        mgr = ObjectivesManager()
        obj = mgr.create(title="T", description="D", category="c", priority=1)
        assert obj.title == "T"
        assert obj.status == "active"
        assert obj.id in mgr.active

    def test_update(self) -> None:
        mgr = ObjectivesManager()
        obj = mgr.create(title="T")
        updated = mgr.update(obj.id, title="T2")
        assert updated is not None
        assert updated.title == "T2"

    def test_complete(self) -> None:
        mgr = ObjectivesManager()
        obj = mgr.create(title="T")
        completed = mgr.complete(obj.id)
        assert completed.status == "completed"
        assert completed.progress == 1.0
        assert obj.id not in mgr.active

    def test_cancel(self) -> None:
        mgr = ObjectivesManager()
        obj = mgr.create(title="T")
        cancelled = mgr.cancel(obj.id)
        assert cancelled.status == "cancelled"

    def test_max_active_backlog(self) -> None:
        mgr = ObjectivesManager(max_active=3)
        mgr.create(title="A")
        mgr.create(title="B")
        mgr.create(title="C")
        o4 = mgr.create(title="D")
        assert len(mgr.active) == 3
        assert o4.status == "backlog"
        assert o4 in mgr.backlog

    def test_promote_from_backlog(self) -> None:
        mgr = ObjectivesManager(max_active=2)
        o1 = mgr.create(title="A")
        mgr.create(title="B")
        o3 = mgr.create(title="C")
        mgr.active.pop(o1.id)
        promoted = mgr.promote_from_backlog(o3.id)
        assert promoted is not None
        assert promoted.status == "active"
        assert promoted.id in mgr.active

    def test_promote_from_backlog_full(self) -> None:
        mgr = ObjectivesManager(max_active=2)
        mgr.create(title="A")
        mgr.create(title="B")
        o3 = mgr.create(title="C")
        result = mgr.promote_from_backlog(o3.id)
        assert result is None

    def test_update_progress(self) -> None:
        mgr = ObjectivesManager()
        obj = mgr.create(title="T")
        mgr.update_progress(obj.id, 0.5)
        assert obj.progress == 0.5

    def test_update_progress_clamp(self) -> None:
        mgr = ObjectivesManager()
        obj = mgr.create(title="T")
        mgr.update_progress(obj.id, 2.0)
        assert obj.progress == 1.0
        mgr.update_progress(obj.id, -1.0)
        assert obj.progress == 0.0

    def test_add_milestone(self) -> None:
        mgr = ObjectivesManager()
        obj = mgr.create(title="T")
        assert mgr.add_milestone(obj.id, {"title": "M1"}) is True
        assert len(obj.milestones) == 1

    def test_add_goal(self) -> None:
        mgr = ObjectivesManager()
        obj = mgr.create(title="T")
        assert mgr.add_goal(obj.id, {"title": "G1"}) is True
        assert len(obj.goals) == 1

    def test_add_task(self) -> None:
        mgr = ObjectivesManager()
        obj = mgr.create(title="T")
        assert mgr.add_task(obj.id, {"title": "Task1"}) is True
        assert len(obj.tasks) == 1

    def test_list_active(self) -> None:
        mgr = ObjectivesManager()
        mgr.create(title="A")
        assert len(mgr.list_active()) == 1

    def test_list_backlog(self) -> None:
        mgr = ObjectivesManager(max_active=1)
        mgr.create(title="A")
        mgr.create(title="B")
        assert len(mgr.list_backlog()) == 1

    def test_list_all(self) -> None:
        mgr = ObjectivesManager()
        mgr.create(title="A")
        mgr.create(title="B")
        assert len(mgr.list_all()) == 2

    def test_list_all_filter_status(self) -> None:
        mgr = ObjectivesManager()
        mgr.create(title="A")
        obj = mgr.create(title="B")
        mgr.complete(obj.id)
        active = mgr.list_all(status="active")
        assert len(active) == 1

    def test_get(self) -> None:
        mgr = ObjectivesManager()
        obj = mgr.create(title="T")
        assert mgr.get(obj.id) is obj

    def test_cancel_backlog_item(self) -> None:
        mgr = ObjectivesManager(max_active=1)
        mgr.create(title="A")
        b = mgr.create(title="B")
        cancelled = mgr.cancel(b.id)
        assert cancelled.status == "cancelled"
        assert b not in mgr.backlog

    def test_to_dict(self) -> None:
        mgr = ObjectivesManager()
        d = mgr.to_dict()
        assert "active" in d
        assert "backlog" in d


# ── 4. TestProjectsManager ────────────────────────────────────────────────────


class TestProjectsManager:
    def test_create(self) -> None:
        mgr = ProjectsManager()
        p = mgr.create(name="P", description="D", objective_id="oid")
        assert p.name == "P"
        assert p.objective_id == "oid"

    def test_update(self) -> None:
        mgr = ProjectsManager()
        p = mgr.create(name="P")
        updated = mgr.update(p.id, name="P2")
        assert updated.name == "P2"

    def test_complete(self) -> None:
        mgr = ProjectsManager()
        p = mgr.create(name="P")
        mgr.complete(p.id)
        assert p.status == "completed"
        assert p.progress == 1.0

    def test_pause(self) -> None:
        mgr = ProjectsManager()
        p = mgr.create(name="P")
        mgr.pause(p.id)
        assert p.status == "paused"

    def test_resume(self) -> None:
        mgr = ProjectsManager()
        p = mgr.create(name="P")
        mgr.pause(p.id)
        mgr.resume(p.id)
        assert p.status == "active"

    def test_list_all_no_filter(self) -> None:
        mgr = ProjectsManager()
        mgr.create(name="A")
        mgr.create(name="B")
        assert len(mgr.list_all()) == 2

    def test_list_all_status_filter(self) -> None:
        mgr = ProjectsManager()
        p = mgr.create(name="A")
        mgr.complete(p.id)
        mgr.create(name="B")
        completed = mgr.list_all(status="completed")
        assert len(completed) == 1

    def test_add_phase(self) -> None:
        mgr = ProjectsManager()
        p = mgr.create(name="P")
        assert mgr.add_phase(p.id, {"name": "Phase1"}) is True
        assert len(p.phases) == 1

    def test_add_milestone(self) -> None:
        mgr = ProjectsManager()
        p = mgr.create(name="P")
        assert mgr.add_milestone(p.id, {"title": "M1"}) is True
        assert len(p.milestones) == 1

    def test_update_progress(self) -> None:
        mgr = ProjectsManager()
        p = mgr.create(name="P")
        mgr.update_progress(p.id, 0.75)
        assert p.progress == 0.75

    def test_get(self) -> None:
        mgr = ProjectsManager()
        p = mgr.create(name="P")
        assert mgr.get(p.id) is p

    def test_to_dict(self) -> None:
        mgr = ProjectsManager()
        d = mgr.to_dict()
        assert isinstance(d, dict)


# ── 5. TestRoadmapManager ─────────────────────────────────────────────────────


class TestRoadmapManager:
    def test_create_auto_generates_phases(self) -> None:
        mgr = RoadmapManager()
        rm = mgr.create(name="R", duration_years=1)
        assert len(rm.phases) == 4
        assert rm.phases[0]["title"] == "Foundation"

    def test_create_multi_year(self) -> None:
        mgr = RoadmapManager()
        rm = mgr.create(name="R", duration_years=3)
        assert len(rm.phases) == 6

    def test_add_phase(self) -> None:
        mgr = RoadmapManager()
        rm = mgr.create(name="R")
        phase = mgr.add_phase(rm.id, {"title": "New Phase", "duration_months": 6})
        assert phase is not None
        assert phase.title == "New Phase"

    def test_complete_phase(self) -> None:
        mgr = RoadmapManager()
        rm = mgr.create(name="R")
        phase_id = rm.phases[0]["id"]
        assert mgr.complete_phase(rm.id, phase_id) is True
        assert rm.phases[0]["status"] == "completed"

    def test_complete_phase_nonexistent(self) -> None:
        mgr = RoadmapManager()
        rm = mgr.create(name="R")
        assert mgr.complete_phase(rm.id, "fake_id") is False

    def test_list_all_filter(self) -> None:
        mgr = RoadmapManager()
        mgr.create(name="R1")
        rm2 = mgr.create(name="R2")
        mgr.update(rm2.id, status="active")
        draft = mgr.list_all(status="draft")
        assert len(draft) == 1

    def test_get(self) -> None:
        mgr = RoadmapManager()
        rm = mgr.create(name="R")
        assert mgr.get(rm.id) is rm

    def test_to_dict(self) -> None:
        mgr = RoadmapManager()
        d = mgr.to_dict()
        assert isinstance(d, dict)


# ── 6. TestBacklogManager ─────────────────────────────────────────────────────


class TestBacklogManager:
    def test_add(self) -> None:
        mgr = BacklogManager()
        item = mgr.add(title="T", description="D", category="cat", priority=1, source="user")
        assert item.title == "T"
        assert item.priority == 1

    def test_update(self) -> None:
        mgr = BacklogManager()
        item = mgr.add(title="T")
        updated = mgr.update(item.id, title="T2")
        assert updated.title == "T2"

    def test_approve(self) -> None:
        mgr = BacklogManager()
        item = mgr.add(title="T")
        mgr.approve(item.id)
        assert item.status == "approved"

    def test_reject(self) -> None:
        mgr = BacklogManager()
        item = mgr.add(title="T")
        mgr.reject(item.id)
        assert item.status == "rejected"

    def test_remove(self) -> None:
        mgr = BacklogManager()
        item = mgr.add(title="T")
        assert mgr.remove(item.id) is True
        assert mgr.get(item.id) is None

    def test_remove_nonexistent(self) -> None:
        mgr = BacklogManager()
        assert mgr.remove("fake") is False

    def test_list_items_filter_status(self) -> None:
        mgr = BacklogManager()
        mgr.add(title="A")
        b = mgr.add(title="B")
        mgr.approve(b.id)
        pending = mgr.list_items(status="pending")
        assert len(pending) == 1

    def test_list_items_filter_category(self) -> None:
        mgr = BacklogManager()
        mgr.add(title="A", category="x")
        mgr.add(title="B", category="y")
        x = mgr.list_items(category="x")
        assert len(x) == 1

    def test_prioritize(self) -> None:
        mgr = BacklogManager()
        mgr.add(title="Low", priority=1)
        mgr.add(title="High", priority=5)
        ordered = mgr.prioritize()
        assert ordered[0].priority == 5

    def test_to_dict(self) -> None:
        mgr = BacklogManager()
        d = mgr.to_dict()
        assert isinstance(d, dict)


# ── 7. TestMilestonesManager ──────────────────────────────────────────────────


class TestMilestonesManager:
    def test_create(self) -> None:
        mgr = MilestonesManager()
        m = mgr.create(
            title="M", description="D", objective_id="oid", project_id="pid", due_date="2025-01-01"
        )
        assert m.title == "M"
        assert m.objective_id == "oid"

    def test_update(self) -> None:
        mgr = MilestonesManager()
        m = mgr.create(title="M")
        mgr.update(m.id, title="M2")
        assert m.title == "M2"

    def test_complete(self) -> None:
        mgr = MilestonesManager()
        m = mgr.create(title="M")
        mgr.complete(m.id)
        assert m.status == "completed"

    def test_list_all_filter_status(self) -> None:
        mgr = MilestonesManager()
        mgr.create(title="A")
        m2 = mgr.create(title="B")
        mgr.complete(m2.id)
        completed = mgr.list_all(status="completed")
        assert len(completed) == 1

    def test_list_all_filter_objective(self) -> None:
        mgr = MilestonesManager()
        mgr.create(title="A", objective_id="o1")
        mgr.create(title="B", objective_id="o2")
        result = mgr.list_all(objective_id="o1")
        assert len(result) == 1

    def test_list_all_filter_project(self) -> None:
        mgr = MilestonesManager()
        mgr.create(title="A", project_id="p1")
        mgr.create(title="B", project_id="p2")
        result = mgr.list_all(project_id="p1")
        assert len(result) == 1

    def test_get(self) -> None:
        mgr = MilestonesManager()
        m = mgr.create(title="M")
        assert mgr.get(m.id) is m

    def test_to_dict(self) -> None:
        mgr = MilestonesManager()
        d = mgr.to_dict()
        assert isinstance(d, dict)


# ── 8. TestApprovalsManager ───────────────────────────────────────────────────


class TestApprovalsManager:
    def test_request(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(
            action_type="deploy", description="Deploy", risk_level="low", requester="nova"
        )
        assert r.status == "pending"
        assert r.action_type == "deploy"

    def test_approve(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(action_type="deploy", description="D")
        approved = mgr.approve(r.id, reviewer="admin")
        assert approved.status == "approved"
        assert approved.reviewer == "admin"

    def test_reject(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(action_type="deploy", description="D")
        rejected = mgr.reject(r.id, reviewer="admin", reason="no")
        assert rejected.status == "rejected"
        assert rejected.reason == "no"

    def test_eight_default_policies(self) -> None:
        mgr = ApprovalsManager()
        assert len(mgr.policies) == 8
        assert "system_config" in mgr.policies
        assert "data_access" in mgr.policies
        assert "deploy" in mgr.policies
        assert "execute_code" in mgr.policies
        assert "modify_objective" in mgr.policies
        assert "create_project" in mgr.policies
        assert "governor_action" in mgr.policies
        assert "autonomous_task" in mgr.policies

    def test_requires_approval_known(self) -> None:
        mgr = ApprovalsManager()
        assert mgr.requires_approval("deploy") is True
        assert mgr.requires_approval("modify_objective") is False

    def test_requires_approval_unknown(self) -> None:
        mgr = ApprovalsManager()
        assert mgr.requires_approval("unknown_action") is True

    def test_get_pending(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(action_type="deploy", description="D")
        pending = mgr.get_pending()
        assert len(pending) == 1
        assert pending[0].id == r.id

    def test_get_resolved(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(action_type="deploy", description="D")
        mgr.approve(r.id)
        resolved = mgr.get_resolved()
        assert len(resolved) == 1

    def test_set_policy(self) -> None:
        mgr = ApprovalsManager()
        p = mgr.set_policy("custom_action", True, 600, "high")
        assert p["require_approval"] is True
        assert p["timeout_seconds"] == 600
        assert mgr.requires_approval("custom_action") is True

    def test_to_dict(self) -> None:
        mgr = ApprovalsManager()
        d = mgr.to_dict()
        assert "requests" in d
        assert "policies" in d


# ── 9. TestAutonomyManager ────────────────────────────────────────────────────


class TestAutonomyManager:
    def test_default_level(self) -> None:
        mgr = AutonomyManager()
        assert mgr.get_level() == 0.5

    def test_set_level_clamp_high(self) -> None:
        mgr = AutonomyManager()
        mgr.set_level(2.0)
        assert mgr.get_level() == 1.0

    def test_set_level_clamp_low(self) -> None:
        mgr = AutonomyManager()
        mgr.set_level(-1.0)
        assert mgr.get_level() == 0.0

    def test_capabilities_at_low_level(self) -> None:
        mgr = AutonomyManager()
        mgr.set_level(0.1)
        caps = mgr.get_capabilities()
        assert "read" in caps
        assert "analyze" in caps

    def test_capabilities_at_high_level(self) -> None:
        mgr = AutonomyManager()
        mgr.set_level(0.9)
        caps = mgr.get_capabilities()
        assert "self_improve" in caps
        assert "modify_code" in caps

    def test_can_perform(self) -> None:
        mgr = AutonomyManager()
        mgr.set_level(0.1)
        assert mgr.can_perform("read") is True
        assert mgr.can_perform("execute_task") is False

    def test_requires_approval_high_risk(self) -> None:
        mgr = AutonomyManager()
        mgr.set_level(0.8)
        assert mgr.requires_approval("self_improve") is True

    def test_requires_approval_low_level(self) -> None:
        mgr = AutonomyManager()
        mgr.set_level(0.3)
        assert mgr.requires_approval("create_project") is True

    def test_to_dict(self) -> None:
        mgr = AutonomyManager()
        d = mgr.to_dict()
        assert "level" in d
        assert "capabilities" in d
        assert "policies" in d


# ── 10. TestDecisionEngine ────────────────────────────────────────────────────


class TestDecisionEngine:
    def test_make_decision(self) -> None:
        eng = DecisionEngine()
        d = eng.make_decision("deploy", "Deploy v1", {"risk": "low"}, confidence=0.8)
        assert isinstance(d, GovernorDecision)
        assert d.decision_type == "deploy"
        assert d.requires_approval is False

    def test_make_decision_low_confidence(self) -> None:
        eng = DecisionEngine()
        d = eng.make_decision("test", "desc", confidence=0.5)
        assert d.requires_approval is True

    def test_get_decision(self) -> None:
        eng = DecisionEngine()
        d = eng.make_decision("test", "desc")
        assert eng.get_decision(d.id) is d

    def test_list_decisions(self) -> None:
        eng = DecisionEngine()
        eng.make_decision("a", "desc1")
        eng.make_decision("a", "desc2")
        eng.make_decision("b", "desc3")
        a_list = eng.list_decisions(decision_type="a")
        assert len(a_list) == 2

    def test_approve_decision(self) -> None:
        eng = DecisionEngine()
        d = eng.make_decision("test", "desc")
        eng.approve_decision(d.id)
        assert d.approved is True
        assert d.action_taken == "approved"

    def test_reject_decision(self) -> None:
        eng = DecisionEngine()
        d = eng.make_decision("test", "desc")
        eng.reject_decision(d.id)
        assert d.approved is False
        assert d.action_taken == "rejected"

    def test_list_decisions_limit(self) -> None:
        eng = DecisionEngine()
        for i in range(10):
            eng.make_decision("t", f"desc{i}")
        assert len(eng.list_decisions(limit=3)) == 3

    def test_to_dict(self) -> None:
        eng = DecisionEngine()
        d = eng.to_dict()
        assert isinstance(d, dict)


# ── 11. TestRecommendationEngine ──────────────────────────────────────────────


class TestRecommendationEngine:
    def test_create(self) -> None:
        eng = RecommendationEngine()
        r = eng.create("perf", "Optimize", "Improve speed", "high", "high", "medium")
        assert r.category == "perf"
        assert r.priority == "high"
        assert r.status == "pending"

    def test_accept(self) -> None:
        eng = RecommendationEngine()
        r = eng.create("c", "T", "D")
        eng.accept(r.id)
        assert r.status == "accepted"

    def test_reject(self) -> None:
        eng = RecommendationEngine()
        r = eng.create("c", "T", "D")
        eng.reject(r.id)
        assert r.status == "rejected"

    def test_implement(self) -> None:
        eng = RecommendationEngine()
        r = eng.create("c", "T", "D")
        eng.implement(r.id)
        assert r.status == "implemented"

    def test_list_all(self) -> None:
        eng = RecommendationEngine()
        eng.create("a", "T1", "D1")
        eng.create("b", "T2", "D2")
        assert len(eng.list_all()) == 2
        assert len(eng.list_all(category="a")) == 1

    def test_get_pending(self) -> None:
        eng = RecommendationEngine()
        r = eng.create("c", "T", "D")
        eng.accept(r.id)
        eng.create("c", "T2", "D2")
        pending = eng.get_pending()
        assert len(pending) == 1

    def test_get_nonexistent(self) -> None:
        eng = RecommendationEngine()
        assert eng.get("fake") is None


# ── 12. TestOptimizationEngine ────────────────────────────────────────────────


class TestOptimizationEngine:
    def test_analyze(self) -> None:
        eng = OptimizationEngine()
        o = eng.analyze("perf", "slow", "fast", "2x improvement", 5, "high")
        assert o.category == "perf"
        assert o.priority == 5
        assert o.status == "identified"

    def test_prioritize(self) -> None:
        eng = OptimizationEngine()
        eng.analyze("a", "cur", "pro", "imp", priority=1)
        eng.analyze("b", "cur", "pro", "imp", priority=5)
        ordered = eng.prioritize()
        assert ordered[0].priority == 5

    def test_approve(self) -> None:
        eng = OptimizationEngine()
        o = eng.analyze("a", "cur", "pro", "imp")
        eng.approve(o.id)
        assert o.status == "approved"

    def test_implement(self) -> None:
        eng = OptimizationEngine()
        o = eng.analyze("a", "cur", "pro", "imp")
        eng.implement(o.id)
        assert o.status == "implemented"

    def test_list_all_filter(self) -> None:
        eng = OptimizationEngine()
        eng.analyze("a", "cur", "pro", "imp")
        eng.analyze("b", "cur", "pro", "imp")
        assert len(eng.list_all(category="a")) == 1

    def test_get(self) -> None:
        eng = OptimizationEngine()
        o = eng.analyze("a", "cur", "pro", "imp")
        assert eng.get(o.id) is o


# ── 13. TestOrchestrator ──────────────────────────────────────────────────────


class TestOrchestrator:
    def _make(self) -> Orchestrator:
        obj = ObjectivesManager()
        proj = ProjectsManager()
        appr = ApprovalsManager()
        gov = GovernorOrchestrator(obj, proj, appr)
        return Orchestrator(
            governor=gov,
            objectives_mgr=obj,
            projects_mgr=proj,
            roadmap_mgr=RoadmapManager(),
            backlog_mgr=BacklogManager(),
            approvals_mgr=appr,
            decisions_engine=DecisionEngine(),
        )

    @pytest.mark.asyncio
    async def test_orchestrate_returns_result(self) -> None:
        orch = self._make()
        result = await orch.orchestrate("Build a feature to add login")
        assert "objective" in result
        assert "project" in result
        assert "milestones" in result
        assert "goals" in result
        assert "tasks" in result
        assert "decision" in result

    @pytest.mark.asyncio
    async def test_orchestrate_creates_objective(self) -> None:
        orch = self._make()
        result = await orch.orchestrate("Fix bug in auth")
        obj = orch.objectives.get(result["objective"]["id"])
        assert obj is not None
        assert obj.title == "Fix bug in auth"

    @pytest.mark.asyncio
    async def test_orchestrate_creates_project(self) -> None:
        orch = self._make()
        result = await orch.orchestrate("Add new feature")
        proj = orch.projects.get(result["project"]["id"])
        assert proj is not None

    @pytest.mark.asyncio
    async def test_orchestrate_long_term_creates_roadmap(self) -> None:
        orch = self._make()
        text = " ".join(["word"] * 35)
        result = await orch.orchestrate(text)
        assert result["roadmap"] is not None

    @pytest.mark.asyncio
    async def test_get_status(self) -> None:
        orch = self._make()
        status = await orch.get_status()
        assert "active_objectives" in status
        assert "phase" in status

    @pytest.mark.asyncio
    async def test_recommend_next_no_objectives(self) -> None:
        orch = self._make()
        rec = await orch.recommend_next()
        assert rec["action"] == "create_objective"

    @pytest.mark.asyncio
    async def test_recommend_next_with_pending_approval(self) -> None:
        orch = self._make()
        orch.approvals.request(action_type="deploy", description="D")
        rec = await orch.recommend_next()
        assert rec["action"] == "review_approval"

    @pytest.mark.asyncio
    async def test_recommend_next_continue(self) -> None:
        orch = self._make()
        orch.objectives.create(title="Active")
        rec = await orch.recommend_next()
        assert rec["action"] == "continue_objective"

    @pytest.mark.asyncio
    async def test_recommend_next_promote_backlog(self) -> None:
        orch = self._make()
        orch.backlog.add(title="Backlog item")
        rec = await orch.recommend_next()
        assert rec["action"] == "promote_backlog"

    def test_to_dict(self) -> None:
        orch = self._make()
        d = orch.to_dict()
        assert "governor" in d


# ── 14. TestCommandCenterLifecycle ────────────────────────────────────────────


class TestCommandCenterLifecycle:
    def test_start(self) -> None:
        lc = CommandCenterLifecycle()
        result = lc.start()
        assert result["success"] is True
        assert lc.get_phase() == "running"

    def test_stop(self) -> None:
        lc = CommandCenterLifecycle()
        lc.start()
        result = lc.stop()
        assert result["success"] is True
        assert lc.get_phase() == "stopped"

    def test_pause(self) -> None:
        lc = CommandCenterLifecycle()
        lc.start()
        result = lc.pause()
        assert result["success"] is True
        assert lc.get_phase() == "paused"

    def test_resume(self) -> None:
        lc = CommandCenterLifecycle()
        lc.start()
        lc.pause()
        result = lc.resume()
        assert result["success"] is True
        assert lc.get_phase() == "running"

    def test_invalid_transition(self) -> None:
        lc = CommandCenterLifecycle()
        result = lc.stop()
        assert result["success"] is False

    def test_record_event(self) -> None:
        lc = CommandCenterLifecycle()
        event = lc.record_event("custom_event", {"key": "value"})
        assert event["event_type"] == "custom_event"
        assert lc.events[-1]["data"]["key"] == "value"

    def test_get_events(self) -> None:
        lc = CommandCenterLifecycle()
        lc.record_event("e1")
        lc.record_event("e2")
        events = lc.get_events()
        assert len(events) == 2

    def test_uptime(self) -> None:
        lc = CommandCenterLifecycle()
        assert lc.uptime() == 0.0
        lc.start()
        assert lc.uptime() >= 0.0

    def test_to_dict(self) -> None:
        lc = CommandCenterLifecycle()
        d = lc.to_dict()
        assert "phase" in d
        assert "phase_history" in d


# ── 15. TestMetricsCollector ──────────────────────────────────────────────────


class TestMetricsCollector:
    def test_increment(self) -> None:
        mc = MetricsCollector()
        mc.increment("requests")
        mc.increment("requests", 5)
        assert mc.get_counter("requests") == 6

    def test_decrement(self) -> None:
        mc = MetricsCollector()
        mc.increment("items", 10)
        mc.decrement("items", 3)
        assert mc.get_counter("items") == 7

    def test_set_gauge(self) -> None:
        mc = MetricsCollector()
        mc.set_gauge("cpu", 75.5)
        assert mc.get_gauge("cpu") == 75.5

    def test_observe(self) -> None:
        mc = MetricsCollector()
        mc.observe("latency", 10.0)
        mc.observe("latency", 20.0)
        h = mc.get_histogram("latency")
        assert h["count"] == 2
        assert h["avg"] == 15.0

    def test_snapshot(self) -> None:
        mc = MetricsCollector()
        mc.increment("c")
        mc.set_gauge("g", 1.0)
        mc.observe("h", 5.0)
        snap = mc.snapshot()
        assert "counters" in snap
        assert "gauges" in snap
        assert "histograms" in snap

    def test_reset(self) -> None:
        mc = MetricsCollector()
        mc.increment("c")
        mc.set_gauge("g", 1.0)
        mc.reset()
        assert mc.get_counter("c") == 0
        assert mc.get_gauge("g") is None


# ── 16. TestTracingManager ────────────────────────────────────────────────────


class TestTracingManager:
    def test_start_span(self) -> None:
        tm = TracingManager()
        span = tm.start_span("op1")
        assert span["operation"] == "op1"
        assert span["status"] == "in_progress"
        assert span["trace_id"] is not None

    def test_end_span(self) -> None:
        tm = TracingManager()
        span = tm.start_span("op1")
        ended = tm.end_span(span["span_id"], status="completed", result="ok")
        assert ended["status"] == "completed"
        assert ended["duration_ms"] is not None

    def test_end_span_nonexistent(self) -> None:
        tm = TracingManager()
        assert tm.end_span("fake") is None

    def test_get_trace(self) -> None:
        tm = TracingManager()
        s1 = tm.start_span("op1")
        s2 = tm.start_span("op2", parent_span_id=s1["span_id"])
        trace = tm.get_trace(s1["trace_id"])
        assert len(trace) == 2

    def test_list_spans(self) -> None:
        tm = TracingManager()
        tm.start_span("op1")
        tm.start_span("op2")
        tm.start_span("op1")
        assert len(tm.list_spans(operation="op1")) == 2
        assert len(tm.list_spans()) == 3

    def test_list_spans_limit(self) -> None:
        tm = TracingManager()
        for _ in range(10):
            tm.start_span("op")
        assert len(tm.list_spans(limit=3)) == 3

    def test_to_dict(self) -> None:
        tm = TracingManager()
        d = tm.to_dict()
        assert "total_spans" in d
        assert "total_traces" in d


# ── 17. TestSchemas ───────────────────────────────────────────────────────────


class TestSchemas:
    def test_command_request(self) -> None:
        r = CommandRequest(command="test", parameters={"k": "v"})
        assert r.command == "test"
        assert r.id is not None

    def test_command_response(self) -> None:
        r = CommandResponse(command="test", status="completed", result={"ok": True})
        assert r.status == "completed"

    def test_objective(self) -> None:
        o = Objective(title="T", description="D", category="c")
        assert o.title == "T"
        assert o.priority == 3

    def test_project(self) -> None:
        p = Project(name="P", description="D")
        assert p.name == "P"
        assert p.status == "planning"

    def test_roadmap(self) -> None:
        r = Roadmap(name="R", duration_years=2)
        assert r.duration_years == 2

    def test_roadmap_phase(self) -> None:
        rp = RoadmapPhase(title="Phase1", order=1, duration_months=6)
        assert rp.order == 1

    def test_milestone(self) -> None:
        m = Milestone(title="M", objective_id="oid")
        assert m.status == "pending"

    def test_backlog_item(self) -> None:
        b = BacklogItem(title="B", priority=2, source="governor")
        assert b.priority == 2

    def test_governor_decision(self) -> None:
        d = GovernorDecision(decision_type="test", confidence=0.9)
        assert d.confidence == 0.9

    def test_approval_request(self) -> None:
        a = ApprovalRequest(action_type="deploy", risk_level="high")
        assert a.risk_level == "high"

    def test_recommendation(self) -> None:
        r = Recommendation(category="perf", title="Optimize", priority="high")
        assert r.priority == "high"

    def test_optimization(self) -> None:
        o = Optimization(category="perf", current_state="slow", proposed_state="fast")
        assert o.status == "identified"

    def test_lifecycle_state(self) -> None:
        ls = LifecycleState(phase="ready")
        assert ls.phase == "ready"

    def test_command_metrics(self) -> None:
        cm = CommandMetrics(total_commands=10, successful=8)
        assert cm.total_commands == 10


# ── 18. TestFactory ───────────────────────────────────────────────────────────


class TestFactory:
    def test_create_all_returns_all_keys(self) -> None:
        result = CommandCenterFactory.create_all()
        expected_keys = {
            "objectives",
            "projects",
            "roadmap",
            "backlog",
            "milestones",
            "approvals",
            "autonomy",
            "decisions",
            "recommendations",
            "optimization",
            "lifecycle",
            "metrics",
            "tracing",
            "self_improvement",
            "governor",
            "orchestrator",
            "command_center",
        }
        assert expected_keys == set(result.keys())

    def test_create_all_types(self) -> None:
        result = CommandCenterFactory.create_all()
        assert isinstance(result["objectives"], ObjectivesManager)
        assert isinstance(result["projects"], ProjectsManager)
        assert isinstance(result["roadmap"], RoadmapManager)
        assert isinstance(result["backlog"], BacklogManager)
        assert isinstance(result["milestones"], MilestonesManager)
        assert isinstance(result["approvals"], ApprovalsManager)
        assert isinstance(result["autonomy"], AutonomyManager)
        assert isinstance(result["decisions"], DecisionEngine)
        assert isinstance(result["recommendations"], RecommendationEngine)
        assert isinstance(result["optimization"], OptimizationEngine)
        assert isinstance(result["lifecycle"], CommandCenterLifecycle)
        assert isinstance(result["metrics"], MetricsCollector)
        assert isinstance(result["tracing"], TracingManager)
        assert isinstance(result["self_improvement"], SelfImprovementEngine)
        assert isinstance(result["governor"], GovernorOrchestrator)
        assert isinstance(result["orchestrator"], Orchestrator)

    def test_create_all_lifecycle_started(self) -> None:
        result = CommandCenterFactory.create_all()
        assert result["lifecycle"].get_phase() == "running"

    def test_create_all_components_list(self) -> None:
        result = CommandCenterFactory.create_all()
        cc = result["command_center"]
        assert cc["version"] == "1.0.0"
        assert len(cc["components"]) == 16


# ── 19. TestApprovalsManagerEnhanced ────────────────────────────────────────


class TestApprovalsManagerEnhanced:
    def test_mandatory_category_architectural(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(action_type="system_config", description="Refactor module structure")
        assert r.metadata.get("mandatory_category") == "architectural"
        assert r.risk_level == "critical"

    def test_mandatory_category_destructive(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(action_type="execute_code", description="Delete and remove all old files")
        assert r.metadata.get("mandatory_category") == "destructive"
        assert r.risk_level == "critical"

    def test_mandatory_category_security(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(action_type="system_config", description="Update auth certificates")
        assert r.metadata.get("mandatory_category") == "security"
        assert r.risk_level == "critical"

    def test_mandatory_category_production(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(action_type="system_config", description="Deploy to production server")
        assert r.metadata.get("mandatory_category") == "production"
        assert r.risk_level == "critical"

    def test_mandatory_category_data(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(action_type="execute_code", description="Migrate database schema")
        assert r.metadata.get("mandatory_category") == "data"
        assert r.risk_level == "high"

    def test_mandatory_category_strategic(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(action_type="modify_objective", description="Change roadmap priorities")
        assert r.metadata.get("mandatory_category") == "strategic"
        assert r.risk_level == "high"

    def test_no_mandatory_category(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(action_type="autonomous_task", description="Simple configuration update")
        assert r.metadata.get("mandatory_category") is None

    def test_requires_mandatory_approval(self) -> None:
        mgr = ApprovalsManager()
        assert mgr.requires_mandatory_approval("Deploy to production server") == "production"
        assert mgr.requires_mandatory_approval("Delete all files") == "destructive"
        assert mgr.requires_mandatory_approval("Simple update") is None

    def test_bulk_approve(self) -> None:
        mgr = ApprovalsManager()
        r1 = mgr.request(action_type="deploy", description="D1")
        r2 = mgr.request(action_type="deploy", description="D2")
        results = mgr.bulk_approve([r1.id, r2.id], reviewer="admin")
        assert len(results) == 2
        assert all(r.status == "approved" for r in results)

    def test_bulk_reject(self) -> None:
        mgr = ApprovalsManager()
        r1 = mgr.request(action_type="deploy", description="D1")
        r2 = mgr.request(action_type="deploy", description="D2")
        results = mgr.bulk_reject([r1.id, r2.id], reviewer="admin", reason="no")
        assert len(results) == 2
        assert all(r.status == "rejected" for r in results)

    def test_bulk_approve_nonexistent(self) -> None:
        mgr = ApprovalsManager()
        results = mgr.bulk_approve(["fake1", "fake2"])
        assert results == [None, None]

    def test_audit_log(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(action_type="deploy", description="D")
        mgr.approve(r.id, reviewer="admin")
        log = mgr.get_audit_log()
        assert len(log) == 2
        assert log[0]["action"] == "request"
        assert log[1]["action"] == "approve"

    def test_audit_log_limit(self) -> None:
        mgr = ApprovalsManager()
        for i in range(10):
            mgr.request(action_type="deploy", description=f"D{i}")
        log = mgr.get_audit_log(limit=3)
        assert len(log) == 3

    def test_get_mandatory_categories(self) -> None:
        mgr = ApprovalsManager()
        cats = mgr.get_mandatory_categories()
        assert "architectural" in cats
        assert "destructive" in cats
        assert "security" in cats
        assert "production" in cats
        assert "data" in cats
        assert "strategic" in cats
        assert len(cats) == 6

    def test_to_dict_includes_mandatory(self) -> None:
        mgr = ApprovalsManager()
        d = mgr.to_dict()
        assert "mandatory_categories" in d
        assert "audit_log_size" in d

    def test_expire_stale(self) -> None:
        mgr = ApprovalsManager()
        r = mgr.request(action_type="deploy", description="D")
        r.created_at = "2020-01-01T00:00:00"
        expired = mgr.expire_stale(max_age_seconds=60)
        assert len(expired) == 1
        assert expired[0].status == "expired"


# ── 20. TestOrchestratorEnhanced ────────────────────────────────────────────


class TestOrchestratorEnhanced:
    def _make(self) -> Orchestrator:
        obj = ObjectivesManager()
        proj = ProjectsManager()
        appr = ApprovalsManager()
        gov = GovernorOrchestrator(obj, proj, appr)
        return Orchestrator(
            governor=gov,
            objectives_mgr=obj,
            projects_mgr=proj,
            roadmap_mgr=RoadmapManager(),
            backlog_mgr=BacklogManager(),
            approvals_mgr=appr,
            decisions_engine=DecisionEngine(),
        )

    @pytest.mark.asyncio
    async def test_execute_plan_returns_result(self) -> None:
        orch = self._make()
        result = await orch.orchestrate("Build a feature")
        plan = {
            "id": "plan-1",
            "phases": [{"name": "Phase1", "tasks": [{"t": 1}]}],
            "strategy": "agile",
            "milestones": [],
            "goals": [],
            "dependencies_graph": {},
        }
        exec_result = await orch.execute_plan(result["orchestration_id"], plan)
        assert exec_result["status"] == "completed"
        assert exec_result["phases_executed"] == 1

    @pytest.mark.asyncio
    async def test_execute_plan_not_found(self) -> None:
        orch = self._make()
        exec_result = await orch.execute_plan("nonexistent", {})
        assert "error" in exec_result

    @pytest.mark.asyncio
    async def test_execute_plan_updates_objective(self) -> None:
        orch = self._make()
        result = await orch.orchestrate("Build a feature")
        plan = {
            "id": "plan-1",
            "phases": [{"name": "Phase1", "tasks": []}],
            "strategy": "incremental",
            "milestones": [{"title": "M1"}],
            "goals": [{"title": "G1"}],
        }
        exec_result = await orch.execute_plan(result["orchestration_id"], plan)
        obj = orch.objectives.get(result["objective"]["id"])
        assert obj.analysis["strategy"] == "incremental"
        assert obj.analysis["milestone_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_plan_updates_project_phases(self) -> None:
        orch = self._make()
        result = await orch.orchestrate("Build a feature")
        plan = {
            "id": "plan-1",
            "phases": [{"name": "P1"}, {"name": "P2"}],
            "strategy": "phased",
        }
        exec_result = await orch.execute_plan(result["orchestration_id"], plan)
        proj = orch.projects.get(result["project"]["id"])
        assert len(proj.phases) == 2

    @pytest.mark.asyncio
    async def test_get_status_includes_executions(self) -> None:
        orch = self._make()
        result = await orch.orchestrate("Build something")
        plan = {"id": "p1", "phases": [{"name": "P1", "tasks": []}], "strategy": "quick"}
        await orch.execute_plan(result["orchestration_id"], plan)
        status = await orch.get_status()
        assert status["executions_completed"] == 1

    @pytest.mark.asyncio
    async def test_to_dict_includes_executions(self) -> None:
        orch = self._make()
        d = orch.to_dict()
        assert "executions_completed" in d


# ── 21. TestSelfImprovementEngine ──────────────────────────────────────────


class TestSelfImprovementEngine:
    def test_record_metric(self) -> None:
        eng = SelfImprovementEngine()
        entry = eng.record_metric("latency", 150.0, {"context": "test"})
        assert entry["name"] == "latency"
        assert entry["value"] == 150.0

    def test_record_multiple_metrics(self) -> None:
        eng = SelfImprovementEngine()
        for i in range(10):
            eng.record_metric("latency", 100.0 + i)
        summary = eng.get_metrics_summary()
        assert summary["total_entries"] == 10
        assert "latency" in summary["metrics"]

    def test_detect_patterns_insufficient_data(self) -> None:
        eng = SelfImprovementEngine()
        for i in range(2):
            eng.record_metric("latency", 100.0)
        patterns = eng.detect_patterns()
        assert len(patterns) == 0

    def test_detect_patterns_stable(self) -> None:
        eng = SelfImprovementEngine()
        for _ in range(10):
            eng.record_metric("latency", 100.0)
        patterns = eng.detect_patterns()
        assert len(patterns) == 1
        assert patterns[0]["trend"] == "stable"

    def test_detect_patterns_improving(self) -> None:
        eng = SelfImprovementEngine()
        for i in range(10):
            eng.record_metric("latency", 50.0 + i * 10)
        patterns = eng.detect_patterns()
        assert any(p["trend"] == "improving" for p in patterns)

    def test_detect_patterns_degrading(self) -> None:
        eng = SelfImprovementEngine()
        for i in range(10):
            eng.record_metric("latency", 200.0 - i * 10)
        patterns = eng.detect_patterns()
        assert any(p["trend"] == "degrading" for p in patterns)

    def test_suggest_improvements(self) -> None:
        eng = SelfImprovementEngine()
        for i in range(10):
            eng.record_metric("error_rate", 0.5 - i * 0.04)
        eng.detect_patterns()
        suggestions = eng.suggest_improvements()
        assert len(suggestions) > 0
        assert suggestions[0]["priority"] == "high"

    def test_suggest_improvements_none(self) -> None:
        eng = SelfImprovementEngine()
        for _ in range(10):
            eng.record_metric("latency", 100.0)
        eng.detect_patterns()
        suggestions = eng.suggest_improvements()
        assert len(suggestions) == 0

    def test_record_improvement(self) -> None:
        eng = SelfImprovementEngine()
        imp = eng.record_improvement("performance", "Cache optimization", "Added Redis caching")
        assert imp["status"] == "implemented"
        assert imp["category"] == "performance"

    def test_get_improvements(self) -> None:
        eng = SelfImprovementEngine()
        eng.record_improvement("performance", "T1", "D1")
        eng.record_improvement("accuracy", "T2", "D2")
        assert len(eng.get_improvements()) == 2
        assert len(eng.get_improvements(category="performance")) == 1

    def test_get_patterns_filter(self) -> None:
        eng = SelfImprovementEngine()
        for _ in range(5):
            eng.record_metric("latency", 100.0)
        for i in range(5):
            eng.record_metric("error_rate", 0.5 - i * 0.1)
        eng.detect_patterns()
        stable = eng.get_patterns(trend="stable")
        degrading = eng.get_patterns(trend="degrading")
        assert len(stable) >= 1
        assert len(degrading) >= 1

    def test_enable_disable(self) -> None:
        eng = SelfImprovementEngine()
        assert eng.is_enabled() is True
        eng.set_enabled(False)
        assert eng.is_enabled() is False

    def test_metrics_history_capped(self) -> None:
        eng = SelfImprovementEngine()
        for i in range(1200):
            eng.record_metric("latency", float(i))
        assert len(eng._metrics_history) <= 1000

    def test_to_dict(self) -> None:
        eng = SelfImprovementEngine()
        d = eng.to_dict()
        assert "enabled" in d
        assert "total_improvements" in d
        assert "categories" in d

    def test_categorize_improvement(self) -> None:
        eng = SelfImprovementEngine()
        assert eng._categorize_improvement("failure_count") == "robustness"
        assert eng._categorize_improvement("cache_hit_ratio") == "performance"
        assert eng._categorize_improvement("unknown_metric") == "general"


# ── 22. TestGovernorEnhanced ────────────────────────────────────────────────


class TestGovernorEnhanced:
    def _make_governor(self) -> GovernorCore:
        return GovernorCore(ObjectivesManager(), ProjectsManager(), ApprovalsManager())

    @pytest.mark.asyncio
    async def test_analyze_execution_strategies(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective("Build a simple tool")
        assert "execution_strategies" in result
        assert len(result["execution_strategies"]) >= 1

    @pytest.mark.asyncio
    async def test_analyze_resource_needs(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective("Build a simple tool")
        assert "required_resources" in result
        assert len(result["required_resources"]) >= 1

    @pytest.mark.asyncio
    async def test_analyze_risks_business(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective("Build a company with revenue growth")
        risk_names = [r["risk"] for r in result["key_risks"]]
        assert "Market timing" in risk_names

    @pytest.mark.asyncio
    async def test_analyze_risks_financial(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective("Manage investment portfolio with crypto trading")
        risk_names = [r["risk"] for r in result["key_risks"]]
        assert "Cash flow issues" in risk_names

    @pytest.mark.asyncio
    async def test_analyze_opportunities_business(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective("Launch a startup business")
        opp_names = [o["opportunity"] for o in result["opportunities"]]
        assert "Market expansion" in opp_names

    @pytest.mark.asyncio
    async def test_analyze_dependencies_technology(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective("Build software API system")
        dep_types = [d["type"] for d in result["dependencies"]]
        assert "infrastructure" in dep_types

    @pytest.mark.asyncio
    async def test_analyze_requires_approval(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective("Deploy to production server")
        assert result["requires_human_approval"] is True

    @pytest.mark.asyncio
    async def test_analyze_requires_open_code(self) -> None:
        g = self._make_governor()
        result = await g.analyze_objective("Build a software application")
        assert result["requires_open_code"] is True

    def test_tool_orchestration_code_task(self) -> None:
        g = self._make_governor()
        decisions = g.decide_tool_orchestration("Implement login feature", "technology", "medium")
        assert decisions["use_open_code"] is True
        assert decisions["use_agents"] is True

    def test_tool_orchestration_research_task(self) -> None:
        g = self._make_governor()
        decisions = g.decide_tool_orchestration("Research AI trends", "research", "medium")
        assert decisions["use_research"] is True

    def test_tool_orchestration_api_task(self) -> None:
        g = self._make_governor()
        decisions = g.decide_tool_orchestration("Integrate third-party API", "technology", "medium")
        assert decisions["use_apis"] is True

    def test_tool_orchestration_high_risk(self) -> None:
        g = self._make_governor()
        decisions = g.decide_tool_orchestration("Deploy to production", "technology", "high")
        assert decisions["human_approval_required"] is True
        assert decisions["use_workflows"] is True

    def test_execution_strategies_very_high(self) -> None:
        g = self._make_governor()
        strategies = g._generate_execution_strategies("very_high", "technology")
        names = [s["name"] for s in strategies]
        assert "phased" in names

    def test_execution_strategies_low(self) -> None:
        g = self._make_governor()
        strategies = g._generate_execution_strategies("low", "general")
        names = [s["name"] for s in strategies]
        assert "quick_win" in names

    def test_build_dependency_graph(self) -> None:
        g = self._make_governor()
        tasks = [{"title": "T1"}, {"title": "T2"}, {"title": "T3"}]
        graph = g._build_dependency_graph(tasks, [])
        assert "T1" in graph
        assert "T2" in graph
        assert "T1" in graph["T2"]
        assert "T2" in graph["T3"]

    def test_assess_resource_needs_high(self) -> None:
        g = self._make_governor()
        resources = g._assess_resource_needs("high", "technology")
        types = [r["type"] for r in resources]
        assert "storage" in types
        assert "development_tools" in types

    def test_assess_risks_high_complexity(self) -> None:
        g = self._make_governor()
        risks = g._assess_risks("test", "general", "high")
        risk_names = [r["risk"] for r in risks]
        assert "Technical debt accumulation" in risk_names

    def test_categorize_community(self) -> None:
        g = self._make_governor()
        assert g._categorize_objective("Organize community meetup event") == "community"

    def test_categorize_research(self) -> None:
        g = self._make_governor()
        assert g._categorize_objective("Research and experiment with new methods") == "research"

    def test_decision_history(self) -> None:
        g = self._make_governor()
        g._decision_history = [GovernorDecision(decision_type=f"d{i}") for i in range(10)]
        history = g.get_decision_history(limit=5)
        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_create_plan_phases(self) -> None:
        g = self._make_governor()
        tasks = [{"title": f"T{i}"} for i in range(9)]
        plan = await g.create_plan({
            "tasks": tasks,
            "milestones": [],
            "goals": [],
            "category": "tech",
        })
        assert len(plan["phases"]) == 3
        assert plan["phases"][0]["name"] == "Foundation"
        assert plan["phases"][1]["name"] == "Execution"
        assert plan["phases"][2]["name"] == "Completion"
