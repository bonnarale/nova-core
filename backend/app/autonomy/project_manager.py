from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .objective_manager import ObjectiveManager


class ProjectManager:
    def __init__(self) -> None:
        self._projects: dict[str, dict] = {}
        self._objective_manager = ObjectiveManager()

    def create_project(self, objective_text: str) -> dict:
        analysis = self._objective_manager.analyze_objective(objective_text)
        plan = self._objective_manager.create_plan(objective_text, analysis)
        project_id = str(uuid.uuid4())
        project = {
            "id": project_id,
            "objective": objective_text,
            "analysis": analysis,
            "plan": {
                "id": plan.id,
                "title": plan.title,
                "milestones": plan.milestones,
                "goals": plan.goals,
                "tasks": plan.tasks,
                "workflows": plan.workflows,
                "tools_needed": plan.tools_needed,
                "agents_needed": plan.agents_needed,
                "risk_assessment": plan.risk_assessment,
                "estimated_duration": plan.estimated_duration,
            },
            "status": "analyzing",
            "progress": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._projects[project_id] = project
        return project

    def get_project(self, project_id: str) -> dict | None:
        return self._projects.get(project_id)

    def update_project(self, project_id: str, **kwargs: object) -> dict | None:
        project = self._projects.get(project_id)
        if project is None:
            return None
        project.update(kwargs)
        project["updated_at"] = datetime.now(timezone.utc).isoformat()
        return project

    def list_projects(self, status: str | None = None) -> list[dict]:
        projects = list(self._projects.values())
        if status is not None:
            projects = [p for p in projects if p["status"] == status]
        return projects

    def get_project_status(self, project_id: str) -> dict | None:
        project = self._projects.get(project_id)
        if project is None:
            return None
        tasks = project.get("plan", {}).get("tasks", [])
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        total = len(tasks) if tasks else 1
        return {
            "id": project["id"],
            "status": project["status"],
            "progress": project["progress"],
            "tasks_completed": completed,
            "tasks_total": len(tasks),
            "updated_at": project["updated_at"],
        }

    def to_dict(self) -> dict:
        return {"projects": dict(self._projects)}
