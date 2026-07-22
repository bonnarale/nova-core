"""Strategy registry for dynamic strategy selection."""

from __future__ import annotations

from app.reasoning.base import ReasoningStrategy
from app.reasoning.models import ReasoningContext
from app.reasoning.strategy import (
    AnalyticalReasoningStrategy,
    ComparativeReasoningStrategy,
    DirectReasoningStrategy,
    MultiStepReasoningStrategy,
    SelfCritiqueReasoningStrategy,
)


class StrategyRegistry:
    """Registry of available reasoning strategies with dynamic selection."""

    def __init__(self, strategies: list[ReasoningStrategy] | None = None) -> None:
        self._strategies: dict[str, ReasoningStrategy] = {}
        for s in (strategies if strategies is not None else self._default_strategies()):
            self._strategies[s.name] = s

    @staticmethod
    def _default_strategies() -> list[ReasoningStrategy]:
        return [
            SelfCritiqueReasoningStrategy(),
            MultiStepReasoningStrategy(),
            ComparativeReasoningStrategy(),
            AnalyticalReasoningStrategy(),
            DirectReasoningStrategy(),
        ]

    @property
    def strategies(self) -> dict[str, ReasoningStrategy]:
        return dict(self._strategies)

    def register(self, strategy: ReasoningStrategy) -> None:
        self._strategies[strategy.name] = strategy

    def unregister(self, name: str) -> None:
        self._strategies.pop(name, None)

    def get(self, name: str) -> ReasoningStrategy | None:
        return self._strategies.get(name)

    async def select(self, context: ReasoningContext) -> ReasoningStrategy | None:
        for strategy in self._strategies.values():
            if await strategy.can_handle(context):
                return strategy
        return self._strategies.get("DIRECT")

    def list_names(self) -> list[str]:
        return list(self._strategies.keys())
