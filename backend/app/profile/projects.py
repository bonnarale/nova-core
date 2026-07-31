from __future__ import annotations

from datetime import datetime, timezone

from .schemas import Project


class ProjectsManager:
    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}

    def create_project(
        self,
        name: str,
        description: str = "",
        owner_id: str | None = None,
        priority: int = 3,
        tags: list[str] | None = None,
    ) -> dict:
        project = Project(
            name=name,
            description=description,
            owner_id=owner_id,
            priority=priority,
            tags=tags if tags is not None else [],
        )
        self.projects[project.id] = project
        return project.to_dict()

    def get_project(self, project_id: str) -> dict | None:
        project = self.projects.get(project_id)
        return project.to_dict() if project else None

    def update_project(self, project_id: str, **kwargs) -> dict | None:
        project = self.projects.get(project_id)
        if not project:
            return None
        for key, value in kwargs.items():
            if hasattr(project, key) and key not in ("id", "created_at"):
                setattr(project, key, value)
        project.updated_at = datetime.now(timezone.utc)
        return project.to_dict()

    def archive_project(self, project_id: str) -> dict | None:
        project = self.projects.get(project_id)
        if not project:
            return None
        project.status = "archived"
        project.updated_at = datetime.now(timezone.utc)
        return project.to_dict()

    def delete_project(self, project_id: str) -> bool:
        if project_id in self.projects:
            del self.projects[project_id]
            return True
        return False

    def list_projects(
        self, status: str | None = None, owner_id: str | None = None
    ) -> list[dict]:
        result = list(self.projects.values())
        if status:
            result = [p for p in result if p.status == status]
        if owner_id:
            result = [p for p in result if p.owner_id == owner_id]
        return [p.to_dict() for p in result]

    def to_dict(self) -> dict:
        return {pid: p.to_dict() for pid, p in self.projects.items()}
