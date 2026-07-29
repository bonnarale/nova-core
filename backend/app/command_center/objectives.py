from __future__ import annotations

from .schemas import Objective


class ObjectivesManager:
    def __init__(self, max_active: int = 3) -> None:
        self.max_active: int = max_active
        self.active: dict[str, Objective] = {}
        self.backlog: list[Objective] = []

    def create(
        self,
        title: str,
        description: str = "",
        category: str = "general",
        priority: int = 3,
    ) -> Objective:
        obj = Objective(
            title=title,
            description=description,
            category=category,
            priority=priority,
        )
        if len(self.active) >= self.max_active:
            obj.status = "backlog"
            self.backlog.append(obj)
        else:
            self.active[obj.id] = obj
        return obj

    def update(self, objective_id: str, **kwargs: object) -> Objective | None:
        obj = self.active.get(objective_id) or next(
            (o for o in self.backlog if o.id == objective_id), None
        )
        if obj is None:
            return None
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        return obj

    def complete(self, objective_id: str) -> Objective | None:
        obj = self.active.pop(objective_id, None)
        if obj is None:
            return None
        obj.status = "completed"
        obj.progress = 1.0
        self._promote_next()
        return obj

    def cancel(self, objective_id: str) -> Objective | None:
        obj = self.active.pop(objective_id, None)
        if obj is None:
            obj = next((o for o in self.backlog if o.id == objective_id), None)
            if obj is None:
                return None
            self.backlog = [o for o in self.backlog if o.id != objective_id]
        obj.status = "cancelled"
        self._promote_next()
        return obj

    def get(self, objective_id: str) -> Objective | None:
        return self.active.get(objective_id) or next(
            (o for o in self.backlog if o.id == objective_id), None
        )

    def list_active(self) -> list[Objective]:
        return list(self.active.values())

    def list_backlog(self) -> list[Objective]:
        return list(self.backlog)

    def list_all(self, status: str | None = None) -> list[Objective]:
        all_objs: list[Objective] = list(self.active.values()) + list(self.backlog)
        if status:
            all_objs = [o for o in all_objs if o.status == status]
        return all_objs

    def promote_from_backlog(self, objective_id: str) -> Objective | None:
        idx = next(
            (i for i, o in enumerate(self.backlog) if o.id == objective_id), None
        )
        if idx is None:
            return None
        if len(self.active) >= self.max_active:
            return None
        obj = self.backlog.pop(idx)
        obj.status = "active"
        self.active[obj.id] = obj
        return obj

    def update_progress(self, objective_id: str, progress: float) -> Objective | None:
        obj = self.active.get(objective_id)
        if obj is None:
            return None
        obj.progress = max(0.0, min(1.0, progress))
        return obj

    def add_milestone(self, objective_id: str, milestone: dict) -> bool:
        obj = self.active.get(objective_id)
        if obj is None:
            return False
        obj.milestones.append(milestone)
        return True

    def add_goal(self, objective_id: str, goal: dict) -> bool:
        obj = self.active.get(objective_id)
        if obj is None:
            return False
        obj.goals.append(goal)
        return True

    def add_task(self, objective_id: str, task: dict) -> bool:
        obj = self.active.get(objective_id)
        if obj is None:
            return False
        obj.tasks.append(task)
        return True

    def _promote_next(self) -> None:
        if len(self.active) >= self.max_active:
            return
        if not self.backlog:
            return
        obj = self.backlog.pop(0)
        obj.status = "active"
        self.active[obj.id] = obj

    def to_dict(self) -> dict:
        return {
            "max_active": self.max_active,
            "active": {k: v.__dict__ for k, v in self.active.items()},
            "backlog": [o.__dict__ for o in self.backlog],
        }
