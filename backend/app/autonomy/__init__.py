from __future__ import annotations

from .approval_engine import ApprovalEngine
from .autonomy_engine import AutonomyEngine
from .delegation_engine import DelegationEngine
from .objective_manager import ObjectiveManager
from .optimization_engine import OptimizationEngine
from .project_manager import ProjectManager
from .recommendation_engine import RecommendationEngine
from .research_manager import ResearchManager
from .roadmap_manager import RoadmapManager
from .schemas import (
    DelegationTask,
    ObjectivePlan,
    OptimizationResult,
    ProjectOrchestration,
    Recommendation,
    ResearchQuery,
    SelfImprovementItem,
)
from .self_improvement import SelfImprovementEngine

__version__ = "1.1.0"

__all__ = [
    "ApprovalEngine",
    "AutonomyEngine",
    "DelegationEngine",
    "DelegationTask",
    "ObjectiveManager",
    "ObjectivePlan",
    "OptimizationEngine",
    "OptimizationResult",
    "ProjectManager",
    "ProjectOrchestration",
    "Recommendation",
    "RecommendationEngine",
    "ResearchManager",
    "ResearchQuery",
    "RoadmapManager",
    "SelfImprovementEngine",
    "SelfImprovementItem",
]
