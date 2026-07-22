"""CognitiveContext — unified data bag for the Cognitive Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentType(str, Enum):
    CHAT = "CHAT"
    QUESTION = "QUESTION"
    GOAL = "GOAL"
    TASK = "TASK"
    SEARCH = "SEARCH"
    RESEARCH = "RESEARCH"
    CODE = "CODE"
    MEMORY = "MEMORY"
    PROFILE_UPDATE = "PROFILE_UPDATE"
    SYSTEM = "SYSTEM"
    PLAN = "PLAN"
    REASON = "REASON"
    WORKFLOW = "WORKFLOW"
    KNOWLEDGE_GRAPH = "KNOWLEDGE_GRAPH"
    SDD_TASK = "SDD_TASK"
    META_IMPROVEMENT = "META_IMPROVEMENT"


@dataclass
class CognitiveContext:
    """All data loaded for a single cognitive cycle."""

    raw_input: str = ""
    user_id: str | None = None
    session_id: str | None = None
    intent: IntentType = IntentType.CHAT
    confidence: float = 0.0

    conversation_history: list[dict[str, str]] = field(default_factory=list)
    user_profile: dict[str, Any] | None = None
    goals: list[dict[str, Any]] = field(default_factory=list)
    pending_tasks: list[dict[str, Any]] = field(default_factory=list)
    running_tasks: list[dict[str, Any]] = field(default_factory=list)
    agent_registry: list[str] = field(default_factory=list)

    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_input": self.raw_input,
            "user_id": self.user_id,
            "session_id": str(self.session_id) if self.session_id else None,
            "intent": self.intent.value,
            "confidence": self.confidence,
            "conversation_history_count": len(self.conversation_history),
            "user_profile_present": self.user_profile is not None,
            "goals_count": len(self.goals),
            "pending_tasks_count": len(self.pending_tasks),
            "running_tasks_count": len(self.running_tasks),
            "agent_registry": self.agent_registry,
        }
