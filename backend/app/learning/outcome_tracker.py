"""OutcomeTracker — records execution outcomes and subscribes to task events."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from app.learning.base import OutcomeStore
from app.learning.models import ExecutionOutcome

logger = logging.getLogger(__name__)


class InMemoryOutcomeStore(OutcomeStore):
    """In-memory implementation of OutcomeStore for testing and development."""

    def __init__(self) -> None:
        self._outcomes: dict[str, ExecutionOutcome] = {}  # execution_id → outcome

    async def create(self, outcome: ExecutionOutcome) -> ExecutionOutcome:
        """Persist an outcome record (deduplicates by execution_id)."""
        existing = await self.get_by_execution(outcome.execution_id)
        if existing is not None:
            return existing
        self._outcomes[outcome.execution_id] = outcome
        return outcome

    async def get_by_execution(self, execution_id: str) -> Optional[ExecutionOutcome]:
        """Retrieve an outcome by execution ID."""
        return self._outcomes.get(execution_id)

    async def list_by_strategy(self, strategy: str) -> list[ExecutionOutcome]:
        """List all outcomes for a given strategy."""
        return [o for o in self._outcomes.values() if o.strategy_used == strategy]

    async def list_by_agent(self, agent_id: str) -> list[ExecutionOutcome]:
        """List all outcomes where task_id matches agent_id."""
        return [o for o in self._outcomes.values() if o.task_id == agent_id]

    async def list_all(self, limit: int = 1000) -> list[ExecutionOutcome]:
        """List all outcomes with optional limit."""
        outcomes = list(self._outcomes.values())
        return outcomes[:limit]

    async def count(self) -> int:
        """Return total number of outcomes."""
        return len(self._outcomes)


class OutcomeTracker:
    """Records execution outcomes and subscribes to task events.

    Listens to task.completed and task.failed events to automatically
    record outcomes.
    """

    def __init__(
        self,
        store: OutcomeStore | None = None,
        event_bus: Any = None,
    ) -> None:
        self.store = store or InMemoryOutcomeStore()
        self._event_bus = event_bus

    async def subscribe(self) -> None:
        """Register event handlers on the event bus."""
        if self._event_bus is None:
            return
        self._event_bus.on("task.completed", self._on_task_completed)
        self._event_bus.on("task.failed", self._on_task_failed)
        logger.debug("OutcomeTracker: subscribed to task events")

    async def record_outcome(
        self,
        execution_id: str,
        task_id: str = "",
        strategy_used: str = "",
        outcome: str = "success",
        duration_ms: int = 0,
        error_count: int = 0,
    ) -> ExecutionOutcome:
        """Record an execution outcome (with deduplication)."""
        existing = await self.store.get_by_execution(execution_id)
        if existing is not None:
            return existing

        record = ExecutionOutcome(
            id=str(uuid.uuid4()),
            execution_id=execution_id,
            task_id=task_id,
            strategy_used=strategy_used,
            outcome=outcome,
            duration_ms=duration_ms,
            error_count=error_count,
        )
        await self.store.create(record)
        logger.debug("OutcomeTracker: recorded outcome for execution %s", execution_id)
        return record

    async def _on_task_completed(self, event_type: str, data: dict[str, Any]) -> None:
        """Handle task.completed event."""
        task_id = data.get("task_id", "")
        duration_ms = data.get("duration_ms", 0)
        await self.record_outcome(
            execution_id=task_id,
            task_id=task_id,
            outcome="success",
            duration_ms=duration_ms,
        )

    async def _on_task_failed(self, event_type: str, data: dict[str, Any]) -> None:
        """Handle task.failed event."""
        task_id = data.get("task_id", "")
        error_count = data.get("error_count", 1)
        await self.record_outcome(
            execution_id=task_id,
            task_id=task_id,
            outcome="failure",
            error_count=error_count,
        )
