"""Tests for ErrorPatternAnalyzer — threshold detection, cross-strategy patterns, severity scoring, lifecycle archival."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.learning.error_pattern_analyzer import (
    ErrorPatternAnalyzer,
    ErrorPattern,
    PatternAnalysis,
)
from app.learning.models import ExecutionOutcome
from app.long_term_memory.base import MemoryStore
from app.long_term_memory.models import (
    LongTermMemory,
    MemoryStatus,
    MemoryType,
)


# ======================================================================
# Fake in-memory stores for tests
# ======================================================================


class FakeOutcomeStore:
    """In-memory store for execution outcomes."""

    def __init__(self) -> None:
        self._outcomes: dict[str, ExecutionOutcome] = {}

    async def create(self, outcome: ExecutionOutcome) -> ExecutionOutcome:
        self._outcomes[outcome.id] = outcome
        return outcome

    async def get(self, outcome_id: str) -> ExecutionOutcome | None:
        return self._outcomes.get(outcome_id)

    async def list_by_strategy(
        self, strategy: str, limit: int = 100
    ) -> list[ExecutionOutcome]:
        return [
            o for o in self._outcomes.values()
            if o.strategy_used == strategy
        ][:limit]

    async def list_failures(self, limit: int = 100) -> list[ExecutionOutcome]:
        return [
            o for o in self._outcomes.values()
            if o.outcome == "failure"
        ][:limit]


class FakeMemoryStore(MemoryStore):
    """In-memory implementation of MemoryStore for testing."""

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
        results = [
            m for m in self._memories.values()
            if m.user_id == user_id
        ]
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        if status:
            results = [m for m in results if m.status == status]
        return results[offset:offset + limit]

    async def list_by_type(
        self,
        memory_type: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[LongTermMemory]:
        results = [
            m for m in self._memories.values()
            if m.memory_type == memory_type
        ]
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
        results = [
            m for m in self._memories.values()
            if tag_set & set(m.tags)
        ]
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        return results[:limit]

    async def search_by_entity(
        self, entity: str, limit: int = 50
    ) -> list[LongTermMemory]:
        return [
            m for m in self._memories.values()
            if entity in m.entities
        ][:limit]

    async def get_related(
        self, memory_id: str, limit: int = 20
    ) -> list[LongTermMemory]:
        memory = self._memories.get(memory_id)
        if not memory:
            return []
        linked = memory.linked_memory_ids or []
        return [
            m for m in self._memories.values()
            if m.id in linked
        ][:limit]

    async def list_aging(
        self, age_days: int = 30, limit: int = 100
    ) -> list[LongTermMemory]:
        return [
            m for m in self._memories.values()
            if m.status == MemoryStatus.ACTIVE.value
        ][:limit]

    async def list_archivable(
        self, min_age_days: int = 90, importance_below: int = 30, limit: int = 100
    ) -> list[LongTermMemory]:
        return [
            m for m in self._memories.values()
            if m.status == MemoryStatus.ACTIVE.value
            and m.importance_score < importance_below
        ][:limit]

    async def count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for m in self._memories.values():
            counts[m.status] = counts.get(m.status, 0) + 1
        return counts


# ======================================================================
# ErrorPatternAnalyzer Tests
# ======================================================================


class TestErrorPatternAnalyzerInit:
    """Tests for ErrorPatternAnalyzer initialization."""

    def test_create_analyzer(self):
        """Test creating an analyzer with stores."""
        outcome_store = FakeOutcomeStore()
        memory_store = FakeMemoryStore()
        analyzer = ErrorPatternAnalyzer(outcome_store, memory_store)
        assert analyzer is not None

    def test_create_analyzer_with_threshold(self):
        """Test creating analyzer with custom threshold."""
        outcome_store = FakeOutcomeStore()
        memory_store = FakeMemoryStore()
        analyzer = ErrorPatternAnalyzer(
            outcome_store, memory_store, min_occurrences=5
        )
        assert analyzer._min_occurrences == 5


class TestDetectPatterns:
    """Tests for detect_patterns method."""

    @pytest.fixture
    def outcome_store(self) -> FakeOutcomeStore:
        return FakeOutcomeStore()

    @pytest.fixture
    def memory_store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def analyzer(
        self, outcome_store: FakeOutcomeStore, memory_store: FakeMemoryStore
    ) -> ErrorPatternAnalyzer:
        return ErrorPatternAnalyzer(outcome_store, memory_store)

    @pytest.mark.asyncio
    async def test_detect_pattern_from_repeated_errors(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore
    ):
        """Test detecting pattern from 3+ similar errors."""
        # Create 3 failures with similar error messages
        for i in range(3):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used="A",
                    outcome="failure",
                    error_message="Connection timeout: unable to reach database",
                )
            )
        patterns = await analyzer.detect_patterns()
        assert len(patterns) == 1
        assert patterns[0].occurrence_count == 3
        assert "Connection timeout" in patterns[0].error_signature

    @pytest.mark.asyncio
    async def test_detect_pattern_across_strategies(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore
    ):
        """Test detecting pattern that occurs across multiple strategies."""
        strategies = ["A", "B", "C"]
        for i, strategy in enumerate(strategies):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used=strategy,
                    outcome="failure",
                    error_message="Null pointer exception in processor",
                )
            )
        patterns = await analyzer.detect_patterns()
        assert len(patterns) == 1
        assert len(patterns[0].affected_strategies) == 3
        assert set(patterns[0].affected_strategies) == set(strategies)

    @pytest.mark.asyncio
    async def test_no_pattern_below_threshold(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore
    ):
        """Test no pattern detected for isolated errors."""
        # Only 2 failures (below default threshold of 3)
        for i in range(2):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used="A",
                    outcome="failure",
                    error_message="Some error",
                )
            )
        patterns = await analyzer.detect_patterns()
        assert len(patterns) == 0

    @pytest.mark.asyncio
    async def test_detect_multiple_patterns(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore
    ):
        """Test detecting multiple distinct patterns."""
        # Pattern 1: timeout errors
        for i in range(3):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"timeout_{i}",
                    execution_id=f"e{i}",
                    strategy_used="A",
                    outcome="failure",
                    error_message="Request timed out after 30s",
                )
            )
        # Pattern 2: memory errors
        for i in range(3):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"memory_{i}",
                    execution_id=f"e{i+3}",
                    strategy_used="B",
                    outcome="failure",
                    error_message="Out of memory: cannot allocate buffer",
                )
            )
        patterns = await analyzer.detect_patterns()
        assert len(patterns) == 2

    @pytest.mark.asyncio
    async def test_detect_pattern_custom_threshold(
        self, outcome_store: FakeOutcomeStore, memory_store: FakeMemoryStore
    ):
        """Test detection with custom threshold."""
        analyzer = ErrorPatternAnalyzer(
            outcome_store, memory_store, min_occurrences=2
        )
        for i in range(2):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used="A",
                    outcome="failure",
                    error_message="Error X",
                )
            )
        patterns = await analyzer.detect_patterns()
        assert len(patterns) == 1

    @pytest.mark.asyncio
    async def test_no_failures_returns_empty(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore
    ):
        """Test no patterns when no failures exist."""
        patterns = await analyzer.detect_patterns()
        assert len(patterns) == 0


class TestAnalyzePattern:
    """Tests for analyze_pattern method."""

    @pytest.fixture
    def outcome_store(self) -> FakeOutcomeStore:
        return FakeOutcomeStore()

    @pytest.fixture
    def memory_store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def analyzer(
        self, outcome_store: FakeOutcomeStore, memory_store: FakeMemoryStore
    ) -> ErrorPatternAnalyzer:
        return ErrorPatternAnalyzer(outcome_store, memory_store)

    @pytest.mark.asyncio
    async def test_analyze_pattern_severity_score(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore
    ):
        """Test severity score computation based on frequency."""
        # Create 5 failures with same error
        for i in range(5):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used="A",
                    outcome="failure",
                    error_message="Critical error in auth module",
                )
            )
        patterns = await analyzer.detect_patterns()
        analysis = await analyzer.analyze_pattern(patterns[0])
        assert 0 <= analysis.severity_score <= 1
        assert analysis.occurrence_count == 5

    @pytest.mark.asyncio
    async def test_analyze_pattern_root_cause_candidates(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore
    ):
        """Test root cause candidates are identified."""
        for i in range(3):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used="A",
                    outcome="failure",
                    error_message="Database connection refused",
                )
            )
        patterns = await analyzer.detect_patterns()
        analysis = await analyzer.analyze_pattern(patterns[0])
        assert len(analysis.root_cause_candidates) > 0

    @pytest.mark.asyncio
    async def test_analyze_pattern_cross_strategy_severity(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore
    ):
        """Test higher severity for cross-strategy patterns."""
        # Same error across 3 strategies
        for i, strategy in enumerate(["A", "B", "C"]):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used=strategy,
                    outcome="failure",
                    error_message="API rate limit exceeded",
                )
            )
        patterns = await analyzer.detect_patterns()
        analysis = await analyzer.analyze_pattern(patterns[0])
        # Cross-strategy should have higher severity
        assert analysis.severity_score > 0.5


class TestRetrievalMethods:
    """Tests for retrieval methods."""

    @pytest.fixture
    def outcome_store(self) -> FakeOutcomeStore:
        return FakeOutcomeStore()

    @pytest.fixture
    def memory_store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def analyzer(
        self, outcome_store: FakeOutcomeStore, memory_store: FakeMemoryStore
    ) -> ErrorPatternAnalyzer:
        return ErrorPatternAnalyzer(outcome_store, memory_store)

    @pytest.mark.asyncio
    async def test_get_pattern_by_signature(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore
    ):
        """Test retrieving pattern by error signature."""
        for i in range(3):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used="A",
                    outcome="failure",
                    error_message="Timeout error",
                )
            )
        patterns = await analyzer.detect_patterns()
        found = await analyzer.get_pattern_by_signature(patterns[0].error_signature)
        assert found is not None
        assert found.error_signature == patterns[0].error_signature

    @pytest.mark.asyncio
    async def test_get_pattern_by_signature_not_found(
        self, analyzer: ErrorPatternAnalyzer
    ):
        """Test retrieving non-existent pattern returns None."""
        found = await analyzer.get_pattern_by_signature("nonexistent")
        assert found is None

    @pytest.mark.asyncio
    async def test_get_patterns_by_strategy(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore
    ):
        """Test retrieving patterns affecting a specific strategy."""
        # Pattern affecting strategy A
        for i in range(3):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used="A",
                    outcome="failure",
                    error_message="Error in strategy A",
                )
            )
        # Pattern affecting strategy B
        for i in range(3):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i+3}",
                    execution_id=f"e{i+3}",
                    strategy_used="B",
                    outcome="failure",
                    error_message="Error in strategy B",
                )
            )
        patterns = await analyzer.detect_patterns()
        a_patterns = await analyzer.get_patterns_by_strategy("A")
        assert len(a_patterns) == 1
        assert "A" in a_patterns[0].affected_strategies

    @pytest.mark.asyncio
    async def test_get_top_severity_patterns(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore
    ):
        """Test retrieving top severity patterns."""
        # Pattern 1: 3 occurrences
        for i in range(3):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"low_{i}",
                    execution_id=f"e{i}",
                    strategy_used="A",
                    outcome="failure",
                    error_message="Low severity error",
                )
            )
        # Pattern 2: 5 occurrences
        for i in range(5):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"high_{i}",
                    execution_id=f"e{i+3}",
                    strategy_used="B",
                    outcome="failure",
                    error_message="High severity error",
                )
            )
        patterns = await analyzer.detect_patterns()
        top = await analyzer.get_top_severity_patterns(limit=1)
        assert len(top) == 1
        assert top[0].occurrence_count == 5


class TestFixSuggestion:
    """Tests for get_fix_suggestion method."""

    @pytest.fixture
    def outcome_store(self) -> FakeOutcomeStore:
        return FakeOutcomeStore()

    @pytest.fixture
    def memory_store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def analyzer(
        self, outcome_store: FakeOutcomeStore, memory_store: FakeMemoryStore
    ) -> ErrorPatternAnalyzer:
        return ErrorPatternAnalyzer(outcome_store, memory_store)

    @pytest.mark.asyncio
    async def test_get_fix_suggestion_with_known_fix(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore
    ):
        """Test getting fix suggestion for pattern with known resolution."""
        for i in range(3):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used="A",
                    outcome="failure",
                    error_message="Connection pool exhausted",
                )
            )
        patterns = await analyzer.detect_patterns()
        # Manually set suggested_fix
        patterns[0].suggested_fix = "Increase connection pool size"
        suggestion = await analyzer.get_fix_suggestion(patterns[0].error_signature)
        assert suggestion == "Increase connection pool size"

    @pytest.mark.asyncio
    async def test_get_fix_suggestion_no_fix(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore
    ):
        """Test getting fix suggestion returns None when no fix known."""
        for i in range(3):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used="A",
                    outcome="failure",
                    error_message="Unknown error",
                )
            )
        patterns = await analyzer.detect_patterns()
        suggestion = await analyzer.get_fix_suggestion(patterns[0].error_signature)
        assert suggestion is None


class TestPatternLifecycle:
    """Tests for run_pattern_lifecycle method."""

    @pytest.fixture
    def outcome_store(self) -> FakeOutcomeStore:
        return FakeOutcomeStore()

    @pytest.fixture
    def memory_store(self) -> FakeMemoryStore:
        return FakeMemoryStore()

    @pytest.fixture
    def analyzer(
        self, outcome_store: FakeOutcomeStore, memory_store: FakeMemoryStore
    ) -> ErrorPatternAnalyzer:
        return ErrorPatternAnalyzer(outcome_store, memory_store)

    @pytest.mark.asyncio
    async def test_archive_resolved_patterns(
        self, analyzer: ErrorPatternAnalyzer, outcome_store: FakeOutcomeStore,
        memory_store: FakeMemoryStore
    ):
        """Test archiving resolved patterns."""
        for i in range(3):
            await outcome_store.create(
                ExecutionOutcome(
                    id=f"o{i}",
                    execution_id=f"e{i}",
                    strategy_used="A",
                    outcome="failure",
                    error_message="Error to resolve",
                )
            )
        patterns = await analyzer.detect_patterns()
        # Manually create a memory for the pattern with resolved status
        memory = LongTermMemory(
            id="mem1",
            memory_type=MemoryType.ERROR_PATTERN.value,
            content=patterns[0].error_signature,
            status=MemoryStatus.ACTIVE.value,
            metadata={"status": "resolved"},
        )
        await memory_store.create(memory)
        # Run lifecycle
        archived = await analyzer.run_pattern_lifecycle()
        assert archived >= 1
        # Verify memory is archived
        updated_memory = await memory_store.get("mem1")
        assert updated_memory.status == MemoryStatus.ARCHIVED.value

    @pytest.mark.asyncio
    async def test_purge_old_archived_patterns(
        self, analyzer: ErrorPatternAnalyzer, memory_store: FakeMemoryStore
    ):
        """Test purging old archived patterns."""
        # Create an old archived memory
        old_time = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        memory = LongTermMemory(
            id="old_mem",
            memory_type=MemoryType.ERROR_PATTERN.value,
            content="Old error pattern",
            status=MemoryStatus.ARCHIVED.value,
            created_at=old_time,
            updated_at=old_time,
        )
        await memory_store.create(memory)
        # Run lifecycle
        purged = await analyzer.run_pattern_lifecycle()
        assert purged >= 1
        # Verify memory is purged
        fetched = await memory_store.get("old_mem")
        assert fetched is None
