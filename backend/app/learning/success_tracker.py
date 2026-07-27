"""SuccessTracker — computes success rates, strategy effectiveness, and rankings."""

from __future__ import annotations

import logging
from typing import Any

from app.learning.base import OutcomeStore

logger = logging.getLogger(__name__)


class SuccessTracker:
    """Computes success metrics from execution outcomes.

    Provides overall success rate, per-strategy effectiveness,
    average metrics, and strategy rankings.
    """

    def __init__(self, store: OutcomeStore) -> None:
        self._store = store

    async def compute_success_rate(self) -> float:
        """Compute overall success rate across all outcomes.

        Returns float between 0.0 and 1.0. Returns 0.0 if no outcomes.
        """
        outcomes = await self._store.list_all(limit=100_000)
        if not outcomes:
            return 0.0
        success_count = sum(1 for o in outcomes if o.outcome == "success")
        return success_count / len(outcomes)

    async def compute_strategy_effectiveness(self) -> dict[str, float]:
        """Compute success rate per strategy.

        Returns dict mapping strategy name → success rate (0.0–1.0).
        Only includes strategies with at least 1 execution.
        """
        outcomes = await self._store.list_all(limit=100_000)
        if not outcomes:
            return {}

        strategy_data: dict[str, dict[str, int]] = {}
        for o in outcomes:
            strat = o.strategy_used
            if not strat:
                continue
            if strat not in strategy_data:
                strategy_data[strat] = {"success": 0, "total": 0}
            strategy_data[strat]["total"] += 1
            if o.outcome == "success":
                strategy_data[strat]["success"] += 1

        return {
            strat: data["success"] / data["total"]
            for strat, data in strategy_data.items()
            if data["total"] > 0
        }

    async def compute_average_metrics(
        self, strategy: str | None = None
    ) -> dict[str, float]:
        """Compute average duration, error count, and satisfaction.

        Args:
            strategy: If provided, filter to this strategy only.

        Returns dict with avg_duration_ms, avg_error_count, avg_user_satisfaction, count.
        """
        if strategy:
            outcomes = await self._store.list_by_strategy(strategy)
        else:
            outcomes = await self._store.list_all(limit=100_000)

        if not outcomes:
            return {
                "count": 0,
                "avg_duration_ms": 0.0,
                "avg_error_count": 0.0,
                "avg_user_satisfaction": 0.0,
            }

        count = len(outcomes)
        total_duration = sum(o.duration_ms for o in outcomes)
        total_errors = sum(o.error_count for o in outcomes)
        total_satisfaction = sum(o.user_satisfaction for o in outcomes)

        return {
            "count": count,
            "avg_duration_ms": total_duration / count,
            "avg_error_count": total_errors / count,
            "avg_user_satisfaction": total_satisfaction / count,
        }

    async def get_strategy_rankings(self) -> list[dict[str, Any]]:
        """Return strategies ranked by success rate (best first).

        Each entry: {strategy, success_rate, execution_count}
        """
        effectiveness = await self.compute_strategy_effectiveness()
        outcomes = await self._store.list_all(limit=100_000)

        # Count executions per strategy
        execution_counts: dict[str, int] = {}
        for o in outcomes:
            if o.strategy_used:
                execution_counts[o.strategy_used] = execution_counts.get(o.strategy_used, 0) + 1

        rankings = [
            {
                "strategy": strat,
                "success_rate": rate,
                "execution_count": execution_counts.get(strat, 0),
            }
            for strat, rate in effectiveness.items()
        ]
        rankings.sort(key=lambda r: (-r["success_rate"], -r["execution_count"]))
        return rankings
