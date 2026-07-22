"""Learning models — data structures for the self-improvement loop."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionOutcome:
    """Record of a single task execution outcome."""

    id: str = ""
    execution_id: str = ""
    task_id: str = ""
    strategy_used: str = ""
    outcome: str = ""  # success | failure
    duration_ms: int = 0
    error_count: int = 0
    user_satisfaction: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "strategy_used": self.strategy_used,
            "outcome": self.outcome,
            "duration_ms": self.duration_ms,
            "error_count": self.error_count,
            "user_satisfaction": self.user_satisfaction,
            "metadata": self.metadata,
        }


@dataclass
class ImprovementGoal:
    """Represents a targeted improvement for an agent or capability."""

    id: str = ""
    target_strategy: str = ""
    proposed_change: str = ""
    confidence: float = 0.7
    evidence: dict[str, Any] = field(default_factory=dict)
    status: str = "pending_approval"  # pending_approval | evolving | completed | failed | rolled_back

    @staticmethod
    def new_id() -> str:
        """Generate a new unique ID."""
        return str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "target_strategy": self.target_strategy,
            "proposed_change": self.proposed_change,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "status": self.status,
        }
