"""Integration test: full flow from task event → outcome → success metrics → goals."""

import pytest

from app.learning.models import ExecutionOutcome
from app.learning.outcome_tracker import InMemoryOutcomeStore, OutcomeTracker
from app.learning.success_tracker import SuccessTracker
from app.learning.strategy_experimentor import StrategyExperimentor
from app.learning.self_improvement import SelfImprovementGenerator


class TestLearningFlowIntegration:
    """End-to-end integration test for the self-improvement subsystem."""

    @pytest.fixture
    def components(self):
        store = InMemoryOutcomeStore()
        tracker = OutcomeTracker(store=store)
        success = SuccessTracker(store=store)
        experimentor = StrategyExperimentor(store=store)
        generator = SelfImprovementGenerator(store=store, success_threshold=0.6)
        return {
            "store": store,
            "tracker": tracker,
            "success": success,
            "experimentor": experimentor,
            "generator": generator,
        }

    @pytest.mark.asyncio
    async def test_full_flow_task_event_to_goals(self, components):
        tracker = components["tracker"]
        success = components["success"]
        generator = components["generator"]

        # Simulate 50 task completions with mixed outcomes
        for i in range(29):
            await tracker.record_outcome(
                execution_id=f"exec-success-{i}",
                task_id=f"task-{i}",
                strategy_used="greedy",
                outcome="success",
                duration_ms=100 + i * 10,
            )
        for i in range(21):
            await tracker.record_outcome(
                execution_id=f"exec-fail-{i}",
                task_id=f"task-{i + 29}",
                strategy_used="greedy",
                outcome="failure",
                duration_ms=200 + i * 20,
                error_count=1,
            )

        # Compute success rate
        rate = await success.compute_success_rate()
        assert rate == pytest.approx(0.58)  # 29/50

        # Generate improvement goals
        goals = await generator.generate_goals()
        assert len(goals) == 1
        assert goals[0].target_strategy == "greedy"
        assert goals[0].evidence["execution_count"] == 50

    @pytest.mark.asyncio
    async def test_full_flow_experiment_comparison(self, components):
        experimentor = components["experimentor"]
        store = components["store"]

        # Create experiment
        exp = experimentor.create_experiment(
            name="greedy vs lazy",
            control="greedy",
            variant="lazy",
        )

        # Assign and record 50 outcomes per variant
        # Greedy: 90% success
        for i in range(45):
            experimentor.record_assignment(exp.id, f"g-s-{i}", "greedy")
            await store.create(
                ExecutionOutcome(
                    id=f"o-gs-{i}", execution_id=f"g-s-{i}",
                    strategy_used="greedy", outcome="success",
                )
            )
        for i in range(5):
            experimentor.record_assignment(exp.id, f"g-f-{i}", "greedy")
            await store.create(
                ExecutionOutcome(
                    id=f"o-gf-{i}", execution_id=f"g-f-{i}",
                    strategy_used="greedy", outcome="failure",
                )
            )

        # Lazy: 60% success
        for i in range(30):
            experimentor.record_assignment(exp.id, f"l-s-{i}", "lazy")
            await store.create(
                ExecutionOutcome(
                    id=f"o-ls-{i}", execution_id=f"l-s-{i}",
                    strategy_used="lazy", outcome="success",
                )
            )
        for i in range(20):
            experimentor.record_assignment(exp.id, f"l-f-{i}", "lazy")
            await store.create(
                ExecutionOutcome(
                    id=f"o-lf-{i}", execution_id=f"l-f-{i}",
                    strategy_used="lazy", outcome="failure",
                )
            )

        # Compare
        result = await experimentor.compare_outcomes(exp.id)
        assert result["status"] == "completed"
        assert result["winner"] == "greedy"
        assert result["control_success_rate"] == pytest.approx(0.9)
        assert result["variant_success_rate"] == pytest.approx(0.6)

    @pytest.mark.asyncio
    async def test_deduplication_in_full_flow(self, components):
        tracker = components["tracker"]

        first = await tracker.record_outcome(
            execution_id="exec-1", outcome="success"
        )
        second = await tracker.record_outcome(
            execution_id="exec-1", outcome="failure"
        )

        # Same record returned, original preserved
        assert first.id == second.id
        assert second.outcome == "success"

        store = components["store"]
        assert await store.count() == 1
