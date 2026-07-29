from __future__ import annotations

from .schemas import PriorityEntry


class PrioritiesManager:
    def __init__(self) -> None:
        self.priorities: dict[str, PriorityEntry] = {}

    def create_priority(self, name: str, level: int, description: str = "") -> dict:
        priority = PriorityEntry(name=name, level=level, description=description)
        self.priorities[priority.id] = priority
        return priority.to_dict()

    def update_priority(self, priority_id: str, **kwargs) -> dict | None:
        priority = self.priorities.get(priority_id)
        if not priority:
            return None
        for key, value in kwargs.items():
            if hasattr(priority, key) and key not in ("id", "created_at"):
                setattr(priority, key, value)
        return priority.to_dict()

    def delete_priority(self, priority_id: str) -> bool:
        if priority_id in self.priorities:
            del self.priorities[priority_id]
            return True
        return False

    def get_priority(self, priority_id: str) -> dict | None:
        priority = self.priorities.get(priority_id)
        return priority.to_dict() if priority else None

    def list_priorities(self) -> list[dict]:
        sorted_p = sorted(self.priorities.values(), key=lambda p: p.level, reverse=True)
        return [p.to_dict() for p in sorted_p]

    def get_top(self, n: int = 3) -> list[dict]:
        sorted_p = sorted(self.priorities.values(), key=lambda p: p.level, reverse=True)
        return [p.to_dict() for p in sorted_p[:n]]

    def to_dict(self) -> dict:
        return {pid: p.to_dict() for pid, p in self.priorities.items()}
