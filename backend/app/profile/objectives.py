from __future__ import annotations

from datetime import datetime, timezone

from .schemas import Objective


class ObjectivesManager:
    def __init__(self) -> None:
        self.objectives: dict[str, Objective] = {}

    def create_objective(
        self,
        title: str,
        description: str = "",
        project_id: str | None = None,
        priority: int = 3,
    ) -> dict:
        objective = Objective(
            title=title,
            description=description,
            project_id=project_id,
            priority=priority,
        )
        self.objectives[objective.id] = objective
        return objective.to_dict()

    def get_objective(self, objective_id: str) -> dict | None:
        obj = self.objectives.get(objective_id)
        return obj.to_dict() if obj else None

    def update_objective(self, objective_id: str, **kwargs) -> dict | None:
        obj = self.objectives.get(objective_id)
        if not obj:
            return None
        for key, value in kwargs.items():
            if hasattr(obj, key) and key not in ("id", "created_at"):
                setattr(obj, key, value)
        obj.updated_at = datetime.now(timezone.utc)
        return obj.to_dict()

    def complete_objective(self, objective_id: str) -> dict | None:
        obj = self.objectives.get(objective_id)
        if not obj:
            return None
        obj.status = "completed"
        obj.progress = 1.0
        obj.updated_at = datetime.now(timezone.utc)
        return obj.to_dict()

    def cancel_objective(self, objective_id: str) -> dict | None:
        obj = self.objectives.get(objective_id)
        if not obj:
            return None
        obj.status = "cancelled"
        obj.updated_at = datetime.now(timezone.utc)
        return obj.to_dict()

    def update_progress(self, objective_id: str, progress: float) -> dict | None:
        obj = self.objectives.get(objective_id)
        if not obj:
            return None
        obj.progress = max(0.0, min(1.0, progress))
        obj.updated_at = datetime.now(timezone.utc)
        return obj.to_dict()

    def list_objectives(
        self, status: str | None = None, project_id: str | None = None
    ) -> list[dict]:
        result = list(self.objectives.values())
        if status:
            result = [o for o in result if o.status == status]
        if project_id:
            result = [o for o in result if o.project_id == project_id]
        return [o.to_dict() for o in result]

    def to_dict(self) -> dict:
        return {oid: o.to_dict() for oid, o in self.objectives.items()}
