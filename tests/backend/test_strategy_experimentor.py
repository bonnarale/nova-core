"""Tests for StrategyExperimentor — balanced assignment, insufficient data, chi-squared."""

import pytest

from app.learning.models import ExecutionOutcome
from app.learning.outcome_tracker import InMemoryOutcomeStore
from app.learning.strategy_experimentor import StrategyExperimentor


class TestStrategyExperimentor:
    """Tests for StrategyExperimentor."""

    @pytest.fixture
    def store(self):
        return InMemoryOutcomeStore()

    @pytest.fixture
    def experimentor(self, store):
        return StrategyExperimentor(store)

    def test_create_experiment(self, experimentor):
        exp = experimentor.create_experiment(
            name="test-exp", control="greedy", variant="lazy"
        )
        assert exp.name == "test-exp"
        assert exp.control == "greedy"
        assert exp.variant == "lazy"
        assert exp.active is True

    def test_get_experiment(self, experimentor):
        exp = experimentor.create_experiment("e1", "A", "B")
        found = experimentor.get_experiment(exp.id)
        assert found is not None
        assert found.id == exp.id

    def test_list_experiments(self, experimentor):
        experimentor.create_experiment("e1", "A", "B")
        experimentor.create_experiment("e2", "C", "D")
        assert len(experimentor.list_experiments()) == 2

    def test_assign_variant_balanced(self, experimentor):
        exp = experimentor.create_experiment("e1", "A", "B")
        # Over 1000 assignments, should be approximately balanced
        counts = {"A": 0, "B": 0}
        for i in range(1000):
            strategy = experimentor.assign_variant(exp.id)
            experimentor.record_assignment(exp.id, f"exec-{i}", strategy)
            counts[strategy] += 1

        # Within ±10% tolerance
        assert abs(counts["A"] - 500) <= 100
        assert abs(counts["B"] - 500) <= 100

    def test_assign_variant_inactive(self, experimentor):
        exp = experimentor.create_experiment("e1", "A", "B")
        exp.active = False
        result = experimentor.assign_variant(exp.id)
        assert result is None

    def test_assign_variant_nonexistent(self, experimentor):
        result = experimentor.assign_variant("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_compare_insufficient_data(self, store, experimentor):
        exp = experimentor.create_experiment("e1", "A", "B")
        # Only 10 samples per variant — below threshold
        for i in range(10):
            experimentor.record_assignment(exp.id, f"exec-a{i}", "A")
            experimentor.record_assignment(exp.id, f"exec-b{i}", "B")
            await store.create(
                ExecutionOutcome(
                    id=f"o-a{i}", execution_id=f"exec-a{i}", outcome="success"
                )
            )
            await store.create(
                ExecutionOutcome(
                    id=f"o-b{i}", execution_id=f"exec-b{i}", outcome="failure"
                )
            )

        result = await experimentor.compare_outcomes(exp.id)
        assert result["status"] == "insufficient_data"
        assert result["control_samples"] == 10
        assert result["variant_samples"] == 10

    @pytest.mark.asyncio
    async def test_compare_significant_difference(self, store, experimentor):
        exp = experimentor.create_experiment("e1", "A", "B")
        # 50 samples per variant with clear difference
        # A: 90% success
        for i in range(45):
            experimentor.record_assignment(exp.id, f"exec-a{i}", "A")
            await store.create(
                ExecutionOutcome(
                    id=f"o-a{i}", execution_id=f"exec-a{i}", outcome="success"
                )
            )
        for i in range(5):
            experimentor.record_assignment(exp.id, f"exec-a-f{i}", "A")
            await store.create(
                ExecutionOutcome(
                    id=f"o-af{i}", execution_id=f"exec-a-f{i}", outcome="failure"
                )
            )

        # B: 50% success
        for i in range(25):
            experimentor.record_assignment(exp.id, f"exec-b{i}", "B")
            await store.create(
                ExecutionOutcome(
                    id=f"o-b{i}", execution_id=f"exec-b{i}", outcome="success"
                )
            )
        for i in range(25):
            experimentor.record_assignment(exp.id, f"exec-b-f{i}", "B")
            await store.create(
                ExecutionOutcome(
                    id=f"o-bf{i}", execution_id=f"exec-b-f{i}", outcome="failure"
                )
            )

        result = await experimentor.compare_outcomes(exp.id)
        assert result["status"] == "completed"
        assert result["control_samples"] == 50
        assert result["variant_samples"] == 50
        assert result["control_success_rate"] == pytest.approx(0.9)
        assert result["variant_success_rate"] == pytest.approx(0.5)
        assert result["winner"] == "A"

    @pytest.mark.asyncio
    async def test_compare_no_difference(self, store, experimentor):
        exp = experimentor.create_experiment("e1", "A", "B")
        # Both at 80% success — no significant difference
        for i in range(40):
            experimentor.record_assignment(exp.id, f"exec-a{i}", "A")
            await store.create(
                ExecutionOutcome(
                    id=f"o-a{i}", execution_id=f"exec-a{i}", outcome="success"
                )
            )
        for i in range(10):
            experimentor.record_assignment(exp.id, f"exec-af{i}", "A")
            await store.create(
                ExecutionOutcome(
                    id=f"o-af{i}", execution_id=f"exec-af{i}", outcome="failure"
                )
            )
        for i in range(40):
            experimentor.record_assignment(exp.id, f"exec-b{i}", "B")
            await store.create(
                ExecutionOutcome(
                    id=f"o-b{i}", execution_id=f"exec-b{i}", outcome="success"
                )
            )
        for i in range(10):
            experimentor.record_assignment(exp.id, f"exec-bf{i}", "B")
            await store.create(
                ExecutionOutcome(
                    id=f"o-bf{i}", execution_id=f"exec-bf{i}", outcome="failure"
                )
            )

        result = await experimentor.compare_outcomes(exp.id)
        assert result["status"] == "completed"
        assert result["significant"] is False
        assert result["winner"] is None
