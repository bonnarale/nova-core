"""SelfImprovementGenerator — analyzes outcome patterns and generates improvement goals.

Identifies strategies with low success rates, high error counts, and duration
outliers, then produces ImprovementGoal objects for human review.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.learning.base import OutcomeStore
from app.learning.models import ImprovementGoal

logger = logging.getLogger(__name__)

# Default threshold: strategies below this success rate trigger improvement goals
DEFAULT_SUCCESS_THRESHOLD = 0.6


class SelfImprovementGenerator:
    """Analyzes execution outcomes and generates improvement goals.

    Identifies low-performing strategies and produces ImprovementGoal
    objects with confidence scores based on sample size.
    """

    def __init__(
        self,
        store: OutcomeStore,
        success_threshold: float = DEFAULT_SUCCESS_THRESHOLD,
    ) -> None:
        self._store = store
        self._success_threshold = success_threshold

    async def analyze_patterns(self) -> list[dict[str, Any]]:
        """Analyze outcome history to identify improvement areas.

        Returns list of dicts describing each flagged strategy:
        {strategy, success_rate, execution_count, avg_duration_ms, avg_error_count}
        """
        outcomes = await self._store.list_all(limit=10_000)
        if not outcomes:
            return []

        # Group by strategy
        strategy_data: dict[str, dict[str, Any]] = {}
        for o in outcomes:
            strat = o.strategy_used
            if strat not in strategy_data:
                strategy_data[strat] = {
                    "strategy": strat,
                    "success_count": 0,
                    "total_count": 0,
                    "total_duration_ms": 0,
                    "total_errors": 0,
                }
            d = strategy_data[strat]
            d["total_count"] += 1
            if o.outcome == "success":
                d["success_count"] += 1
            d["total_duration_ms"] += o.duration_ms
            d["total_errors"] += o.error_count

        # Flag strategies below threshold
        flagged = []
        for strat, d in strategy_data.items():
            if d["total_count"] == 0:
                continue
            success_rate = d["success_count"] / d["total_count"]
            if success_rate < self._success_threshold:
                flagged.append({
                    "strategy": strat,
                    "success_rate": success_rate,
                    "execution_count": d["total_count"],
                    "avg_duration_ms": d["total_duration_ms"] / d["total_count"],
                    "avg_error_count": d["total_errors"] / d["total_count"],
                })

        return flagged

    async def generate_goals(self) -> list[ImprovementGoal]:
        """Generate ImprovementGoal objects for flagged strategies.

        Confidence is based on sample size: higher sample count → higher confidence,
        capped at 0.95.
        """
        flagged = await self.analyze_patterns()
        goals = []

        for area in flagged:
            # Confidence based on sample size (log10 scale, capped at 0.95)
            import math
            sample_count = area["execution_count"]
            confidence = min(0.95, 0.5 + 0.2 * math.log10(max(sample_count, 1)))

            goal = ImprovementGoal(
                id=str(uuid.uuid4()),
                target_strategy=area["strategy"],
                proposed_change=(
                    f"Improve strategy '{area['strategy']}' — "
                    f"current success rate {area['success_rate']:.1%} "
                    f"({sample_count} executions) is below {_pct(self._success_threshold)} threshold."
                ),
                confidence=round(confidence, 3),
                evidence={
                    "execution_count": sample_count,
                    "success_rate": area["success_rate"],
                    "avg_duration_ms": area["avg_duration_ms"],
                    "avg_error_count": area["avg_error_count"],
                },
            )
            goals.append(goal)

        logger.info(
            "SelfImprovementGenerator: generated %d goals from %d flagged strategies",
            len(goals), len(flagged),
        )
        return goals


def _pct(value: float) -> str:
    """Format a float as a percentage string."""
    return f"{value:.0%}"
