from __future__ import annotations

__version__ = "1.1.0"

from .history import HistoryManager
from .objectives import ObjectivesManager
from .preferences import PreferencesManager
from .priorities import PrioritiesManager
from .profile import ProfileManager
from .projects import ProjectsManager
from .roadmap import RoadmapManager
from .schemas import (
    HistoryEntry,
    Objective,
    PriorityEntry,
    Project,
    Roadmap,
    RoadmapPhase,
    UserPreference,
    UserProfile,
)

__all__ = [
    "HistoryEntry",
    "HistoryManager",
    "Objective",
    "ObjectivesManager",
    "PreferencesManager",
    "PriorityEntry",
    "PrioritiesManager",
    "ProfileManager",
    "Project",
    "ProjectsManager",
    "Roadmap",
    "RoadmapManager",
    "RoadmapPhase",
    "UserPreference",
    "UserProfile",
]
