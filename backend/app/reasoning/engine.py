"""ReasoningEngine — orchestrates the full reasoning pipeline."""

from __future__ import annotations

import logging
from typing import Any

from app.reasoning.base import CandidateEvaluator, DecisionValidator, ReasoningStrategy, SelfCritic
from app.reasoning.critic import DefaultCritic
from app.reasoning.evaluator import DefaultEvaluator
from app.reasoning.models import (
    ReasoningChain,
    ReasoningContext,
    ReasoningDecision,
    ReasoningStatus,
)
from app.reasoning.registry import StrategyRegistry
from app.reasoning.validator import DefaultValidator

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """Orchestrates the reasoning pipeline:
    context → select strategy → reason → evaluate → validate → critique → decision.
    """

    def __init__(
        self,
        registry: StrategyRegistry | None = None,
        evaluator: CandidateEvaluator | None = None,
        validator: DecisionValidator | None = None,
        critic: SelfCritic | None = None,
    ) -> None:
        self._registry = registry or StrategyRegistry()
        self._evaluator = evaluator or DefaultEvaluator()
        self._validator = validator or DefaultValidator()
        self._critic = critic or DefaultCritic()

    @property
    def registry(self) -> StrategyRegistry:
        return self._registry

    @property
    def evaluator(self) -> CandidateEvaluator:
        return self._evaluator

    @property
    def validator(self) -> DecisionValidator:
        return self._validator

    @property
    def critic(self) -> SelfCritic:
        return self._critic

    async def reason(
        self,
        query: str,
        user_id: str | None = None,
        session_id: str | None = None,
        strategy_name: str | None = None,
        constraints: list[str] | None = None,
        preferences: dict[str, Any] | None = None,
        context_data: dict[str, Any] | None = None,
    ) -> ReasoningDecision:
        """Full reasoning pipeline."""
        context = ReasoningContext(
            query=query,
            user_id=user_id,
            session_id=session_id,
            constraints=constraints or [],
            preferences=preferences or {},
            context_data=context_data or {},
        )

        decision = ReasoningDecision(query=query, status=ReasoningStatus.IN_PROGRESS)

        try:
            strategy = await self._select_strategy(context, strategy_name)
            if strategy is None:
                raise ValueError("No suitable reasoning strategy found")

            chain = await strategy.reason(context)
            decision.chain = chain

            evaluation = await self._evaluator.evaluate(chain, context)
            decision.evaluation = evaluation

            decision.conclusion = chain.conclusion
            decision.confidence = chain.confidence
            decision.metadata["strategy"] = strategy.name
            decision.metadata["steps_count"] = len(chain.steps)

            validation = await self._validator.validate(decision, context)
            decision.validation = validation

            if validation.is_valid:
                critique = await self._critic.critique(chain, context)
                decision.critique = critique
            else:
                decision.metadata["validation_issues"] = validation.issues

            decision.status = ReasoningStatus.COMPLETED

        except Exception as exc:
            logger.exception("ReasoningEngine.reason failed: %s", exc)
            decision.status = ReasoningStatus.FAILED
            decision.error = str(exc)

        return decision

    async def reason_with_strategy(
        self,
        context: ReasoningContext,
        strategy: ReasoningStrategy,
    ) -> ReasoningDecision:
        """Run the pipeline with a specific strategy."""
        decision = ReasoningDecision(query=context.query, status=ReasoningStatus.IN_PROGRESS)

        try:
            chain = await strategy.reason(context)
            decision.chain = chain

            evaluation = await self._evaluator.evaluate(chain, context)
            decision.evaluation = evaluation

            decision.conclusion = chain.conclusion
            decision.confidence = chain.confidence
            decision.metadata["strategy"] = strategy.name

            validation = await self._validator.validate(decision, context)
            decision.validation = validation

            if validation.is_valid:
                critique = await self._critic.critique(chain, context)
                decision.critique = critique
            else:
                decision.metadata["validation_issues"] = validation.issues

            decision.status = ReasoningStatus.COMPLETED

        except Exception as exc:
            logger.exception("reason_with_strategy failed: %s", exc)
            decision.status = ReasoningStatus.FAILED
            decision.error = str(exc)

        return decision

    async def _select_strategy(
        self,
        context: ReasoningContext,
        strategy_name: str | None,
    ) -> ReasoningStrategy | None:
        if strategy_name:
            strategy = self._registry.get(strategy_name)
            if strategy:
                return strategy
            logger.warning("Requested strategy '%s' not found, using automatic selection", strategy_name)
        return await self._registry.select(context)
