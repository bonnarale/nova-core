"""Tests for SelfImprovementGenerator — pattern analysis, goal generation."""

import pytest

from app.learning.models import ExecutionOutcome
from app.learning.outcome_tracker import InMemoryOutcomeStore
from app.learning.self_improvement import SelfImprovementGenerator


class TestSelfImprovementGenerator:
    """Tests for SelfImprovementGenerator."""

    @pytest.fixture
    def store(self):
        return InMemoryOutcomeStore()

    @pytest.fixture
    def generator(self, store):
        return SelfImprovementGenerator(store, success_threshold=0.6)

    @pytest.mark.asyncio
    async def test_analyze_empty(self, generator):
        flagged = await generator.analyze_patterns()
        assert flagged == []

    @pytest.mark.asyncio
    async def test_analyze_flags_low_success(self, store, generator):
        # Strategy "bad": 40% success rate (20/50)
        for i in range(20):
            await store.create(
                ExecutionOutcome(
                    id=f"s{i}", execution_id=f"se{i}",
                    strategy_used="bad", outcome="success",
                )
            )
        for i in range(30):
            await store.create(
                ExecutionOutcome(
                    id=f"f{i}", execution_id=f"fe{i}",
                    strategy_used="bad", outcome="failure",
                )
            )

        flagged = await generator.analyze_patterns()
        assert len(flagged) == 1
        assert flagged[0]["strategy"] == "bad"
        assert flagged[0]["success_rate"] == pytest.approx(0.4)
        assert flagged[0]["execution_count"] == 50

    @pytest.mark.asyncio
    async def test_analyze_ignores_good_strategy(self, store, generator):
        # Strategy "good": 90% success rate
        for i in range(45):
            await store.create(
                ExecutionOutcome(
                    id=f"s{i}", execution_id=f"se{i}",
                    strategy_used="good", outcome="success",
                )
            )
        for i in range(5):
            await store.create(
                ExecutionOutcome(
                    id=f"f{i}", execution_id=f"fe{i}",
                    strategy_used="good", outcome="failure",
                )
            )

        flagged = await generator.analyze_patterns()
        assert len(flagged) == 0

    @pytest.mark.asyncio
    async def test_generate_goals(self, store, generator):
        # Strategy "poor": 30% success (15/50)
        for i in range(15):
            await store.create(
                ExecutionOutcome(
                    id=f"s{i}", execution_id=f"se{i}",
                    strategy_used="poor", outcome="success",
                )
            )
        for i in range(35):
            await store.create(
                ExecutionOutcome(
                    id=f"f{i}", execution_id=f"fe{i}",
                    strategy_used="poor", outcome="failure",
                )
            )

        goals = await generator.generate_goals()
        assert len(goals) == 1
        goal = goals[0]
        assert goal.target_strategy == "poor"
        assert 0.0 <= goal.confidence <= 1.0
        assert goal.evidence["execution_count"] == 50
        assert goal.evidence["success_rate"] == pytest.approx(0.3)
        assert goal.status == "pending_approval"

    @pytest.mark.asyncio
    async def test_generate_goals_confidence_scales_with_samples(self, store):
        # More samples → higher confidence
        gen_low = SelfImprovementGenerator(store, success_threshold=0.6)
        gen_high = SelfImprovementGenerator(store, success_threshold=0.6)

        # Low sample count (10)
        for i in range(4):
            await store.create(
                ExecutionOutcome(
                    id=f"ls{i}", execution_id=f"lse{i}",
                    strategy_used="low", outcome="success",
                )
            )
        for i in range(6):
            await store.create(
                ExecutionOutcome(
                    id=f"lf{i}", execution_id=f"lfe{i}",
                    strategy_used="low", outcome="failure",
                )
            )

        goals_low = await gen_low.generate_goals()
        assert len(goals_low) == 1
        confidence_low = goals_low[0].confidence

        # High sample count (200) — add more outcomes
        for i in range(80):
            await store.create(
                ExecutionOutcome(
                    id=f"hs{i}", execution_id=f"hse{i}",
                    strategy_used="high", outcome="success",
                )
            )
        for i in range(120):
            await store.create(
                ExecutionOutcome(
                    id=f"hf{i}", execution_id=f"hfe{i}",
                    strategy_used="high", outcome="failure",
                )
            )

        goals_high = await gen_high.generate_goals()
        high_goal = next(g for g in goals_high if g.target_strategy == "high")
        assert high_goal.confidence > confidence_low

    @pytest.mark.asyncio
    async def test_analyze_includes_metrics(self, store, generator):
        for i in range(5):
            await store.create(
                ExecutionOutcome(
                    id=f"o{i}", execution_id=f"e{i}",
                    strategy_used="slow",
                    outcome="success" if i < 2 else "failure",
                    duration_ms=1000 + i * 200,
                    error_count=i,
                )
            )

        flagged = await generator.analyze_patterns()
        assert len(flagged) == 1
        assert flagged[0]["avg_duration_ms"] > 0
        assert flagged[0]["avg_error_count"] > 0
