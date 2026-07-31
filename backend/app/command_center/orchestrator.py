from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from .approvals import ApprovalsManager
from .backlog import BacklogManager
from .decisions import DecisionEngine
from .milestones import MilestonesManager
from .objectives import ObjectivesManager
from .projects import ProjectsManager
from .roadmap import RoadmapManager
from .schemas import Objective, _uuid, _utcnow

if TYPE_CHECKING:
    from .governor import Governor


class Orchestrator:
    def __init__(
        self,
        governor: Governor,
        objectives_mgr: ObjectivesManager,
        projects_mgr: ProjectsManager,
        roadmap_mgr: RoadmapManager,
        backlog_mgr: BacklogManager,
        approvals_mgr: ApprovalsManager,
        decisions_engine: DecisionEngine,
    ) -> None:
        self.governor = governor
        self.objectives = objectives_mgr
        self.projects = projects_mgr
        self.roadmap = roadmap_mgr
        self.backlog = backlog_mgr
        self.approvals = approvals_mgr
        self.decisions = decisions_engine
        self._active_orchestrations: dict[str, dict] = {}
        self._execution_history: list[dict] = []

    async def orchestrate(self, objective_text: str) -> dict:
        # Use the rich Governor's analyze_objective (async, deep analysis)
        analysis = await self.governor.analyze_objective(objective_text)
        category = analysis.get("category", "general")
        complexity = analysis.get("complexity", "medium")

        objective = self.objectives.create(
            title=objective_text,
            description=f"Objective: {objective_text}",
            category=category,
            priority=3 if complexity == "low" else 2 if complexity == "medium" else 1,
        )

        project = self.projects.create(
            name=objective_text,
            description=f"Project for: {objective_text}",
            objective_id=objective.id,
        )

        # Use milestones/goals/tasks from the rich analysis if available
        milestones_raw = analysis.get("milestones", [])
        goals_raw = analysis.get("goals", [])
        tasks_raw = analysis.get("tasks", [])

        # Convert analysis milestones to Milestone dataclasses
        from .schemas import Milestone
        milestones_data = []
        for m in milestones_raw:
            if isinstance(m, dict):
                ms = Milestone(
                    title=m.get("title", "Milestone"),
                    description=m.get("description", ""),
                    objective_id=objective.id,
                    project_id=project.id,
                )
                milestones_data.append(ms)
            else:
                milestones_data.append(m)

        # Ensure goals are dicts
        goals_data = []
        for g in goals_raw:
            if isinstance(g, dict):
                goals_data.append(g)
            else:
                goals_data.append({"title": str(g), "status": "pending"})

        # Ensure tasks are dicts
        tasks_data = []
        for t in tasks_raw:
            if isinstance(t, dict):
                tasks_data.append(t)
            else:
                tasks_data.append({"title": str(t), "status": "pending"})

        # Fallback: generate if analysis returned empty
        if not milestones_data:
            milestones_data = self._create_milestones(objective.id, project.id, complexity)
        if not goals_data:
            goals_data = self._create_goals(objective.id, complexity)
        if not tasks_data:
            tasks_data = self._create_tasks(objective.id, project.id, complexity)

        for m in milestones_data:
            self.objectives.add_milestone(objective.id, m)
        for g in goals_data:
            self.objectives.add_goal(objective.id, g)
        for t in tasks_data:
            self.objectives.add_task(objective.id, t)

        is_long_term = complexity in ("high", "very_high") or len(objective_text.split()) > 25
        roadmap_data = None
        if is_long_term:
            roadmap = self.roadmap.create(
                name=objective_text,
                description=f"Long-term roadmap for: {objective_text}",
                duration_years=1,
            )
            roadmap_data = roadmap.__dict__

        workflows = analysis.get("workflows_needed", self._determine_workflows(analysis))
        tools = analysis.get("tools_needed", self._determine_tools(analysis))
        agents = analysis.get("agents_needed", self._determine_agents(analysis))

        decision = self.decisions.make_decision(
            decision_type="orchestration",
            description=f"Orchestrate: {objective_text}",
            context={
                "analysis": analysis,
                "complexity": complexity,
                "is_long_term": is_long_term,
            },
            confidence=0.9 if complexity == "low" else 0.7 if complexity == "medium" else 0.5,
        )

        # Check if approval is required based on rich analysis
        requires_approval = analysis.get("requires_human_approval", False)
        approval = {"requires_approval": requires_approval}
        if requires_approval:
            req = self.approvals.request(
                action_type="create_project",
                description=f"Create project: {objective_text}",
                risk_level="high",
                requester="governor",
            )
            approval["approval_request"] = req.__dict__

        result = {
            "orchestration_id": str(uuid.uuid4()),
            "objective": objective.__dict__,
            "project": project.__dict__,
            "milestones": [m.__dict__ for m in milestones_data],
            "goals": goals_data,
            "tasks": tasks_data,
            "roadmap": roadmap_data,
            "workflows": workflows,
            "tools": tools,
            "agents": agents,
            "decision": decision.__dict__,
            "approval": approval,
            "analysis": analysis,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self._active_orchestrations[result["orchestration_id"]] = result
        return result

    async def execute_plan(self, orchestration_id: str, plan: dict) -> dict:
        orchestration = self._active_orchestrations.get(orchestration_id)
        if orchestration is None:
            return {"error": "Orchestration not found", "orchestration_id": orchestration_id}

        objective_id = orchestration["objective"]["id"]
        project_id = orchestration["project"]["id"]

        phases = plan.get("phases", [])
        execution_results: list[dict] = []

        for phase in phases:
            phase_result = {
                "phase_name": phase.get("name", "unknown"),
                "tasks_completed": 0,
                "tasks_total": len(phase.get("tasks", [])),
                "status": "completed",
            }
            execution_results.append(phase_result)

        objectives_result = self._execute_objectives(objective_id, plan)
        projects_result = self._execute_projects(project_id, plan)
        dependencies = plan.get("dependencies_graph", {})

        execution_record = {
            "orchestration_id": orchestration_id,
            "plan_id": plan.get("id", ""),
            "phases_executed": len(phases),
            "execution_results": execution_results,
            "objectives_result": objectives_result,
            "projects_result": projects_result,
            "dependencies_satisfied": len(dependencies) == 0,
            "status": "completed",
            "executed_at": _utcnow(),
        }

        self._execution_history.append(execution_record)
        return execution_record

    def _execute_objectives(self, objective_id: str, plan: dict) -> dict:
        obj = self.objectives.get(objective_id)
        if obj is None:
            return {"status": "not_found"}
        strategy = plan.get("strategy", "")
        milestones = plan.get("milestones", [])
        goals = plan.get("goals", [])
        obj.analysis = {
            "strategy": strategy,
            "milestone_count": len(milestones),
            "goal_count": len(goals),
        }
        return {"status": "configured", "objective_id": objective_id}

    def _execute_projects(self, project_id: str, plan: dict) -> dict:
        proj = self.projects.get(project_id)
        if proj is None:
            return {"status": "not_found"}
        phases = plan.get("phases", [])
        proj.phases = phases
        return {"status": "configured", "project_id": project_id, "phases_count": len(phases)}

    async def get_status(self) -> dict:
        active_objectives = self.objectives.list_active()
        active_projects = self.projects.list_all(status="active")
        return {
            "active_objectives": len(active_objectives),
            "active_projects": len(active_projects),
            "total_backlog": len(self.backlog.items),
            "active_orchestrations": len(self._active_orchestrations),
            "executions_completed": len(self._execution_history),
            "phase": "running",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def recommend_next(self, context: dict | None = None) -> dict:
        pending = self.approvals.get_pending()
        if pending:
            return {
                "action": "review_approval",
                "reason": f"{len(pending)} pending approval(s)",
                "approval": pending[0].__dict__,
            }

        active_obj = self.objectives.list_active()
        if not active_obj:
            backlog_items = list(self.backlog.items.values())
            if backlog_items:
                return {
                    "action": "promote_backlog",
                    "reason": "No active objectives; promote from backlog",
                    "backlog_item": backlog_items[0].__dict__,
                }
            return {
                "action": "create_objective",
                "reason": "No active objectives or backlog items",
            }

        lowest_progress = min(active_obj, key=lambda o: o.progress)
        return {
            "action": "continue_objective",
            "reason": f"Objective '{lowest_progress.title}' at {lowest_progress.progress:.0%}",
            "objective": lowest_progress.__dict__,
        }

    def _create_milestones(
        self, objective_id: str, project_id: str, complexity: str
    ) -> list:
        from .schemas import Milestone

        count = 3 if complexity == "low" else 5 if complexity == "medium" else 8
        phases = ["Analysis", "Implementation", "Validation", "Refinement", "Delivery"]
        result = []
        for i in range(min(count, len(phases))):
            ms = Milestone(
                title=f"{phases[i]}",
                description=f"Milestone for {phases[i]} phase",
                objective_id=objective_id,
                project_id=project_id,
            )
            result.append(ms)
        return result

    def _create_goals(self, objective_id: str, complexity: str) -> list[dict]:
        count = 2 if complexity == "low" else 3 if complexity == "medium" else 5
        labels = ["Plan", "Execute", "Verify", "Deliver", "Optimize"]
        return [
            {
                "id": str(uuid.uuid4()),
                "title": f"Goal: {labels[i]}",
                "description": f"Complete the {labels[i].lower()} phase",
                "objective_id": objective_id,
                "status": "pending",
            }
            for i in range(min(count, len(labels)))
        ]

    def _create_tasks(
        self, objective_id: str, project_id: str, complexity: str
    ) -> list[dict]:
        count = 3 if complexity == "low" else 6 if complexity == "medium" else 10
        return [
            {
                "id": str(uuid.uuid4()),
                "title": f"Task {i + 1}",
                "description": f"Execute step {i + 1}",
                "objective_id": objective_id,
                "project_id": project_id,
                "status": "pending",
                "priority": 3,
            }
            for i in range(count)
        ]

    def _determine_workflows(self, analysis: dict) -> list[dict]:
        cat = analysis.get("category", "general")
        workflows = [
            {"name": "analysis_workflow", "trigger": "objective_created"},
            {"name": f"{cat}_workflow", "trigger": "objective_approved"},
        ]
        if analysis.get("complexity") == "high":
            workflows.append({"name": "review_cycle", "trigger": "task_completed"})
        return workflows

    def _determine_tools(self, analysis: dict) -> list[str]:
        tools: list[str] = ["code_search"]
        cat = analysis.get("category", "general")
        if cat in ("feature", "refactoring"):
            tools.append("code_generation")
        if cat == "optimization":
            tools.append("profiling")
        if cat == "security":
            tools.append("security_scan")
        return tools

    def _determine_agents(self, analysis: dict) -> list[str]:
        agents: list[str] = ["coordinator"]
        if analysis.get("complexity") in ("medium", "high"):
            agents.append("reviewer")
        cat = analysis.get("category", "general")
        if cat in ("feature", "refactoring"):
            agents.append("coder")
        return agents

    def to_dict(self) -> dict:
        return {
            "active_orchestrations": len(self._active_orchestrations),
            "executions_completed": len(self._execution_history),
            "governor": self.governor.to_dict(),
        }
