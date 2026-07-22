"""Integration tests — exercises SuccessTracker, PreferenceManager, and ErrorPatternAnalyzer together.

These tests verify the three learning capabilities work coherently in realistic
scenarios, not just in isolation.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from app.learning.error_pattern_analyzer import ErrorPatternAnalyzer
from app.learning.models import (
    ExecutionOutcome,
    OutputQuality,
    ResourceMetrics,
    SystemImpact,
)
from app.learning.outcome_tracker import InMemoryOutcomeStore
from app.learning.success_tracker import SuccessTracker
from app.long_term_memory.base import MemoryStore, MemoryRetriever
from app.long_term_memory.manager import LongTermMemoryManager
from app.long_term_memory.models import (
    LongTermMemory,
    MemoryStatus,
    MemoryType,
    RetrievalResult,
)


# ======================================================================
# Shared fakes
# ======================================================================


class FakeMemoryStore(MemoryStore):
    """In-memory MemoryStore for integration tests."""

    def __init__(self) -> None:
        self._memories: dict[str, LongTermMemory] = {}

    async def create(self, memory: LongTermMemory) -> LongTermMemory:
        self._memories[memory.id] = memory
        return memory

    async def get(self, memory_id: str) -> LongTermMemory | None:
        return self._memories.get(memory_id)

    async def update(self, memory: LongTermMemory) -> LongTermMemory | None:
        if memory.id not in self._memories:
            return None
        self._memories[memory.id] = memory
        return memory

    async def delete(self, memory_id: str) -> bool:
        return self._memories.pop(memory_id, None) is not None

    async def list_by_user(
        self,
        user_id: str,
        memory_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LongTermMemory]:
        results = [m for m in self._memories.values() if m.user_id == user_id]
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        if status:
            results = [m for m in results if m.status == status]
        return results[offset : offset + limit]

    async def list_by_type(
        self,
        memory_type: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[LongTermMemory]:
        results = [m for m in self._memories.values() if m.memory_type == memory_type]
        if status:
            results = [m for m in results if m.status == status]
        return results[:limit]

    async def search_by_tags(
        self,
        tags: list[str],
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[LongTermMemory]:
        tag_set = set(tags)
        results = [m for m in self._memories.values() if tag_set & set(m.tags)]
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        return results[:limit]

    async def search_by_entity(
        self, entity: str, limit: int = 50
    ) -> list[LongTermMemory]:
        return [m for m in self._memories.values() if entity in m.entities][:limit]

    async def get_related(
        self, memory_id: str, limit: int = 20
    ) -> list[LongTermMemory]:
        memory = self._memories.get(memory_id)
        if not memory:
            return []
        linked = memory.linked_memory_ids or []
        return [m for m in self._memories.values() if m.id in linked][:limit]

    async def list_aging(
        self, age_days: int = 30, limit: int = 100
    ) -> list[LongTermMemory]:
        return [
            m
            for m in self._memories.values()
            if m.status == MemoryStatus.ACTIVE.value
        ][:limit]

    async def list_archivable(
        self, min_age_days: int = 90, importance_below: int = 30, limit: int = 100
    ) -> list[LongTermMemory]:
        return [
            m
            for m in self._memories.values()
            if m.status == MemoryStatus.ACTIVE.value
            and m.importance_score < importance_below
        ][:limit]

    async def count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for m in self._memories.values():
            counts[m.status] = counts.get(m.status, 0) + 1
        return counts


class FakeMemoryRetriever(MemoryRetriever):
    """In-memory retriever for semantic search testing."""

    def __init__(self, store: FakeMemoryStore) -> None:
        self._store = store

    async def search(
        self,
        query: str,
        memory_type: str | None = None,
        user_id: str | None = None,
        limit: int = 10,
    ) -> RetrievalResult:
        results = list(self._store._memories.values())
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        if user_id:
            results = [m for m in results if m.user_id == user_id]
        query_lower = query.lower()
        matched = [m for m in results if query_lower in m.content.lower()]
        return RetrievalResult(
            results=matched[:limit],
            total=len(matched),
            query=query,
        )

    async def search_similar(
        self,
        content: str,
        memory_type: str | None = None,
        limit: int = 10,
        threshold: float = 0.75,
    ) -> RetrievalResult:
        return await self.search(content, memory_type=memory_type, limit=limit)


# ======================================================================
# Integration tests
# ======================================================================


class TestSuccessTrackerIntegration:
    """Verifies SuccessTracker with InMemoryOutcomeStore."""

    @pytest.fixture
    def store(self) -> InMemoryOutcomeStore:
        return InMemoryOutcomeStore()

    @pytest.fixture
    def tracker(self, store: InMemoryOutcomeStore) -> SuccessTracker:
        return SuccessTracker(store)

    @pytest.mark.asyncio
    async def test_success_rate_with_mixed_outcomes(
        self, store: InMemoryOutcomeStore, tracker: SuccessTracker
    ):
        """3 successes, 2 failures → 0.6 success rate."""
        for i in range(3):
            await store.create(
                ExecutionOutcome(
                    id=f"o{i}", execution_id=f"e{i}", strategy_used="A", outcome="success"
                )
            )
        for i in range(3, 5):
            await store.create(
                ExecutionOutcome(
                    id=f"o{i}", execution_id=f"e{i}", strategy_used="A", outcome="failure"
                )
            )
        rate = await tracker.compute_success_rate()
        assert rate == pytest.approx(0.6)

    @pytest.mark.asyncio
    async def test_average_quality_by_strategy(
        self, store: InMemoryOutcomeStore, tracker: SuccessTracker
    ):
        """Average quality score for strategy 'B' should be 85."""
        await store.create(
            ExecutionOutcome(
                id="o1",
                execution_id="e1",
                strategy_used="B",
                outcome="success",
                quality_score=80,
            )
        )
        await store.create(
            ExecutionOutcome(
                id="o2",
                execution_id="e2",
                strategy_used="B",
                outcome="success",
                quality_score=90,
            )
        )
        avg = await tracker.compute_average_quality_by_strategy("B")
        assert avg == pytest.approx(85.0)

    @pytest.mark.asyncio
    async def test_resource_utilization_by_strategy(
        self, store: InMemoryOutcomeStore, tracker: SuccessTracker
    ):
        """Resource utilization should average across outcomes."""
        await store.create(
            ExecutionOutcome(
                id="o1",
                execution_id="e1",
                strategy_used="C",
                outcome="success",
                resource_metrics=ResourceMetrics(
                    memory_used_mb=100.0, cpu_time_ms=50.0, tokens_used=1000
                ),
            )
        )
        await store.create(
            ExecutionOutcome(
                id="o2",
                execution_id="e2",
                strategy_used="C",
                outcome="success",
                resource_metrics=ResourceMetrics(
                    memory_used_mb=200.0, cpu_time_ms=150.0, tokens_used=2000
                ),
            )
        )
        util = await tracker.compute_resource_utilization_by_strategy("C")
        assert util["avg_memory_mb"] == pytest.approx(150.0)
        assert util["avg_cpu_ms"] == pytest.approx(100.0)
        assert util["avg_tokens"] == pytest.approx(1500.0)

    @pytest.mark.asyncio
    async def test_strategy_rankings(
        self, store: InMemoryOutcomeStore, tracker: SuccessTracker
    ):
        """Strategy 'X' (100%) should rank above 'Y' (50%)."""
        for i in range(2):
            await store.create(
                ExecutionOutcome(
                    id=f"ox{i}",
                    execution_id=f"ex{i}",
                    strategy_used="X",
                    outcome="success",
                )
            )
        await store.create(
            ExecutionOutcome(
                id="oy0",
                execution_id="ey0",
                strategy_used="Y",
                outcome="success",
            )
        )
        await store.create(
            ExecutionOutcome(
                id="oy1",
                execution_id="ey1",
                strategy_used="Y",
                outcome="failure",
            )
        )
        rankings = await tracker.get_strategy_rankings()
        assert rankings[0]["strategy"] == "X"
        assert rankings[0]["success_rate"] == pytest.approx(1.0)
        assert rankings[1]["strategy"] == "Y"
        assert rankings[1]["success_rate"] == pytest.approx(0.5)


class TestPreferenceManagerIntegration:
    """Verifies PreferenceManager CRUD through LongTermMemoryManager."""

    @pytest.fixture
    def store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def retriever(self, store: FakeMemoryStore) -> FakeMemoryRetriever:
        return FakeMemoryRetriever(store)

    @pytest.fixture
    def manager(
        self, store: FakeMemoryStore, retriever: FakeMemoryRetriever
    ) -> LongTermMemoryManager:
        return LongTermMemoryManager(store=store, retriever=retriever)

    @pytest.mark.asyncio
    async def test_full_preference_lifecycle(
        self, manager: LongTermMemoryManager
    ):
        """Create → update → search → soft-delete a preference."""
        pref = await manager.create_preference(
            user_id="u1",
            content="prefer concise responses",
            tags=["style"],
            categories=["communication"],
        )
        assert pref.memory_type == MemoryType.PREFERENCE.value
        assert pref.user_id == "u1"

        # Update
        updated = await manager.update_preference(pref.id, "prefer detailed responses")
        assert updated is not None
        assert updated.content == "prefer detailed responses"

        # Retrieve by user
        prefs = await manager.get_preferences_by_user("u1")
        assert len(prefs) == 1
        assert prefs[0].id == pref.id

        # Filter by tag
        prefs_tagged = await manager.get_preferences_by_user("u1", tag="style")
        assert len(prefs_tagged) == 1

        # Soft-delete
        deleted = await manager.delete_preference(pref.id)
        assert deleted is True

        # After delete, no active preferences
        prefs_after = await manager.get_preferences_by_user("u1")
        assert len(prefs_after) == 0

    @pytest.mark.asyncio
    async def test_conflict_resolution(
        self, manager: LongTermMemoryManager
    ):
        """Two conflicting preferences — supersede old with new."""
        old_pref = await manager.create_preference(
            user_id="u2",
            content="dark theme preferred",
            tags=["ui"],
        )
        new_pref = await manager.create_preference(
            user_id="u2",
            content="light theme preferred",
            tags=["ui"],
        )

        resolved = await manager.resolve_preference_conflict(
            old_pref.id, new_pref.id, resolution="supersede"
        )
        assert resolved is True

        # Old is now consolidated
        all_prefs = await manager.get_preferences_by_user("u2")
        assert len(all_prefs) == 1
        assert all_prefs[0].id == new_pref.id


class TestErrorPatternAnalyzerIntegration:
    """Verifies ErrorPatternAnalyzer detects real patterns."""

    @pytest.fixture
    def analyzer(self) -> ErrorPatternAnalyzer:
        from tests.backend.test_error_pattern_analyzer import FakeOutcomeStore, FakeMemoryStore

        outcome_store = FakeOutcomeStore()
        memory_store = FakeMemoryStore()
        return ErrorPatternAnalyzer(
            outcome_store=outcome_store,
            memory_store=memory_store,
        ), outcome_store

    @pytest.mark.asyncio
    async def test_detect_and_analyze_pattern(self):
        """Multiple failures with same error produce a detected pattern."""
        from tests.backend.test_error_pattern_analyzer import FakeOutcomeStore, FakeMemoryStore

        outcome_store = FakeOutcomeStore()
        memory_store = FakeMemoryStore()
        analyzer = ErrorPatternAnalyzer(
            outcome_store=outcome_store,
            memory_store=memory_store,
        )

        # 3 failures with the same error message
        for i in range(3):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used="chain_of_thought",
                    outcome="failure",
                    error_message="ConnectionTimeout: server did not respond",
                )
            )

        patterns = await analyzer.detect_patterns(min_occurrences=3)
        assert len(patterns) == 1
        assert patterns[0].occurrence_count == 3

        # Analyze the pattern (takes ErrorPattern object, not string)
        analysis = await analyzer.analyze_pattern(patterns[0])
        assert analysis.occurrence_count == 3
        assert analysis.severity_score > 0
        assert len(analysis.root_cause_candidates) > 0

    @pytest.mark.asyncio
    async def test_cross_strategy_pattern(self):
        """Same error across multiple strategies is detected."""
        from tests.backend.test_error_pattern_analyzer import FakeOutcomeStore, FakeMemoryStore

        outcome_store = FakeOutcomeStore()
        memory_store = FakeMemoryStore()
        analyzer = ErrorPatternAnalyzer(
            outcome_store=outcome_store,
            memory_store=memory_store,
        )

        strategies = ["cot", "tot", "react"]
        for i, strat in enumerate(strategies):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used=strat,
                    outcome="failure",
                    error_message="ValueError: invalid input format",
                )
            )

        patterns = await analyzer.detect_patterns(min_occurrences=2)
        assert len(patterns) == 1
        assert len(patterns[0].affected_strategies) == 3

        analysis = await analyzer.analyze_pattern(patterns[0])
        # Cross-strategy pattern should have higher severity
        assert analysis.severity_score > 0.5

    @pytest.mark.asyncio
    async def test_pattern_below_threshold_not_detected(self):
        """Errors below min_occurrences are not detected."""
        from tests.backend.test_error_pattern_analyzer import FakeOutcomeStore, FakeMemoryStore

        outcome_store = FakeOutcomeStore()
        memory_store = FakeMemoryStore()
        analyzer = ErrorPatternAnalyzer(
            outcome_store=outcome_store,
            memory_store=memory_store,
        )

        # Only 2 failures (below default threshold of 3)
        for i in range(2):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used="cot",
                    outcome="failure",
                    error_message="SomeError: something went wrong",
                )
            )

        patterns = await analyzer.detect_patterns(min_occurrences=3)
        assert len(patterns) == 0


class TestCrossCapabilityWorkflow:
    """End-to-end scenario: record outcomes, detect patterns, store preferences."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Simulate a realistic learning cycle across all three capabilities."""
        # --- Setup ---
        outcome_store = InMemoryOutcomeStore()
        memory_store = FakeMemoryStore()
        retriever = FakeMemoryRetriever(memory_store)
        ltm_manager = LongTermMemoryManager(store=memory_store, retriever=retriever)
        success_tracker = SuccessTracker(outcome_store)

        error_memory_store = FakeMemoryStore()
        error_analyzer = ErrorPatternAnalyzer(
            outcome_store=outcome_store,
            memory_store=error_memory_store,
        )

        user_id = "user_42"

        # --- Phase 1: Record execution outcomes ---
        # 4 successes with good quality
        for i in range(4):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"ok{i}",
                    execution_id=f"ek{i}",
                    strategy_used="chain_of_thought",
                    outcome="success",
                    quality_score=85 + i,
                    resource_metrics=ResourceMetrics(
                        memory_used_mb=64.0, tokens_used=512
                    ),
                )
            )

        # 3 failures with same error
        for i in range(3):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"fail{i}",
                    execution_id=f"ef{i}",
                    strategy_used="chain_of_thought",
                    outcome="failure",
                    error_message="ConnectionTimeout: LLM API unreachable",
                )
            )

        # --- Phase 2: Analyze success metrics ---
        rate = await success_tracker.compute_success_rate()
        assert rate == pytest.approx(4 / 7)

        avg_quality = await success_tracker.compute_average_quality_by_strategy(
            "chain_of_thought"
        )
        assert avg_quality == pytest.approx(86.5)

        # --- Phase 3: Detect error patterns ---
        patterns = await error_analyzer.detect_patterns(min_occurrences=3)
        assert len(patterns) == 1
        assert patterns[0].occurrence_count == 3

        analysis = await error_analyzer.analyze_pattern(patterns[0])
        assert analysis.severity_score > 0

        # --- Phase 4: Store user preference based on learnings ---
        pref = await ltm_manager.create_preference(
            user_id=user_id,
            content="prefer fallback to local model when ConnectionTimeout occurs",
            tags=["error_handling", "connection"],
            categories=["reliability"],
        )
        assert pref.memory_type == MemoryType.PREFERENCE.value

        # Verify preference is retrievable
        prefs = await ltm_manager.get_preferences_by_user(user_id, tag="error_handling")
        assert len(prefs) == 1
        assert "ConnectionTimeout" in prefs[0].content

        # --- Phase 5: Update preference after more data ---
        await ltm_manager.update_preference_metadata(
            pref.id, {"strategy": "chain_of_thought", "error_pattern": analysis.error_signature}
        )
        updated_prefs = await ltm_manager.get_preferences_by_user(user_id)
        assert updated_prefs[0].metadata["strategy"] == "chain_of_thought"
