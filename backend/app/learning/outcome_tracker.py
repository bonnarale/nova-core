"""OutcomeTracker — captures execution outcomes from task lifecycle events.

Subscribes to task.completed and task.failed events via the EventBus,
creates ExecutionOutcome records, and stores them via OutcomeStore.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.learning.base import OutcomeStore
from app.learning.events import outcome_recorded_event
from app.learning.models import ExecutionOutcome

logger = logging.getLogger(__name__)


class InMemoryOutcomeStore(OutcomeStore):
    """In-memory implementation of OutcomeStore using plain dicts."""

    def __init__(self) -> None:
        self._outcomes: dict[str, ExecutionOutcome] = {}

    async def create(self, outcome: ExecutionOutcome) -> ExecutionOutcome:
        self._outcomes[outcome.execution_id] = outcome
        return outcome

    async def get_by_execution(self, execution_id: str) -> ExecutionOutcome | None:
        return self._outcomes.get(execution_id)

    async def list_by_strategy(
        self, strategy: str, limit: int = 500
    ) -> list[ExecutionOutcome]:
        results = [
            o for o in self._outcomes.values() if o.strategy_used == strategy
        ]
        return results[:limit]

    async def list_by_agent(
        self, agent_id: str, limit: int = 500
    ) -> list[ExecutionOutcome]:
        results = [
            o for o in self._outcomes.values() if o.task_id == agent_id
        ]
        return results[:limit]

    async def list_all(self, limit: int = 500) -> list[ExecutionOutcome]:
        return list(self._outcomes.values())[:limit]

    async def list_failures(self, limit: int = 500) -> list[ExecutionOutcome]:
        return [o for o in self._outcomes.values() if o.outcome == "failure"][:limit]

    async def count(self) -> int:
        return len(self._outcomes)


class OutcomeTracker:
    """Tracks execution outcomes by subscribing to task lifecycle events.

    Creates ExecutionOutcome records on task.completed and task.failed,
    deduplicating by execution_id.
    """

    def __init__(
        self,
        store: OutcomeStore | None = None,
        event_bus: Any | None = None,
    ) -> None:
        self._store = store or InMemoryOutcomeStore()
        self._event_bus = event_bus

    @property
    def store(self) -> OutcomeStore:
        return self._store

    async def subscribe(self) -> None:
        """Register event handlers on the EventBus."""
        if self._event_bus is not None and hasattr(self._event_bus, "on"):
            self._event_bus.on("task.completed", self._on_task_completed)
            self._event_bus.on("task.failed", self._on_task_failed)
            logger.info("OutcomeTracker: subscribed to task.completed / task.failed")

    async def _on_task_completed(self, event_type: str, data: dict[str, Any]) -> None:
        task_id = data.get("task_id", "")
        try:
            await self.record_outcome(
                execution_id=task_id,
                task_id=task_id,
                strategy_used=data.get("strategy", "default"),
                outcome="success",
                duration_ms=data.get("duration_ms", 0),
                error_count=0,
            )
        except Exception:
            logger.exception("OutcomeTracker: failed to record success for %s", task_id)

    async def _on_task_failed(self, event_type: str, data: dict[str, Any]) -> None:
        task_id = data.get("task_id", "")
        try:
            await self.record_outcome(
                execution_id=task_id,
                task_id=task_id,
                strategy_used=data.get("strategy", "default"),
                outcome="failure",
                duration_ms=data.get("duration_ms", 0),
                error_count=data.get("error_count", 1),
            )
        except Exception:
            logger.exception("OutcomeTracker: failed to record failure for %s", task_id)

    async def record_outcome(
        self,
        execution_id: str,
        task_id: str | None = None,
        strategy_used: str = "default",
        outcome: str = "success",
        duration_ms: int = 0,
        error_count: int = 0,
        user_satisfaction: float | None = None,
    ) -> ExecutionOutcome:
        """Create and store an ExecutionOutcome. Deduplicates by execution_id."""
        existing = await self._store.get_by_execution(execution_id)
        if existing is not None:
            logger.debug("OutcomeTracker: duplicate outcome for %s, skipping", execution_id)
            return existing

        now = datetime.now(timezone.utc).isoformat()
        record = ExecutionOutcome(
            id=ExecutionOutcome.new_id(),
            execution_id=execution_id,
            task_id=task_id,
            strategy_used=strategy_used,
            outcome=outcome,
            duration_ms=duration_ms,
            error_count=error_count,
            user_satisfaction=user_satisfaction,
            created_at=now,
        )
        stored = await self._store.create(record)

        # Emit learning event
        if self._event_bus is not None and hasattr(self._event_bus, "emit"):
            try:
                event = outcome_recorded_event(
                    execution_id=execution_id,
                    outcome=outcome,
                    strategy_used=strategy_used,
                    duration_ms=duration_ms,
                    error_count=error_count,
                )
                await self._event_bus.emit(event.event_type, event.payload)
            except Exception:
                logger.debug("OutcomeTracker: failed to emit outcome_recorded event")

        return stored
