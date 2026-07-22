"""SuccessTracker — aggregates execution outcomes to compute success rates.

Reads from OutcomeStore to provide per-strategy effectiveness,
overall success rate, and average metrics per strategy.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.learning.base import OutcomeStore

logger = logging.getLogger(__name__)


class SuccessTracker:
    """Aggregates execution outcomes to compute strategy effectiveness."""

    def __init__(self, store: OutcomeStore) -> None:
        self._store = store

    async def compute_success_rate(self) -> float:
        """Compute overall success rate across all outcomes.

        Returns 0.0 when no outcomes exist.
        """
        outcomes = await self._store.list_all(limit=10_000)
        if not outcomes:
            return 0.0
        success_count = sum(1 for o in outcomes if o.outcome == "success")
        return success_count / len(outcomes)

    async def compute_strategy_effectiveness(self) -> dict[str, float]:
        """Compute per-strategy success rate.

        Returns dict mapping strategy name → success rate (0.0–1.0).
        """
        outcomes = await self._store.list_all(limit=10_000)
        if not outcomes:
            return {}

        strategy_counts: dict[str, dict[str, int]] = {}
        for o in outcomes:
            strat = o.strategy_used
            if strat not in strategy_counts:
                strategy_counts[strat] = {"success": 0, "total": 0}
            strategy_counts[strat]["total"] += 1
            if o.outcome == "success":
                strategy_counts[strat]["success"] += 1

        return {
            strat: counts["success"] / counts["total"]
            for strat, counts in strategy_counts.items()
            if counts["total"] > 0
        }

    async def compute_average_metrics(
        self, strategy: str | None = None
    ) -> dict[str, Any]:
        """Compute average duration_ms, error_count, and user_satisfaction.

        If strategy is None, computes across all outcomes.
        """
        if strategy:
            outcomes = await self._store.list_by_strategy(strategy, limit=10_000)
        else:
            outcomes = await self._store.list_all(limit=10_000)

        if not outcomes:
            return {
                "count": 0,
                "avg_duration_ms": 0.0,
                "avg_error_count": 0.0,
                "avg_user_satisfaction": 0.0,
            }

        total = len(outcomes)
        avg_duration = sum(o.duration_ms for o in outcomes) / total
        avg_errors = sum(o.error_count for o in outcomes) / total

        satisfaction_values = [
            o.user_satisfaction for o in outcomes if o.user_satisfaction is not None
        ]
        avg_satisfaction = (
            sum(satisfaction_values) / len(satisfaction_values)
            if satisfaction_values
            else 0.0
        )

        return {
            "count": total,
            "avg_duration_ms": avg_duration,
            "avg_error_count": avg_errors,
            "avg_user_satisfaction": avg_satisfaction,
        }

    async def get_strategy_rankings(self) -> list[dict[str, Any]]:
        """Return strategies ranked by success rate (highest first)."""
        effectiveness = await self.compute_strategy_effectiveness()
        ranked = sorted(effectiveness.items(), key=lambda x: x[1], reverse=True)
        return [
            {"strategy": strat, "success_rate": rate}
            for strat, rate in ranked
        ]

    async def compute_average_quality_by_strategy(self, strategy: str) -> float:
        """Compute average quality score for a strategy.

        Returns 0.0 when no outcomes with quality scores exist.
        """
        outcomes = await self._store.list_by_strategy(strategy, limit=10_000)
        quality_scores = [o.quality_score for o in outcomes if o.quality_score is not None]
        if not quality_scores:
            return 0.0
        return sum(quality_scores) / len(quality_scores)

    async def compute_resource_utilization_by_strategy(self, strategy: str) -> dict[str, float]:
        """Compute average resource utilization for a strategy.

        Returns averages of non-None values; 0.0 when no data.
        """
        outcomes = await self._store.list_by_strategy(strategy, limit=10_000)
        memory_values = [o.resource_metrics.memory_used_mb for o in outcomes if o.resource_metrics and o.resource_metrics.memory_used_mb is not None]
        cpu_values = [o.resource_metrics.cpu_time_ms for o in outcomes if o.resource_metrics and o.resource_metrics.cpu_time_ms is not None]
        token_values = [o.resource_metrics.tokens_used for o in outcomes if o.resource_metrics and o.resource_metrics.tokens_used is not None]
        return {
            "avg_memory_mb": sum(memory_values) / len(memory_values) if memory_values else 0.0,
            "avg_cpu_ms": sum(cpu_values) / len(cpu_values) if cpu_values else 0.0,
            "avg_tokens": sum(token_values) / len(token_values) if token_values else 0.0,
        }

    async def get_metrics_by_execution_id(self, execution_id: str) -> dict[str, Any] | None:
        """Return full metrics for a given execution ID, or None if not found."""
        outcome = await self._store.get_by_execution(execution_id)
        if outcome is None:
            return None
        return {
            "execution_id": outcome.execution_id,
            "strategy_used": outcome.strategy_used,
            "outcome": outcome.outcome,
            "quality_score": outcome.quality_score,
            "resource_metrics": {
                "memory_used_mb": outcome.resource_metrics.memory_used_mb,
                "cpu_time_ms": outcome.resource_metrics.cpu_time_ms,
                "tokens_used": outcome.resource_metrics.tokens_used,
            } if outcome.resource_metrics else None,
            "system_impact": {
                "latency_ms": outcome.system_impact.latency_ms,
                "throughput_ops_per_sec": outcome.system_impact.throughput_ops_per_sec,
            } if outcome.system_impact else None,
            "created_at": outcome.created_at,
        }

    async def get_metrics_by_time_range(self, start: str, end: str) -> list[dict[str, Any]]:
        """Return metrics for outcomes within [start, end) timestamps (ISO format)."""
        outcomes = await self._store.list_all(limit=10_000)
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        result = []
        for o in outcomes:
            if o.created_at:
                created = datetime.fromisoformat(o.created_at)
                if start_dt <= created < end_dt:
                    result.append({
                        "execution_id": o.execution_id,
                        "strategy_used": o.strategy_used,
                        "outcome": o.outcome,
                        "quality_score": o.quality_score,
                        "resource_metrics": {
                            "memory_used_mb": o.resource_metrics.memory_used_mb,
                            "cpu_time_ms": o.resource_metrics.cpu_time_ms,
                            "tokens_used": o.resource_metrics.tokens_used,
                        } if o.resource_metrics else None,
                        "system_impact": {
                            "latency_ms": o.system_impact.latency_ms,
                            "throughput_ops_per_sec": o.system_impact.throughput_ops_per_sec,
                        } if o.system_impact else None,
                        "created_at": o.created_at,
                    })
        return result

    async def get_aggregated_metrics_by_strategy(self, strategy: str) -> dict[str, Any]:
        """Return aggregated metrics (averages, count) for a strategy."""
        outcomes = await self._store.list_by_strategy(strategy, limit=10_000)
        if not outcomes:
            return {
                "count": 0,
                "avg_quality_score": 0.0,
                "avg_memory_mb": 0.0,
                "avg_cpu_ms": 0.0,
                "avg_tokens": 0.0,
                "avg_latency_ms": 0.0,
                "avg_throughput": 0.0,
                "avg_duration_ms": 0.0,
            }
        total = len(outcomes)
        # Quality scores (only non-None)
        quality_scores = [o.quality_score for o in outcomes if o.quality_score is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        # Resource metrics (only non-None)
        memory_vals = [o.resource_metrics.memory_used_mb for o in outcomes if o.resource_metrics and o.resource_metrics.memory_used_mb is not None]
        cpu_vals = [o.resource_metrics.cpu_time_ms for o in outcomes if o.resource_metrics and o.resource_metrics.cpu_time_ms is not None]
        token_vals = [o.resource_metrics.tokens_used for o in outcomes if o.resource_metrics and o.resource_metrics.tokens_used is not None]
        # System impact (only non-None)
        latency_vals = [o.system_impact.latency_ms for o in outcomes if o.system_impact and o.system_impact.latency_ms is not None]
        throughput_vals = [o.system_impact.throughput_ops_per_sec for o in outcomes if o.system_impact and o.system_impact.throughput_ops_per_sec is not None]
        # Duration
        duration_vals = [o.duration_ms for o in outcomes]
        return {
            "count": total,
            "avg_quality_score": avg_quality,
            "avg_memory_mb": sum(memory_vals) / len(memory_vals) if memory_vals else 0.0,
            "avg_cpu_ms": sum(cpu_vals) / len(cpu_vals) if cpu_vals else 0.0,
            "avg_tokens": sum(token_vals) / len(token_vals) if token_vals else 0.0,
            "avg_latency_ms": sum(latency_vals) / len(latency_vals) if latency_vals else 0.0,
            "avg_throughput": sum(throughput_vals) / len(throughput_vals) if throughput_vals else 0.0,
            "avg_duration_ms": sum(duration_vals) / total,
        }
