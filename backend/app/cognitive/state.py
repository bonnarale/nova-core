"""CognitiveState — runtime state for the Cognitive Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.cognitive.context import CognitiveContext
from app.cognitive.decision import CognitiveDecision


@dataclass
class CognitiveState:
    """Mutable runtime state for a single cognitive cycle."""

    context: CognitiveContext = field(default_factory=CognitiveContext)
    decision: CognitiveDecision | None = None
    execution_result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "context": self.context.to_dict(),
            "decision": self.decision.to_dict() if self.decision else None,
            "execution_result": self.execution_result,
            "error": self.error,
        }
