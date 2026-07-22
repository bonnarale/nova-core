"""Domain dataclasses for the Reasoning Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReasoningStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StrategyType(str, Enum):
    DIRECT = "DIRECT"
    ANALYTICAL = "ANALYTICAL"
    COMPARATIVE = "COMPARATIVE"
    MULTI_STEP = "MULTI_STEP"
    SELF_CRITIQUE = "SELF_CRITIQUE"


@dataclass
class ReasoningContext:
    """Input context for a reasoning operation."""

    query: str
    user_id: str | None = None
    session_id: str | None = None
    constraints: list[str] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    context_data: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "constraints": self.constraints,
            "preferences": self.preferences,
            "context_data": self.context_data,
            "extra": self.extra,
        }


@dataclass
class ReasoningStep:
    """A single step in a reasoning chain."""

    description: str
    content: str
    step_type: str = "analysis"
    confidence: float = 0.0
    alternatives: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "content": self.content,
            "step_type": self.step_type,
            "confidence": self.confidence,
            "alternatives": self.alternatives,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }


@dataclass
class ReasoningChain:
    """A full chain of reasoning steps leading to a conclusion."""

    steps: list[ReasoningStep] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.0
    strategy: StrategyType = StrategyType.DIRECT
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: ReasoningStep) -> None:
        self.steps.append(step)

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "strategy": self.strategy.value,
            "metadata": self.metadata,
        }


@dataclass
class EvaluationResult:
    """Score and feedback for a reasoning chain."""

    score: float = 0.0
    completeness: float = 0.0
    coherence: float = 0.0
    relevance: float = 0.0
    feedback: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "completeness": self.completeness,
            "coherence": self.coherence,
            "relevance": self.relevance,
            "feedback": self.feedback,
        }


@dataclass
class ValidationResult:
    """Result of validating a reasoning decision."""

    is_valid: bool = True
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "issues": self.issues,
            "suggestions": self.suggestions,
        }


@dataclass
class CritiqueResult:
    """Result of self-critique on a reasoning chain."""

    flaws: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    overall_assessment: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "flaws": self.flaws,
            "gaps": self.gaps,
            "suggestions": self.suggestions,
            "overall_assessment": self.overall_assessment,
        }


@dataclass
class ReasoningDecision:
    """Final output of the reasoning engine."""

    query: str = ""
    chain: ReasoningChain | None = None
    conclusion: str = ""
    confidence: float = 0.0
    evaluation: EvaluationResult | None = None
    validation: ValidationResult | None = None
    critique: CritiqueResult | None = None
    status: ReasoningStatus = ReasoningStatus.PENDING
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "chain": self.chain.to_dict() if self.chain else None,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "critique": self.critique.to_dict() if self.critique else None,
            "status": self.status.value,
            "error": self.error,
            "metadata": self.metadata,
        }
