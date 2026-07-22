"""Abstract base classes for the Reasoning Engine."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.reasoning.models import (
    CritiqueResult,
    EvaluationResult,
    ReasoningChain,
    ReasoningContext,
    ReasoningDecision,
    ValidationResult,
)


class ReasoningStrategy(ABC):
    """Abstract strategy that generates a reasoning chain from context."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def can_handle(self, context: ReasoningContext) -> bool:
        ...

    @abstractmethod
    async def reason(self, context: ReasoningContext) -> ReasoningChain:
        ...


class CandidateEvaluator(ABC):
    """Evaluates the quality of a reasoning chain."""

    @abstractmethod
    async def evaluate(
        self, chain: ReasoningChain, context: ReasoningContext
    ) -> EvaluationResult:
        ...


class DecisionValidator(ABC):
    """Validates a reasoning decision for correctness and completeness."""

    @abstractmethod
    async def validate(
        self, decision: ReasoningDecision, context: ReasoningContext
    ) -> ValidationResult:
        ...


class SelfCritic(ABC):
    """Performs self-critique on a reasoning chain to find flaws and gaps."""

    @abstractmethod
    async def critique(
        self, chain: ReasoningChain, context: ReasoningContext
    ) -> CritiqueResult:
        ...
