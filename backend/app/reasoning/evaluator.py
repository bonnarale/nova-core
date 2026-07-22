"""Default candidate evaluator for reasoning chains."""

from __future__ import annotations

from app.reasoning.base import CandidateEvaluator
from app.reasoning.models import EvaluationResult, ReasoningChain, ReasoningContext


class DefaultEvaluator(CandidateEvaluator):
    """Evaluates reasoning chains on completeness, coherence, and relevance."""

    async def evaluate(
        self, chain: ReasoningChain, context: ReasoningContext
    ) -> EvaluationResult:
        completeness = self._score_completeness(chain)
        coherence = self._score_coherence(chain)
        relevance = self._score_relevance(chain, context)
        score = (completeness * 0.35 + coherence * 0.35 + relevance * 0.30)

        feedback: list[str] = []
        if completeness < 0.6:
            feedback.append("Chain lacks sufficient reasoning steps")
        if coherence < 0.6:
            feedback.append("Steps are not logically connected")
        if relevance < 0.6:
            feedback.append("Some steps deviate from the query")
        if score >= 0.8:
            feedback.append("Strong reasoning chain")

        return EvaluationResult(
            score=round(score, 2),
            completeness=round(completeness, 2),
            coherence=round(coherence, 2),
            relevance=round(relevance, 2),
            feedback=feedback,
        )

    @staticmethod
    def _score_completeness(chain: ReasoningChain) -> float:
        if not chain.steps:
            return 0.0
        has_conclusion = 1.0 if chain.conclusion else 0.0
        step_coverage = min(len(chain.steps) / 3.0, 1.0)
        return (step_coverage * 0.6 + has_conclusion * 0.4)

    @staticmethod
    def _score_coherence(chain: ReasoningChain) -> float:
        if not chain.steps:
            return 0.0
        types = [s.step_type for s in chain.steps]
        unique = len(set(types))
        if unique >= len(types):
            return 0.9
        if unique >= len(types) * 0.5:
            return 0.7
        return 0.5

    @staticmethod
    def _score_relevance(chain: ReasoningChain, context: ReasoningContext) -> float:
        if not chain.steps or not context.query:
            return 0.5
        query_lower = context.query.lower()
        query_words = set(query_lower.split())
        if not query_words:
            return 0.5
        relevant = 0
        for step in chain.steps:
            content_lower = step.content.lower()
            if any(w in content_lower for w in query_words):
                relevant += 1
        return relevant / len(chain.steps) if chain.steps else 0.5
