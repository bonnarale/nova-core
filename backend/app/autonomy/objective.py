"""Objective management — prioritization, dependency analysis, progress, completion scoring."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.autonomy.enums import ObjectivePriority, ObjectiveStatus


class Objective:
    """Represents an autonomous objective."""

    __slots__ = (
        "id", "name", "description", "priority", "status",
        "dependencies", "progress", "metadata", "created_at",
        "updated_at", "completed_at", "score",
    )

    def __init__(
        self,
        name: str,
        description: str = "",
        priority: ObjectivePriority = ObjectivePriority.MEDIUM,
        dependencies: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.name = name
        self.description = description
        self.priority = priority
        self.status = ObjectiveStatus.PENDING
        self.dependencies = dependencies or []
        self.progress = 0.0
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.updated_at = time.time()
        self.completed_at: float | None = None
        self.score = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "progress": self.progress,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "score": self.score,
        }


_PRIORITY_ORDER = {
    ObjectivePriority.CRITICAL: 0,
    ObjectivePriority.HIGH: 1,
    ObjectivePriority.MEDIUM: 2,
    ObjectivePriority.LOW: 3,
    ObjectivePriority.BACKGROUND: 4,
}


class ObjectiveManager:
    """Manages autonomous objectives with prioritization and dependency tracking."""

    def __init__(self) -> None:
        self._objectives: dict[str, Objective] = {}
        self._lock = threading.RLock()

    def create(
        self,
        name: str,
        description: str = "",
        priority: str = "medium",
        dependencies: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Objective:
        obj = Objective(
            name=name,
            description=description,
            priority=ObjectivePriority(priority),
            dependencies=dependencies,
            metadata=metadata,
        )
        with self._lock:
            self._objectives[obj.id] = obj
        return obj

    def get(self, objective_id: str) -> Objective | None:
        with self._lock:
            return self._objectives.get(objective_id)

    def get_all(self) -> list[Objective]:
        with self._lock:
            return list(self._objectives.values())

    def update_status(self, objective_id: str, status: str) -> bool:
        with self._lock:
            obj = self._objectives.get(objective_id)
            if not obj:
                return False
            obj.status = ObjectiveStatus(status)
            obj.updated_at = time.time()
            if obj.status == ObjectiveStatus.COMPLETED:
                obj.progress = 1.0
                obj.completed_at = time.time()
            return True

    def update_progress(self, objective_id: str, progress: float) -> bool:
        with self._lock:
            obj = self._objectives.get(objective_id)
            if not obj:
                return False
            obj.progress = max(0.0, min(1.0, progress))
            obj.updated_at = time.time()
            return True

    def prioritize(self) -> list[Objective]:
        with self._lock:
            objs = list(self._objectives.values())
        objs.sort(key=lambda o: (_PRIORITY_ORDER.get(o.priority, 99), -o.created_at))
        return objs

    def get_ready_objectives(self) -> list[Objective]:
        """Get objectives whose dependencies are all completed."""
        with self._lock:
            ready = []
            for obj in self._objectives.values():
                if obj.status not in (ObjectiveStatus.PENDING, ObjectiveStatus.ACTIVE):
                    continue
                deps_met = all(
                    self._objectives.get(d) is not None
                    and self._objectives[d].status == ObjectiveStatus.COMPLETED
                    for d in obj.dependencies
                )
                if deps_met:
                    ready.append(obj)
        return ready

    def analyze_dependencies(self, objective_id: str) -> dict[str, Any]:
        with self._lock:
            obj = self._objectives.get(objective_id)
            if not obj:
                return {"found": False}
            deps = []
            for d in obj.dependencies:
                dep = self._objectives.get(d)
                if dep:
                    deps.append({"id": d, "name": dep.name, "status": dep.status.value})
            blocked = [d for d in deps if d["status"] != "completed"]
            return {
                "found": True,
                "total": len(deps),
                "completed": len(deps) - len(blocked),
                "blocked": blocked,
                "all_met": len(blocked) == 0,
            }

    def score_completion(self, objective_id: str) -> float:
        with self._lock:
            obj = self._objectives.get(objective_id)
            if not obj:
                return 0.0
            base = obj.progress
            priority_bonus = (4 - _PRIORITY_ORDER.get(obj.priority, 4)) * 0.05
            dep_completion = 0.0
            if obj.dependencies:
                completed_deps = sum(
                    1 for d in obj.dependencies
                    if self._objectives.get(d)
                    and self._objectives[d].status == ObjectiveStatus.COMPLETED
                )
                dep_completion = completed_deps / len(obj.dependencies) * 0.2
            score = min(1.0, base + priority_bonus + dep_completion)
            obj.score = score
            return score

    def remove(self, objective_id: str) -> bool:
        with self._lock:
            if objective_id in self._objectives:
                del self._objectives[objective_id]
                return True
            return False

    def count(self) -> int:
        with self._lock:
            return len(self._objectives)
