"""Learning models — data structures for the self-improvement loop."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ImprovementGoal:
    """Represents a targeted improvement for an agent or capability."""

    id: str = ""
    target_strategy: str = ""
    proposed_change: str = ""
    confidence: float = 0.7
    evidence: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending | evolving | completed | failed | rolled_back

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
