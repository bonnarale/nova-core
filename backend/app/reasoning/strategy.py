"""Concrete reasoning strategies."""

from __future__ import annotations

import re
from typing import Any

from app.reasoning.base import ReasoningStrategy
from app.reasoning.models import ReasoningChain, ReasoningContext, ReasoningStep, StrategyType


class DirectReasoningStrategy(ReasoningStrategy):
    """Direct single-step reasoning for straightforward queries."""

    @property
    def name(self) -> str:
        return StrategyType.DIRECT.value

    async def can_handle(self, context: ReasoningContext) -> bool:
        text = context.query.lower().strip()
        short = len(text.split()) < 15
        no_comparison = not any(
            w in text for w in ("compare", "versus", "vs", "alternative", "difference")
        )
        no_multipart = text.count("?") <= 1
        return short and no_comparison and no_multipart

    async def reason(self, context: ReasoningContext) -> ReasoningChain:
        chain = ReasoningChain(strategy=StrategyType.DIRECT)
        step = ReasoningStep(
            description="Direct analysis",
            content=f"Analyzing: {context.query}",
            step_type="direct",
            confidence=0.85,
        )
        chain.add_step(step)
        chain.conclusion = context.query
        chain.confidence = 0.85
        return chain


class AnalyticalReasoningStrategy(ReasoningStrategy):
    """Step-by-step analytical reasoning for complex problems."""

    @property
    def name(self) -> str:
        return StrategyType.ANALYTICAL.value

    async def can_handle(self, context: ReasoningContext) -> bool:
        text = context.query.lower()
        keywords = ("why", "how", "analyze", "explain", "what causes", "what is the reason")
        return any(k in text for k in keywords)

    async def reason(self, context: ReasoningContext) -> ReasoningChain:
        chain = ReasoningChain(strategy=StrategyType.ANALYTICAL)
        query = context.query

        chain.add_step(
            ReasoningStep(
                description="Problem definition",
                content=f"Defining the problem: {query}",
                step_type="definition",
                confidence=0.9,
            )
        )

        factors = self._extract_factors(query)
        chain.add_step(
            ReasoningStep(
                description="Factor analysis",
                content=f"Identifying contributing factors: {', '.join(factors) if factors else 'Analyzing the core elements of the problem'}",
                step_type="analysis",
                confidence=0.8,
                evidence=factors,
            )
        )

        chain.add_step(
            ReasoningStep(
                description="Synthesis",
                content=f"Synthesizing findings from analysis",
                step_type="synthesis",
                confidence=0.75,
            )
        )

        chain.conclusion = f"Analysis complete for: {query}"
        chain.confidence = 0.8
        return chain

    @staticmethod
    def _extract_factors(text: str) -> list[str]:
        words = text.lower().split()
        factors = [w for w in words if len(w) > 5 and w not in ("because", "without", "through", "between")]
        return factors[:5]


class ComparativeReasoningStrategy(ReasoningStrategy):
    """Compares alternatives for decision-oriented queries."""

    @property
    def name(self) -> str:
        return StrategyType.COMPARATIVE.value

    async def can_handle(self, context: ReasoningContext) -> bool:
        text = context.query.lower()
        keywords = ("compare", "versus", "vs ", "better", "worse", "alternative", "difference between", "trade-off", "pros and cons")
        return any(k in text for k in keywords)

    async def reason(self, context: ReasoningContext) -> ReasoningChain:
        chain = ReasoningChain(strategy=StrategyType.COMPARATIVE)
        query = context.query
        alternatives = self._extract_alternatives(query)

        chain.add_step(
            ReasoningStep(
                description="Alternative identification",
                content=f"Identified alternatives: {', '.join(alternatives) if alternatives else 'Analyzing options in: {query}'}",
                step_type="identification",
                confidence=0.85,
                alternatives=alternatives,
            )
        )

        criteria = ["effectiveness", "efficiency", "cost", "complexity"]
        chain.add_step(
            ReasoningStep(
                description="Criteria evaluation",
                content=f"Evaluating each alternative against: {', '.join(criteria)}",
                step_type="evaluation",
                confidence=0.8,
                evidence=criteria,
            )
        )

        chain.add_step(
            ReasoningStep(
                description="Recommendation",
                content=f"Weighing trade-offs and recommending the best option",
                step_type="recommendation",
                confidence=0.7,
            )
        )

        chain.conclusion = f"Comparative analysis complete. Recommendation based on trade-off evaluation."
        chain.confidence = 0.75
        return chain

    @staticmethod
    def _extract_alternatives(text: str) -> list[str]:
        parts = re.split(r"\b(vs|versus|or|and)\b", text, flags=re.IGNORECASE)
        alternatives = []
        for p in parts:
            p = p.strip().strip("?").strip()
            if p and p.lower() not in ("vs", "versus", "or", "and") and len(p) > 2:
                alternatives.append(p)
        return alternatives[:4]


class MultiStepReasoningStrategy(ReasoningStrategy):
    """Complex multi-stage reasoning for multi-part queries."""

    @property
    def name(self) -> str:
        return StrategyType.MULTI_STEP.value

    async def can_handle(self, context: ReasoningContext) -> bool:
        text = context.query.lower()
        multi_part = text.count("?") > 1
        has_multi = any(
            w in text for w in ("first", "then", "finally", "step", "phase", "stage", "multi")
        )
        return multi_part or has_multi or len(text.split()) > 30

    async def reason(self, context: ReasoningContext) -> ReasoningChain:
        chain = ReasoningChain(strategy=StrategyType.MULTI_STEP)
        sub_problems = self._decompose(context.query)

        for i, sub in enumerate(sub_problems):
            chain.add_step(
                ReasoningStep(
                    description=f"Sub-problem {i + 1}",
                    content=f"Solving: {sub}",
                    step_type="sub_problem",
                    confidence=0.8 - (i * 0.05),
                )
            )

        chain.add_step(
            ReasoningStep(
                description="Synthesis",
                content="Combining sub-problem solutions into a unified conclusion",
                step_type="synthesis",
                confidence=0.75,
            )
        )

        chain.conclusion = f"Multi-step reasoning complete across {len(sub_problems)} sub-problems."
        chain.confidence = 0.75
        return chain

    @staticmethod
    def _decompose(text: str) -> list[str]:
        sentences = re.split(r"[.?!\n]+", text)
        parts = [s.strip() for s in sentences if len(s.strip()) > 10]
        if not parts:
            parts = [text]
        return parts[:4]


class SelfCritiqueReasoningStrategy(ReasoningStrategy):
    """Wraps another strategy and adds self-critique refinement."""

    def __init__(self, inner: ReasoningStrategy | None = None) -> None:
        self._inner = inner or AnalyticalReasoningStrategy()

    @property
    def name(self) -> str:
        return StrategyType.SELF_CRITIQUE.value

    async def can_handle(self, context: ReasoningContext) -> bool:
        return await self._inner.can_handle(context)

    async def reason(self, context: ReasoningContext) -> ReasoningChain:
        chain = await self._inner.reason(context)

        flaws = self._find_flaws(chain)
        if flaws:
            chain.add_step(
                ReasoningStep(
                    description="Self-critique refinement",
                    content=f"Addressing identified issues: {'; '.join(flaws)}",
                    step_type="refinement",
                    confidence=0.7,
                    evidence=flaws,
                )
            )
            chain.conclusion = f"Refined conclusion after addressing: {'; '.join(flaws[:3])}"
            chain.confidence = min(chain.confidence + 0.05, 1.0)

        chain.metadata["self_critiqued"] = True
        return chain

    @staticmethod
    def _find_flaws(chain: ReasoningChain) -> list[str]:
        flaws = []
        if not chain.steps:
            flaws.append("No reasoning steps generated")
        if not chain.conclusion:
            flaws.append("Missing conclusion")
        if chain.confidence < 0.5:
            flaws.append("Low confidence in reasoning")
        if len(chain.steps) == 1:
            flaws.append("Single step may oversimplify the problem")
        return flaws
