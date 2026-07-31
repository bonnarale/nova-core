"""EvolutionEngine — manages autonomous improvement cycles.

Event-driven scheduler with rate limiting, state machine, and history tracking.
Triggered by task.completed events; runs MetaAgent when threshold is met.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EvolutionState(str, Enum):
    """State machine for evolution cycles."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


class EvolutionAlreadyRunning(Exception):
    """Raised when a cycle is started while another is running."""

    pass


class RateLimitExceeded(Exception):
    """Raised when a cycle is requested before the rate limit allows."""

    def __init__(self, tasks_since: int, min_tasks: int) -> None:
        self.tasks_since = tasks_since
        self.min_tasks = min_tasks
        remaining = min_tasks - tasks_since
        super().__init__(
            f"Rate limit: {remaining} more tasks needed before next cycle "
            f"({tasks_since}/{min_tasks} since last cycle)"
        )


class EvolutionEngine:
    """Manages autonomous evolution cycles with rate limiting and history.

    Subscribes to task.completed events and triggers MetaAgent when
    the task threshold is met.
    """

    def __init__(
        self,
        bus: Any = None,
        meta_agent: Any = None,
        outcome_tracker: Any = None,
        success_tracker: Any = None,
        min_tasks_between_cycles: int = 50,
    ) -> None:
        self._bus = bus
        self._meta_agent = meta_agent
        self._outcome_tracker = outcome_tracker
        self._success_tracker = success_tracker
        self._min_tasks_between_cycles = min_tasks_between_cycles

        self._state = EvolutionState.IDLE
        self._tasks_since_last_cycle = 0
        self._history: list[dict[str, Any]] = []
        self._current_cycle_id: str | None = None

    @property
    def state(self) -> EvolutionState:
        return self._state

    @property
    def tasks_since_last_cycle(self) -> int:
        return self._tasks_since_last_cycle

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    async def on_task_completed(self, event_type: str, data: dict[str, Any]) -> None:
        """Event handler for task.completed — increments counter and checks threshold."""
        # Don't increment or trigger while a cycle is already running
        if self._state == EvolutionState.RUNNING:
            return

        self._tasks_since_last_cycle += 1
        logger.debug(
            "EvolutionEngine: task completed (%d/%d since last cycle)",
            self._tasks_since_last_cycle,
            self._min_tasks_between_cycles,
        )

        if self._tasks_since_last_cycle >= self._min_tasks_between_cycles:
            try:
                await self.run_evolution_cycle()
            except EvolutionAlreadyRunning:
                logger.debug("EvolutionEngine: cycle already running, skipping")
            except RateLimitExceeded:
                logger.debug("EvolutionEngine: rate limit exceeded, skipping")
            except Exception as exc:
                logger.exception("EvolutionEngine: cycle failed: %s", exc)

    async def start_cycle(self) -> None:
        """Start an evolution cycle. Raises if already running or rate limited."""
        if self._state == EvolutionState.RUNNING:
            raise EvolutionAlreadyRunning()

        if self._tasks_since_last_cycle < self._min_tasks_between_cycles:
            raise RateLimitExceeded(
                self._tasks_since_last_cycle,
                self._min_tasks_between_cycles,
            )

        self._state = EvolutionState.RUNNING
        self._current_cycle_id = str(uuid.uuid4())

        # Publish start event
        await self._publish_event(
            "evolution_cycle_started",
            {"cycle_id": self._current_cycle_id},
        )

    async def run_evolution_cycle(self) -> dict[str, Any]:
        """Run a full evolution cycle: start → execute meta agent → record → complete.

        Returns the cycle result dict.
        """
        await self.start_cycle()

        cycle_result: dict[str, Any] = {
            "cycle_id": self._current_cycle_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tasks_since_last_cycle": self._tasks_since_last_cycle,
            "status": "completed",
            "result": None,
        }

        try:
            # Execute MetaAgent
            if self._meta_agent is not None:
                result = await self._meta_agent.execute(
                    task="run_evolution_cycle",
                    context={},
                )
                cycle_result["result"] = result
            else:
                cycle_result["result"] = {"status": "skipped", "error": "No MetaAgent available"}

            # Publish completion event
            await self._publish_event(
                "evolution_cycle_completed",
                cycle_result,
            )

        except Exception as exc:
            cycle_result["status"] = "failed"
            cycle_result["error"] = str(exc)
            logger.exception("EvolutionEngine: cycle execution failed: %s", exc)

            await self._publish_event(
                "evolution_cycle_failed",
                cycle_result,
            )

        finally:
            # Record in history
            self._history.append(cycle_result)

            # Reset state
            self._state = EvolutionState.IDLE
            self._tasks_since_last_cycle = 0
            self._current_cycle_id = None

        return cycle_result

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return the most recent evolution cycle records."""
        return self._history[-limit:]

    async def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event to the event bus if available."""
        if self._bus is None:
            return
        try:
            await self._bus.emit(event_type, data)
        except Exception as exc:
            logger.debug("EvolutionEngine: failed to publish event %s: %s", event_type, exc)
