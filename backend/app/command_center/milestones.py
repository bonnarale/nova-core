from __future__ import annotations

from .schemas import Milestone


class MilestonesManager:
    def __init__(self) -> None:
        self.milestones: dict[str, Milestone] = {}

    def create(
        self,
        title: str,
        description: str = "",
        objective_id: str | None = None,
        project_id: str | None = None,
        due_date: str | None = None,
    ) -> Milestone:
        milestone = Milestone(
            title=title,
            description=description,
            objective_id=objective_id,
            project_id=project_id,
            due_date=due_date,
        )
        self.milestones[milestone.id] = milestone
        return milestone

    def update(self, milestone_id: str, **kwargs: object) -> Milestone | None:
        milestone = self.milestones.get(milestone_id)
        if milestone is None:
            return None
        for key, value in kwargs.items():
            if hasattr(milestone, key):
                setattr(milestone, key, value)
        return milestone

    def complete(self, milestone_id: str) -> Milestone | None:
        milestone = self.milestones.get(milestone_id)
        if milestone is None:
            return None
        milestone.status = "completed"
        return milestone

    def get(self, milestone_id: str) -> Milestone | None:
        return self.milestones.get(milestone_id)

    def list_all(
        self,
        status: str | None = None,
        objective_id: str | None = None,
        project_id: str | None = None,
    ) -> list[Milestone]:
        milestones = list(self.milestones.values())
        if status:
            milestones = [m for m in milestones if m.status == status]
        if objective_id:
            milestones = [m for m in milestones if m.objective_id == objective_id]
        if project_id:
            milestones = [m for m in milestones if m.project_id == project_id]
        return milestones

    def to_dict(self) -> dict:
        return {k: v.__dict__ for k, v in self.milestones.items()}
