"""Default decision validator for reasoning outputs."""

from __future__ import annotations

from app.reasoning.base import DecisionValidator
from app.reasoning.models import ReasoningContext, ReasoningDecision, ValidationResult


class DefaultValidator(DecisionValidator):
    """Validates reasoning decisions for correctness and completeness."""

    async def validate(
        self, decision: ReasoningDecision, context: ReasoningContext
    ) -> ValidationResult:
        issues: list[str] = []
        suggestions: list[str] = []

        if not decision.conclusion:
            issues.append("No conclusion provided")
            suggestions.append("Ensure the reasoning chain produces a conclusion")

        if decision.confidence < 0.3:
            issues.append("Very low confidence in the decision")
            suggestions.append("Consider gathering more evidence")

        if decision.chain and not decision.chain.steps:
            issues.append("Reasoning chain has no steps")
            suggestions.append("Use a strategy that generates at least one step")

        if decision.chain and decision.chain.confidence < 0.3:
            issues.append("Low confidence in reasoning chain")
            suggestions.append("Review the reasoning logic for errors")

        if decision.evaluation and decision.evaluation.score < 0.4:
            issues.append(f"Low evaluation score: {decision.evaluation.score}")
            suggestions.append("Try an alternative reasoning strategy")

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            suggestions=suggestions,
        )
