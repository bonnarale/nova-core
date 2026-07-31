"""Tests for SuccessTracker — success rate computation, strategy ranking, metric aggregation."""

import pytest

from app.learning.models import ExecutionOutcome
from app.learning.outcome_tracker import InMemoryOutcomeStore
from app.learning.success_tracker import SuccessTracker


class TestSuccessTracker:
    """Tests for SuccessTracker."""

    @pytest.fixture
    def store(self):
        return InMemoryOutcomeStore()

    @pytest.fixture
    def tracker(self, store):
        return SuccessTracker(store)

    @pytest.mark.asyncio
    async def test_success_rate_empty(self, tracker):
        rate = await tracker.compute_success_rate()
        assert rate == 0.0

    @pytest.mark.asyncio
    async def test_success_rate_80_percent(self, store, tracker):
        for i in range(80):
            await store.create(
                ExecutionOutcome(
                    id=f"o{i}", execution_id=f"e{i}", outcome="success"
                )
            )
        for i in range(20):
            await store.create(
                ExecutionOutcome(
                    id=f"f{i}", execution_id=f"fe{i}", outcome="failure"
                )
            )
        rate = await tracker.compute_success_rate()
        assert rate == pytest.approx(0.8)

    @pytest.mark.asyncio
    async def test_strategy_effectiveness(self, store, tracker):
        # Strategy A: 90% success (9/10)
        for i in range(9):
            await store.create(
                ExecutionOutcome(
                    id=f"a{i}", execution_id=f"ae{i}",
                    strategy_used="A", outcome="success",
                )
            )
        await store.create(
            ExecutionOutcome(
                id="af1", execution_id="afe1", strategy_used="A", outcome="failure"
            )
        )

        # Strategy B: 70% success (7/10)
        for i in range(7):
            await store.create(
                ExecutionOutcome(
                    id=f"b{i}", execution_id=f"be{i}",
                    strategy_used="B", outcome="success",
                )
            )
        for i in range(3):
            await store.create(
                ExecutionOutcome(
                    id=f"bf{i}", execution_id=f"bfe{i}",
                    strategy_used="B", outcome="failure",
                )
            )

        effectiveness = await tracker.compute_strategy_effectiveness()
        assert effectiveness["A"] == pytest.approx(0.9)
        assert effectiveness["B"] == pytest.approx(0.7)

    @pytest.mark.asyncio
    async def test_average_metrics(self, store, tracker):
        for i in range(3):
            await store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used="greedy",
                    outcome="success",
                    duration_ms=100 + i * 50,  # 100, 150, 200
                    error_count=i,
                    user_satisfaction=0.8 + i * 0.05,
                )
            )

        metrics = await tracker.compute_average_metrics(strategy="greedy")
        assert metrics["count"] == 3
        assert metrics["avg_duration_ms"] == pytest.approx(150.0)
        assert metrics["avg_error_count"] == pytest.approx(1.0)
        assert metrics["avg_user_satisfaction"] == pytest.approx(0.85)

    @pytest.mark.asyncio
    async def test_average_metrics_empty(self, tracker):
        metrics = await tracker.compute_average_metrics()
        assert metrics["count"] == 0
        assert metrics["avg_duration_ms"] == 0.0

    @pytest.mark.asyncio
    async def test_strategy_rankings(self, store, tracker):
        # Strategy "best": 100% success
        for i in range(5):
            await store.create(
                ExecutionOutcome(
                    id=f"b{i}", execution_id=f"be{i}",
                    strategy_used="best", outcome="success",
                )
            )
        # Strategy "worst": 40% success
        for i in range(2):
            await store.create(
                ExecutionOutcome(
                    id=f"w{i}", execution_id=f"we{i}",
                    strategy_used="worst", outcome="success",
                )
            )
        for i in range(3):
            await store.create(
                ExecutionOutcome(
                    id=f"wf{i}", execution_id=f"wfe{i}",
                    strategy_used="worst", outcome="failure",
                )
            )

        rankings = await tracker.get_strategy_rankings()
        assert len(rankings) == 2
        assert rankings[0]["strategy"] == "best"
        assert rankings[0]["success_rate"] == pytest.approx(1.0)
        assert rankings[1]["strategy"] == "worst"
        assert rankings[1]["success_rate"] == pytest.approx(0.4)
