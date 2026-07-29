"""Autonomous planner — generates execution plans from objectives."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any


class PlanStep:
    """A single step in an autonomous plan."""

    __slots__ = ("id", "action", "target", "parameters", "order", "dependencies", "estimated_duration_ms")

    def __init__(
        self,
        action: str,
        target: str = "",
        parameters: dict[str, Any] | None = None,
        order: int = 0,
        dependencies: list[str] | None = None,
        estimated_duration_ms: float = 100.0,
    ) -> None:
        self.id = str(uuid.uuid4())[:8]
        self.action = action
        self.target = target
        self.parameters = parameters or {}
        self.order = order
        self.dependencies = dependencies or []
        self.estimated_duration_ms = estimated_duration_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "target": self.target,
            "parameters": self.parameters,
            "order": self.order,
            "dependencies": self.dependencies,
            "estimated_duration_ms": self.estimated_duration_ms,
        }


class Plan:
    """An autonomous execution plan."""

    __slots__ = ("id", "objective_id", "steps", "created_at", "status", "metadata")

    def __init__(self, objective_id: str, metadata: dict[str, Any] | None = None) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.objective_id = objective_id
        self.steps: list[PlanStep] = []
        self.created_at = time.time()
        self.status = "proposed"
        self.metadata = metadata or {}

    def add_step(self, step: PlanStep) -> None:
        self.steps.append(step)
        self.steps.sort(key=lambda s: s.order)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "objective_id": self.objective_id,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "status": self.status,
            "estimated_total_ms": sum(s.estimated_duration_ms for s in self.steps),
            "metadata": self.metadata,
        }


class AutonomousPlanner:
    """Generates and manages autonomous execution plans."""

    def __init__(self) -> None:
        self._plans: dict[str, Plan] = {}
        self._lock = threading.RLock()

    async def propose_plan(self, objective_id: str, context: dict[str, Any] | None = None) -> Plan:
        plan = Plan(objective_id, context)
        analysis_step = PlanStep(action="analyze", target="objective", order=0, estimated_duration_ms=50)
        plan.add_step(analysis_step)
        plan.add_step(PlanStep(action="gather_context", target="memory", order=1, estimated_duration_ms=100))
        plan.add_step(PlanStep(action="execute", target="engine", order=2, estimated_duration_ms=500))
        plan.add_step(PlanStep(action="evaluate", target="results", order=3, estimated_duration_ms=50))
        plan.add_step(PlanStep(action="report", target="observer", order=4, estimated_duration_ms=25))
        with self._lock:
            self._plans[plan.id] = plan
        return plan

    def get_plan(self, plan_id: str) -> Plan | None:
        with self._lock:
            return self._plans.get(plan_id)

    def get_plans_for_objective(self, objective_id: str) -> list[Plan]:
        with self._lock:
            return [p for p in self._plans.values() if p.objective_id == objective_id]

    def approve_plan(self, plan_id: str) -> bool:
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan and plan.status == "proposed":
                plan.status = "approved"
                return True
            return False

    def complete_plan(self, plan_id: str) -> bool:
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan:
                plan.status = "completed"
                return True
            return False

    def cancel_plan(self, plan_id: str) -> bool:
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan and plan.status != "completed":
                plan.status = "cancelled"
                return True
            return False

    def get_all_plans(self) -> list[Plan]:
        with self._lock:
            return list(self._plans.values())

    def count(self) -> int:
        with self._lock:
            return len(self._plans)
