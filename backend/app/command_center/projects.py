from __future__ import annotations

from .schemas import Project


class ProjectsManager:
    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}

    def create(
        self,
        name: str,
        description: str = "",
        objective_id: str | None = None,
    ) -> Project:
        project = Project(
            name=name,
            description=description,
            objective_id=objective_id,
        )
        self.projects[project.id] = project
        return project

    def update(self, project_id: str, **kwargs: object) -> Project | None:
        project = self.projects.get(project_id)
        if project is None:
            return None
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)
        return project

    def complete(self, project_id: str) -> Project | None:
        project = self.projects.get(project_id)
        if project is None:
            return None
        project.status = "completed"
        project.progress = 1.0
        return project

    def pause(self, project_id: str) -> Project | None:
        project = self.projects.get(project_id)
        if project is None:
            return None
        project.status = "paused"
        return project

    def resume(self, project_id: str) -> Project | None:
        project = self.projects.get(project_id)
        if project is None:
            return None
        project.status = "active"
        return project

    def get(self, project_id: str) -> Project | None:
        return self.projects.get(project_id)

    def list_all(self, status: str | None = None) -> list[Project]:
        projects = list(self.projects.values())
        if status:
            projects = [p for p in projects if p.status == status]
        return projects

    def add_phase(self, project_id: str, phase: dict) -> bool:
        project = self.projects.get(project_id)
        if project is None:
            return False
        project.phases.append(phase)
        return True

    def add_milestone(self, project_id: str, milestone: dict) -> bool:
        project = self.projects.get(project_id)
        if project is None:
            return False
        project.milestones.append(milestone)
        return True

    def update_progress(self, project_id: str, progress: float) -> Project | None:
        project = self.projects.get(project_id)
        if project is None:
            return None
        project.progress = max(0.0, min(1.0, progress))
        return project

    def to_dict(self) -> dict:
        return {k: v.__dict__ for k, v in self.projects.items()}
