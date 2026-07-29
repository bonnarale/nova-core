from __future__ import annotations

from typing import Any

from .approvals import ApprovalsManager
from .autonomy import AutonomyManager
from .backlog import BacklogManager
from .decisions import DecisionEngine
from .governor import Governor as RichGovernor
from .lifecycle import CommandCenterLifecycle
from .metrics import MetricsCollector
from .milestones import MilestonesManager
from .objectives import ObjectivesManager
from .optimization import OptimizationEngine
from .orchestrator import Orchestrator
from .projects import ProjectsManager
from .recommendations import RecommendationEngine
from .roadmap import RoadmapManager
from .self_improvement import SelfImprovementEngine
from .tracing import TracingManager


class CommandCenterFactory:
    @staticmethod
    def create_all() -> dict[str, Any]:
        objectives_mgr = ObjectivesManager()
        projects_mgr = ProjectsManager()
        roadmap_mgr = RoadmapManager()
        backlog_mgr = BacklogManager()
        milestones_mgr = MilestonesManager()
        approvals_mgr = ApprovalsManager()
        autonomy_mgr = AutonomyManager()
        decisions_engine = DecisionEngine()
        recommendations_engine = RecommendationEngine()
        optimization_engine = OptimizationEngine()
        lifecycle = CommandCenterLifecycle()
        metrics = MetricsCollector()
        tracing = TracingManager()
        self_improvement = SelfImprovementEngine()

        # Use the rich Governor from governor.py (not the minimal one from orchestrator.py)
        governor = RichGovernor(
            objectives_manager=objectives_mgr,
            projects_manager=projects_mgr,
            approvals_manager=approvals_mgr,
        )

        orchestrator = Orchestrator(
            governor=governor,
            objectives_mgr=objectives_mgr,
            projects_mgr=projects_mgr,
            roadmap_mgr=roadmap_mgr,
            backlog_mgr=backlog_mgr,
            approvals_mgr=approvals_mgr,
            decisions_engine=decisions_engine,
        )

        lifecycle.start()

        return {
            "objectives": objectives_mgr,
            "projects": projects_mgr,
            "roadmap": roadmap_mgr,
            "backlog": backlog_mgr,
            "milestones": milestones_mgr,
            "approvals": approvals_mgr,
            "autonomy": autonomy_mgr,
            "decisions": decisions_engine,
            "recommendations": recommendations_engine,
            "optimization": optimization_engine,
            "lifecycle": lifecycle,
            "metrics": metrics,
            "tracing": tracing,
            "self_improvement": self_improvement,
            "governor": governor,
            "orchestrator": orchestrator,
            "command_center": {
                "version": "1.0.0",
                "components": [
                    "objectives",
                    "projects",
                    "roadmap",
                    "backlog",
                    "milestones",
                    "approvals",
                    "autonomy",
                    "decisions",
                    "recommendations",
                    "optimization",
                    "lifecycle",
                    "metrics",
                    "tracing",
                    "self_improvement",
                    "governor",
                    "orchestrator",
                ],
            },
        }
