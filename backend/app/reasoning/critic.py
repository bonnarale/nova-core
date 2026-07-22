"""Default self-critic for reasoning chains."""

from __future__ import annotations

from app.reasoning.base import SelfCritic
from app.reasoning.models import CritiqueResult, ReasoningChain, ReasoningContext


class DefaultCritic(SelfCritic):
    """Performs basic self-critique to identify flaws and gaps in reasoning."""

    async def critique(
        self, chain: ReasoningChain, context: ReasoningContext
    ) -> CritiqueResult:
        flaws: list[str] = []
        gaps: list[str] = []
        suggestions: list[str] = []

        if not chain.steps:
            flaws.append("No reasoning steps generated")
            suggestions.append("Break down the problem into smaller steps")
        else:
            last_type = None
            for i, step in enumerate(chain.steps):
                if step.step_type == last_type:
                    flaws.append(f"Consecutive steps {i} and {i+1} have the same type '{step.step_type}'")
                last_type = step.step_type

                if not step.content:
                    flaws.append(f"Step {i+1} has no content")
                elif len(step.content) < 20:
                    gaps.append(f"Step {i+1} content is too brief")

            if len(chain.steps) < 2:
                gaps.append("Only one reasoning step provided")
                suggestions.append("Consider adding intermediate analysis steps")

        if not chain.conclusion:
            flaws.append("Missing conclusion")
            suggestions.append("Ensure the chain ends with a clear conclusion")

        if chain.confidence < 0.5:
            gaps.append("Overall confidence is low")
            suggestions.append("Gather more evidence to strengthen confidence")

        if not gaps and not flaws:
            overall = "Reasoning chain appears sound with no major issues."
        elif flaws:
            overall = f"Found {len(flaws)} flaw(s) and {len(gaps)} gap(s) in the reasoning chain."
        else:
            overall = f"Minor gaps identified: {len(gaps)} area(s) could be improved."

        return CritiqueResult(
            flaws=flaws,
            gaps=gaps,
            suggestions=suggestions,
            overall_assessment=overall,
        )
