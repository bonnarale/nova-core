from __future__ import annotations

import time
from typing import Any

from .approvals import ApprovalsManager
from .backlog import BacklogManager
from .governor import Governor
from .milestones import MilestonesManager
from .objectives import ObjectivesManager
from .projects import ProjectsManager
from .roadmap import RoadmapManager
from .schemas import (
    CommandMetrics,
    CommandRequest,
    CommandResponse,
    LifecycleState,
)


class CommandCenter:
    def __init__(self) -> None:
        self._objectives = ObjectivesManager()
        self._projects = ProjectsManager()
        self._approvals = ApprovalsManager()
        self._governor = Governor(self._objectives, self._projects, self._approvals)
        self._roadmap = RoadmapManager()
        self._backlog = BacklogManager()
        self._milestones = MilestonesManager()
        self._lifecycle = LifecycleState(
            phase="ready",
            started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self._metrics = CommandMetrics()
        self._processing_times: list[float] = []

    @property
    def governor(self) -> Governor:
        return self._governor

    @property
    def objectives(self) -> ObjectivesManager:
        return self._objectives

    @property
    def projects(self) -> ProjectsManager:
        return self._projects

    @property
    def roadmap(self) -> RoadmapManager:
        return self._roadmap

    @property
    def backlog(self) -> BacklogManager:
        return self._backlog

    @property
    def milestones(self) -> MilestonesManager:
        return self._milestones

    @property
    def approvals(self) -> ApprovalsManager:
        return self._approvals

    @property
    def lifecycle(self) -> LifecycleState:
        return self._lifecycle

    @property
    def metrics(self) -> CommandMetrics:
        return self._update_metrics()

    async def process_command(self, request: CommandRequest) -> CommandResponse:
        start = time.monotonic()
        self._metrics.total_commands += 1
        cmd = request.command.lower().strip()
        params = request.parameters
        result: Any = None
        error: str | None = None
        suggestions: list[str] = []
        try:
            if cmd == "analyze":
                text = params.get("text", params.get("objective", ""))
                result = await self._governor.analyze_objective(text)
            elif cmd == "plan":
                analysis = params.get("analysis", {})
                result = await self._governor.create_plan(analysis)
            elif cmd == "create_objective":
                obj = self._objectives.create(
                    title=params.get("title", ""),
                    description=params.get("description", ""),
                    category=params.get("category", "general"),
                    priority=params.get("priority", 3),
                )
                result = obj.__dict__
            elif cmd == "create_project":
                proj = self._projects.create(
                    name=params.get("name", ""),
                    description=params.get("description", ""),
                    objective_id=params.get("objective_id"),
                )
                result = proj.__dict__
            elif cmd == "create_roadmap":
                rm = self._roadmap.create(
                    name=params.get("name", ""),
                    description=params.get("description", ""),
                    duration_years=params.get("duration_years", 1),
                )
                result = rm.__dict__
            elif cmd == "list_objectives":
                status_filter = params.get("status")
                result = [o.__dict__ for o in self._objectives.list_all(status=status_filter)]
            elif cmd == "list_projects":
                status_filter = params.get("status")
                result = [p.__dict__ for p in self._projects.list_all(status=status_filter)]
            elif cmd == "list_backlog":
                status_filter = params.get("status")
                category_filter = params.get("category")
                result = [
                    i.__dict__
                    for i in self._backlog.list_items(
                        status=status_filter, category=category_filter
                    )
                ]
            elif cmd == "approve":
                approval_id = params.get("approval_id", "")
                reviewer = params.get("reviewer", "user")
                reason = params.get("reason")
                result = self._approvals.approve(approval_id, reviewer, reason)
                result = result.__dict__ if result else None
                if result is None:
                    error = f"Approval {approval_id} not found"
            elif cmd == "reject":
                approval_id = params.get("approval_id", "")
                reviewer = params.get("reviewer", "user")
                reason = params.get("reason")
                result = self._approvals.reject(approval_id, reviewer, reason)
                result = result.__dict__ if result else None
                if result is None:
                    error = f"Approval {approval_id} not found"
            elif cmd == "recommend":
                context = params.get("context", {})
                result = await self._governor.recommend_next_action(context)
            elif cmd == "optimize":
                category = params.get("category", "general")
                result = {
                    "category": category,
                    "optimizations": [
                        {"area": "processing", "suggestion": "Batch similar commands"},
                        {"area": "memory", "suggestion": "Cache frequently accessed data"},
                    ],
                }
            elif cmd == "status":
                result = await self.get_status()
            else:
                suggestions = [
                    "analyze",
                    "plan",
                    "create_objective",
                    "create_project",
                    "create_roadmap",
                    "list_objectives",
                    "list_projects",
                    "list_backlog",
                    "approve",
                    "reject",
                    "recommend",
                    "optimize",
                    "status",
                ]
                error = "Command not recognized"
        except Exception as exc:
            error = str(exc)
            self._metrics.failed += 1
        elapsed = (time.monotonic() - start) * 1000
        self._processing_times.append(elapsed)
        if error is None:
            self._metrics.successful += 1
        status = "failed" if error else "completed"
        return CommandResponse(
            command=request.command,
            status=status,
            result=result,
            error=error,
            suggestions=suggestions,
            metadata={"processing_time_ms": elapsed},
        )

    async def get_status(self) -> dict:
        m = self._update_metrics()
        return {
            "lifecycle": self._lifecycle.__dict__,
            "metrics": m.__dict__,
            "objectives": self._objectives.to_dict(),
            "projects": self._projects.to_dict(),
            "roadmap": self._roadmap.to_dict(),
            "backlog": self._backlog.to_dict(),
            "milestones": self._milestones.to_dict(),
            "approvals": self._approvals.to_dict(),
        }

    def _update_metrics(self) -> CommandMetrics:
        self._metrics.active_objectives = len(self._objectives.active)
        self._metrics.active_projects = len(self._projects.projects)
        self._metrics.total_backlog = len(self._backlog.items)
        self._metrics.pending_approval = len(self._approvals.get_pending())
        if self._processing_times:
            self._metrics.avg_processing_time_ms = sum(self._processing_times) / len(
                self._processing_times
            )
        return self._metrics

    def to_dict(self) -> dict:
        return {
            "lifecycle": self._lifecycle.__dict__,
            "metrics": self._update_metrics().__dict__,
        }
