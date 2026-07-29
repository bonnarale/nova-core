from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .schemas import ObjectivePlan


class ObjectiveManager:
    def __init__(self, max_active: int = 3) -> None:
        self._max_active = max_active
        self._objectives: dict[str, dict] = {}
        self._backlog: list[dict] = []

    def analyze_objective(self, objective_text: str) -> dict:
        text_lower = objective_text.lower()
        category = "general"
        if any(k in text_lower for k in ("optimize", "performance", "speed")):
            category = "optimization"
        elif any(k in text_lower for k in ("security", "auth", "protect")):
            category = "security"
        elif any(k in text_lower for k in ("refactor", "clean", "restructure")):
            category = "refactoring"
        elif any(k in text_lower for k in ("feature", "add", "implement", "create")):
            category = "feature"
        elif any(k in text_lower for k in ("fix", "bug", "patch", "error")):
            category = "bugfix"

        word_count = len(objective_text.split())
        if word_count > 30:
            complexity = "high"
            estimated_duration = "2-4 weeks"
        elif word_count > 15:
            complexity = "medium"
            estimated_duration = "1-2 weeks"
        else:
            complexity = "low"
            estimated_duration = "1-3 days"

        return {
            "category": category,
            "complexity": complexity,
            "estimated_duration": estimated_duration,
            "risks": [
                "Scope creep",
                "Integration issues",
                "Performance regression",
            ],
            "opportunities": [
                "Improved maintainability",
                "Better test coverage",
                "Enhanced functionality",
            ],
        }

    def create_plan(self, objective_text: str, analysis: dict) -> ObjectivePlan:
        milestones, goals, tasks = self._decompose_objective(objective_text, analysis)
        workflows = self._determine_workflows(analysis)
        tools = self._determine_tools(analysis)
        agents = self._determine_agents(analysis)
        risks = self._assess_risks(analysis)

        return ObjectivePlan(
            title=objective_text,
            description=f"Plan for: {objective_text}",
            analysis=analysis,
            milestones=milestones,
            goals=goals,
            tasks=tasks,
            workflows=workflows,
            tools_needed=tools,
            agents_needed=agents,
            risk_assessment=risks,
            estimated_duration=analysis.get("estimated_duration", "unknown"),
            requires_human_approval=analysis.get("complexity", "low") != "low",
            requires_open_code=analysis.get("category") in ("feature", "refactoring"),
        )

    def add_objective(
        self, title: str, description: str, priority: int = 3
    ) -> dict:
        objective = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": description,
            "priority": priority,
            "status": "backlog",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        active = [o for o in self._objectives.values() if o["status"] == "active"]
        if len(active) < self._max_active:
            objective["status"] = "active"
            self._objectives[objective["id"]] = objective
        else:
            self._backlog.append(objective)
        return objective

    def update_objective(self, objective_id: str, **kwargs: object) -> dict | None:
        obj = self._objectives.get(objective_id)
        if obj is None:
            for item in self._backlog:
                if item["id"] == objective_id:
                    item.update(kwargs)
                    return item
            return None
        obj.update(kwargs)
        return obj

    def complete_objective(self, objective_id: str) -> dict | None:
        obj = self._objectives.pop(objective_id, None)
        if obj is None:
            return None
        obj["status"] = "completed"
        obj["completed_at"] = datetime.now(timezone.utc).isoformat()
        self._objectives[objective_id] = obj
        self._promote_next()
        return obj

    def list_active(self) -> list[dict]:
        return [o for o in self._objectives.values() if o["status"] == "active"]

    def list_backlog(self) -> list[dict]:
        return list(self._backlog)

    def promote_from_backlog(self, objective_id: str) -> dict | None:
        for i, item in enumerate(self._backlog):
            if item["id"] == objective_id:
                active = self.list_active()
                if len(active) >= self._max_active:
                    return None
                self._backlog.pop(i)
                item["status"] = "active"
                self._objectives[item["id"]] = item
                return item
        return None

    def _decompose_objective(
        self, title: str, analysis: dict
    ) -> tuple[list[dict], list[dict], list[dict]]:
        complexity = analysis.get("complexity", "low")
        num_tasks = {"low": 3, "medium": 5, "high": 8}.get(complexity, 3)

        milestones = [
            {
                "id": str(uuid.uuid4()),
                "title": f"Milestone {i+1}: {phase}",
                "status": "pending",
            }
            for i, phase in enumerate(["Analysis", "Implementation", "Validation"])
        ]

        goals = [
            {
                "id": str(uuid.uuid4()),
                "title": f"Goal {i+1}",
                "description": f"Complete phase: {phase}",
                "status": "pending",
            }
            for i, phase in enumerate(["Plan", "Execute", "Verify", "Deliver"])
        ]

        tasks = [
            {
                "id": str(uuid.uuid4()),
                "title": f"Task {i+1}: {task_desc}",
                "status": "pending",
                "priority": 3,
            }
            for i, task_desc in enumerate(
                [f"Step {j+1} of {title}" for j in range(num_tasks)]
            )
        ]

        return milestones, goals, tasks

    def _determine_workflows(self, analysis: dict) -> list[dict]:
        cat = analysis.get("category", "general")
        workflows = [
            {"name": "default_analysis", "trigger": "objective_created"},
            {"name": f"{cat}_pipeline", "trigger": "objective_approved"},
        ]
        if analysis.get("complexity") == "high":
            workflows.append({"name": "review_cycle", "trigger": "task_completed"})
        return workflows

    def _determine_tools(self, analysis: dict) -> list[str]:
        tools = ["code_search"]
        cat = analysis.get("category", "general")
        if cat in ("feature", "refactoring"):
            tools.append("code_generation")
        if cat == "optimization":
            tools.append("profiling")
        if cat == "security":
            tools.append("security_scan")
        return tools

    def _determine_agents(self, analysis: dict) -> list[str]:
        agents = ["coordinator"]
        if analysis.get("complexity") in ("medium", "high"):
            agents.append("reviewer")
        cat = analysis.get("category", "general")
        if cat in ("feature", "refactoring"):
            agents.append("coder")
        return agents

    def _assess_risks(self, analysis: dict) -> dict:
        complexity = analysis.get("complexity", "low")
        return {
            "overall": complexity,
            "mitigation_strategies": [
                "Incremental implementation",
                "Regular testing",
                "Code review checkpoints",
            ],
            "blocking_risks": [],
            "monitoring_required": complexity == "high",
        }

    def _promote_next(self) -> None:
        active = self.list_active()
        while len(active) < self._max_active and self._backlog:
            next_obj = self._backlog.pop(0)
            next_obj["status"] = "active"
            self._objectives[next_obj["id"]] = next_obj
            active = self.list_active()

    def to_dict(self) -> dict:
        return {
            "max_active": self._max_active,
            "objectives": dict(self._objectives),
            "backlog": list(self._backlog),
        }
