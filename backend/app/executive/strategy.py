"""Planning strategy abstraction for the Executive Planner."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SuggestedTask:
    """A task suggested by a planning strategy."""

    goal_id: str
    goal_title: str
    title: str
    description: str = ""
    priority: int = 3
    suggested_agent: str | None = None
    dependencies: list[str] = field(default_factory=list)


@dataclass
class PlanningOutput:
    """Output from a planning strategy analysis."""

    reviewed_goal_ids: list[str] = field(default_factory=list)
    suggested_tasks: list[SuggestedTask] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)


class PlanningStrategy(ABC):
    """Abstract strategy for goal analysis and task generation.

    Implementations can be rule-based, LLM-based, or hybrid.
    """

    @abstractmethod
    async def analyze(
        self,
        goals: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
        profile: dict[str, Any] | None,
        recent_messages: list[dict[str, str]],
    ) -> PlanningOutput:
        """Analyze goals and existing state, returning suggested tasks."""
        ...


class RuleBasedStrategy(PlanningStrategy):
    """Rule-based planning strategy.

    Uses heuristics to suggest tasks from active goals:
    - Skip goals that already have pending/completed tasks.
    - Prioritize by goal priority and progress.
    - Suggest agents based on keyword matching.
    """

    _AGENT_KEYWORDS: dict[str, list[str]] = {
        "planner": ["plan", "organize", "design", "architecture", "strategy"],
        "researcher": ["research", "investigate", "find", "search", "analyze", "learn"],
        "coder": ["implement", "code", "write", "develop", "build", "program", "create"],
        "reviewer": ["review", "check", "validate", "audit", "inspect", "test"],
        "memory": ["remember", "store", "recall", "memorize", "save"],
        "executor": ["deploy", "execute", "run", "perform", "action", "apply"],
    }

    async def analyze(
        self,
        goals: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
        profile: dict[str, Any] | None,
        recent_messages: list[dict[str, str]],
    ) -> PlanningOutput:
        reviewed: list[str] = []
        suggestions: list[SuggestedTask] = []
        observations: list[str] = []

        goal_tasks_map = self._build_goal_tasks_map(tasks)

        for goal in goals:
            gid = goal.get("id", "")
            status = goal.get("status", "")
            priority = goal.get("priority", 3)
            progress = goal.get("progress", 0)
            title = goal.get("title", "")
            description = goal.get("description", "")

            reviewed.append(gid)

            if status in ("completed", "abandoned"):
                continue

            pending = goal_tasks_map.get(gid, [])
            has_active_task = any(
                t.get("status") in ("QUEUED", "RUNNING", "WAITING", "CREATED")
                for t in pending
            )
            has_completed_task = any(
                t.get("status") == "COMPLETED" for t in pending
            )

            if has_active_task:
                observations.append(
                    f"Goal '{title[:40]}' already has an active task in progress."
                )
                continue

            if has_completed_task and progress >= 100:
                continue

            if has_completed_task and progress < 100:
                observations.append(
                    f"Goal '{title[:40]}' has a completed task but progress is {progress}%."
                )

            task_title = self._generate_task_title(title, description)
            task_desc = description or f"Work on: {title}"
            suggested_agent = self._suggest_agent(title, description)

            suggestions.append(
                SuggestedTask(
                    goal_id=gid,
                    goal_title=title,
                    title=task_title,
                    description=task_desc,
                    priority=priority,
                    suggested_agent=suggested_agent,
                )
            )

        return PlanningOutput(
            reviewed_goal_ids=reviewed,
            suggested_tasks=suggestions,
            observations=observations,
        )

    def _build_goal_tasks_map(
        self, tasks: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        mapping: dict[str, list[dict[str, Any]]] = {}
        for t in tasks:
            gid = t.get("goal_id", "")
            if gid:
                mapping.setdefault(gid, []).append(t)
        return mapping

    def _generate_task_title(self, goal_title: str, description: str) -> str:
        text = description or goal_title
        words = text.split()[:8]
        base = " ".join(words)
        if len(base) > 60:
            base = base[:60]
        return f"Execute: {base}"

    def _suggest_agent(self, title: str, description: str) -> str:
        text = (title + " " + (description or "")).lower()
        best_agent = "executor"
        best_score = 0
        for agent, keywords in self._AGENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_agent = agent
        return best_agent
