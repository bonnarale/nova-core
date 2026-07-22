"""ErrorPatternAnalyzer — detects recurring error patterns from execution outcomes."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from app.learning.models import ExecutionOutcome
from app.long_term_memory.base import MemoryStore
from app.long_term_memory.models import (
    LongTermMemory,
    MemoryStatus,
    MemoryType,
)

logger = logging.getLogger(__name__)


@dataclass
class ErrorPattern:
    """Represents a detected error pattern."""
    
    error_signature: str
    occurrence_count: int = 0
    affected_strategies: list[str] = field(default_factory=list)
    affected_execution_ids: list[str] = field(default_factory=list)
    suggested_fix: str | None = None
    status: str = "active"
    memory_id: str | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class PatternAnalysis:
    """Analysis results for an error pattern."""
    
    error_signature: str
    occurrence_count: int
    severity_score: float
    root_cause_candidates: list[str] = field(default_factory=list)
    affected_strategies: list[str] = field(default_factory=list)


class ErrorPatternAnalyzer:
    """Analyzes execution outcomes to detect recurring error patterns.
    
    Usage::
    
        analyzer = ErrorPatternAnalyzer(outcome_store, memory_store)
        patterns = await analyzer.detect_patterns()
        analysis = await analyzer.analyze_pattern(patterns[0])
    """
    
    def __init__(
        self,
        outcome_store: Any,
        memory_store: MemoryStore,
        min_occurrences: int = 3,
    ) -> None:
        self._outcome_store = outcome_store
        self._memory_store = memory_store
        self._min_occurrences = min_occurrences
        self._patterns: dict[str, ErrorPattern] = {}
    
    def _normalize_error(self, error_message: str) -> str:
        """Normalize error message to create a signature.
        
        Removes specific values like numbers, timestamps, etc.
        to group similar errors together.
        """
        import re
        # Remove numbers, timestamps, and common variable parts
        normalized = re.sub(r'\d+', 'N', error_message)
        normalized = re.sub(r'0x[0-9a-fA-F]+', 'HEX', normalized)
        normalized = re.sub(r'localhost:\d+', 'localhost:PORT', normalized)
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', normalized)
        return normalized.strip()
    
    async def detect_patterns(
        self,
        min_occurrences: int | None = None,
    ) -> list[ErrorPattern]:
        """Detect recurring error patterns from execution failures.
        
        Args:
            min_occurrences: Minimum number of occurrences to form a pattern.
                           If None, uses the instance default.
        
        Returns:
            List of detected error patterns.
        """
        threshold = min_occurrences or self._min_occurrences
        
        # Get all failures from outcome store
        failures = await self._outcome_store.list_failures(limit=1000)
        
        if not failures:
            return []
        
        # Group failures by normalized error signature
        error_groups: dict[str, list[ExecutionOutcome]] = {}
        for outcome in failures:
            if not outcome.error_message:
                continue
            signature = self._normalize_error(outcome.error_message)
            if signature not in error_groups:
                error_groups[signature] = []
            error_groups[signature].append(outcome)
        
        # Filter groups that meet threshold
        patterns = []
        for signature, outcomes in error_groups.items():
            if len(outcomes) >= threshold:
                strategies = list(set(o.strategy_used for o in outcomes if o.strategy_used))
                execution_ids = [o.execution_id for o in outcomes]
                
                pattern = ErrorPattern(
                    error_signature=signature,
                    occurrence_count=len(outcomes),
                    affected_strategies=strategies,
                    affected_execution_ids=execution_ids,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
                patterns.append(pattern)
                self._patterns[signature] = pattern
        
        return patterns
    
    async def analyze_pattern(self, pattern: ErrorPattern) -> PatternAnalysis:
        """Analyze an error pattern for insights.
        
        Args:
            pattern: The error pattern to analyze.
        
        Returns:
            PatternAnalysis with severity score and root cause candidates.
        """
        # Compute severity score based on frequency and impact
        # More occurrences = higher severity
        # Cross-strategy = higher severity
        frequency_factor = min(pattern.occurrence_count / 10.0, 1.0)
        strategy_factor = min(len(pattern.affected_strategies) / 3.0, 1.0)
        severity_score = (frequency_factor * 0.6 + strategy_factor * 0.4)
        
        # Identify root cause candidates based on error signature
        root_cause_candidates = []
        signature_lower = pattern.error_signature.lower()
        
        if "timeout" in signature_lower:
            root_cause_candidates.append("Network latency or server overload")
            root_cause_candidates.append("Insufficient timeout configuration")
        
        if "connection" in signature_lower:
            root_cause_candidates.append("Connection pool exhaustion")
            root_cause_candidates.append("Network connectivity issues")
        
        if "memory" in signature_lower or "allocation" in signature_lower:
            root_cause_candidates.append("Memory leak")
            root_cause_candidates.append("Insufficient memory allocation")
        
        if "null" in signature_lower or "none" in signature_lower:
            root_cause_candidates.append("Missing null check")
            root_cause_candidates.append("Unexpected None value in data flow")
        
        if "permission" in signature_lower or "access" in signature_lower:
            root_cause_candidates.append("Insufficient permissions")
            root_cause_candidates.append("Access control misconfiguration")
        
        if not root_cause_candidates:
            root_cause_candidates.append("Requires manual investigation")
        
        return PatternAnalysis(
            error_signature=pattern.error_signature,
            occurrence_count=pattern.occurrence_count,
            severity_score=severity_score,
            root_cause_candidates=root_cause_candidates,
            affected_strategies=pattern.affected_strategies,
        )
    
    async def get_pattern_by_signature(
        self,
        error_signature: str,
    ) -> ErrorPattern | None:
        """Get a pattern by its error signature.
        
        Args:
            error_signature: The normalized error signature.
        
        Returns:
            The matching ErrorPattern or None.
        """
        return self._patterns.get(error_signature)
    
    async def get_patterns_by_strategy(
        self,
        strategy: str,
    ) -> list[ErrorPattern]:
        """Get all patterns affecting a specific strategy.
        
        Args:
            strategy: The strategy name to filter by.
        
        Returns:
            List of patterns affecting the strategy.
        """
        return [
            p for p in self._patterns.values()
            if strategy in p.affected_strategies
        ]
    
    async def get_top_severity_patterns(
        self,
        limit: int = 10,
    ) -> list[ErrorPattern]:
        """Get top patterns sorted by severity (occurrence count).
        
        Args:
            limit: Maximum number of patterns to return.
        
        Returns:
            List of top severity patterns.
        """
        sorted_patterns = sorted(
            self._patterns.values(),
            key=lambda p: p.occurrence_count,
            reverse=True,
        )
        return sorted_patterns[:limit]
    
    async def get_fix_suggestion(
        self,
        error_signature: str,
    ) -> str | None:
        """Get fix suggestion for a pattern.
        
        Args:
            error_signature: The normalized error signature.
        
        Returns:
            Suggested fix string or None if no fix known.
        """
        pattern = self._patterns.get(error_signature)
        if pattern is None:
            return None
        return pattern.suggested_fix
    
    async def run_pattern_lifecycle(self) -> int:
        """Run pattern lifecycle: archive resolved, purge old.
        
        Returns:
            Number of patterns processed.
        """
        processed = 0
        
        # Get all error pattern memories
        memories = await self._memory_store.list_by_type(
            memory_type=MemoryType.ERROR_PATTERN.value,
            status=MemoryStatus.ACTIVE.value,
        )
        
        # Archive resolved patterns
        for memory in memories:
            if memory.metadata.get("status") == "resolved":
                memory.status = MemoryStatus.ARCHIVED.value
                memory.updated_at = datetime.now(timezone.utc).isoformat()
                await self._memory_store.update(memory)
                processed += 1
        
        # Purge old archived patterns (older than 90 days)
        archived_memories = await self._memory_store.list_by_type(
            memory_type=MemoryType.ERROR_PATTERN.value,
            status=MemoryStatus.ARCHIVED.value,
        )
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
        
        for memory in archived_memories:
            if memory.created_at:
                try:
                    created = datetime.fromisoformat(memory.created_at)
                    if created < cutoff_date:
                        await self._memory_store.delete(memory.id)
                        processed += 1
                except (ValueError, TypeError):
                    # Invalid timestamp, skip
                    pass
        
        return processed
