"""Multi-agent coordinator — orchestrates sequential, parallel, fan-out,
fan-in, delegation, aggregation, and arbitration patterns.
"""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class CoordinationPattern(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    FAN_OUT = "fan_out"
    FAN_IN = "fan_in"
    DELEGATION = "delegation"
    AGGREGATION = "aggregation"
    ARBITRATION = "arbitration"


class CoordinationStep:
    """A single step in a coordination plan."""

    def __init__(
        self,
        agent_id: str,
        task: str,
        context: dict[str, Any] | None = None,
        pattern: CoordinationPattern = CoordinationPattern.SEQUENTIAL,
        step_id: str = "",
        depends_on: list[str] | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.task = task
        self.context = context or {}
        self.pattern = pattern
        self.step_id = step_id or f"{agent_id}_{int(time.time() * 1000)}"
        self.depends_on = depends_on or []
        self.result: dict[str, Any] | None = None
        self.status: str = "pending"
        self.error: str | None = None
        self.started_at: float | None = None
        self.completed_at: float | None = None

    @property
    def duration_ms(self) -> float | None:
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "agent_id": self.agent_id,
            "task": self.task,
            "pattern": self.pattern.value,
            "status": self.status,
            "depends_on": list(self.depends_on),
            "duration_ms": round(self.duration_ms, 2) if self.duration_ms else None,
            "error": self.error,
        }


class CoordinatorResult:
    """Aggregated result of a coordination run."""

    def __init__(self, pattern: str = "") -> None:
        self.pattern = pattern
        self.steps: list[CoordinationStep] = []
        self.status: str = "pending"
        self.result: Any = None
        self.error: str | None = None
        self.started_at: float = time.time()
        self.completed_at: float | None = None

    @property
    def duration_ms(self) -> float | None:
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2) if self.duration_ms else None,
            "error": self.error,
        }


# Type alias for the dispatch function
DispatchFn = Callable[[str, str, dict[str, Any]], Awaitable[dict[str, Any]]]


class AgentCoordinator:
    """Orchestrates multi-agent execution patterns."""

    def __init__(self, dispatch_fn: DispatchFn | None = None) -> None:
        self._dispatch_fn = dispatch_fn

    async def execute_sequential(
        self,
        steps: list[CoordinationStep],
        dispatch_fn: DispatchFn | None = None,
    ) -> CoordinatorResult:
        fn = dispatch_fn or self._dispatch_fn
        result = CoordinatorResult(pattern=CoordinationPattern.SEQUENTIAL.value)

        for step in steps:
            result.steps.append(step)
            step.started_at = time.time()
            step.status = "running"

            try:
                ctx = dict(step.context)
                ctx["previous_results"] = [
                    s.to_dict() for s in result.steps[:-1] if s.result
                ]
                if fn is None:
                    raise RuntimeError("No dispatch function configured")
                step.result = await fn(step.agent_id, step.task, ctx)
                step.status = "completed"
            except Exception as exc:
                step.status = "failed"
                step.error = str(exc)
                result.status = "failed"
                result.error = str(exc)
                break
            finally:
                step.completed_at = time.time()

        if result.status != "failed":
            result.status = "completed"

        result.completed_at = time.time()
        return result

    async def execute_parallel(
        self,
        steps: list[CoordinationStep],
        dispatch_fn: DispatchFn | None = None,
    ) -> CoordinatorResult:
        fn = dispatch_fn or self._dispatch_fn
        result = CoordinatorResult(pattern=CoordinationPattern.PARALLEL.value)
        result.steps = list(steps)

        if fn is None:
            raise RuntimeError("No dispatch function configured")

        async def _run_step(step: CoordinationStep) -> None:
            step.started_at = time.time()
            step.status = "running"
            try:
                step.result = await fn(step.agent_id, step.task, step.context)
                step.status = "completed"
            except Exception as exc:
                step.status = "failed"
                step.error = str(exc)
            finally:
                step.completed_at = time.time()

        await asyncio.gather(*[_run_step(s) for s in steps])

        failures = [s for s in steps if s.status == "failed"]
        if failures:
            result.status = "failed"
            result.error = "; ".join(s.error or "unknown" for s in failures)
        else:
            result.status = "completed"

        result.completed_at = time.time()
        return result

    async def execute_fan_out_fan_in(
        self,
        fan_out_steps: list[CoordinationStep],
        aggregate_agent_id: str,
        dispatch_fn: DispatchFn | None = None,
    ) -> CoordinatorResult:
        fn = dispatch_fn or self._dispatch_fn
        result = CoordinatorResult(pattern=CoordinationPattern.FAN_OUT.value)

        # Fan-out: execute all steps in parallel
        fan_out_result = await self.execute_parallel(fan_out_steps, dispatch_fn=fn)
        result.steps.extend(fan_out_steps)

        if fan_out_result.status == "failed":
            result.status = "failed"
            result.error = fan_out_result.error
            result.completed_at = time.time()
            return result

        # Fan-in: aggregate results
        agg_step = CoordinationStep(
            agent_id=aggregate_agent_id,
            task="aggregate results",
            context={
                "fan_out_results": [s.to_dict() for s in fan_out_steps],
                "pattern": "fan_in",
            },
            pattern=CoordinationPattern.FAN_IN,
        )
        agg_step.started_at = time.time()
        agg_step.status = "running"
        try:
            agg_step.result = await fn(aggregate_agent_id, agg_step.task, agg_step.context)
            agg_step.status = "completed"
            result.result = agg_step.result
        except Exception as exc:
            agg_step.status = "failed"
            agg_step.error = str(exc)
            result.status = "failed"
            result.error = str(exc)
        finally:
            agg_step.completed_at = time.time()
            result.steps.append(agg_step)

        if result.status != "failed":
            result.status = "completed"

        result.completed_at = time.time()
        return result

    async def execute_delegation(
        self,
        from_agent: str,
        to_agent: str,
        task: str,
        context: dict[str, Any] | None = None,
        dispatch_fn: DispatchFn | None = None,
    ) -> CoordinatorResult:
        fn = dispatch_fn or self._dispatch_fn
        result = CoordinatorResult(pattern=CoordinationPattern.DELEGATION.value)

        ctx = dict(context or {})
        ctx["delegated_from"] = from_agent

        step = CoordinationStep(
            agent_id=to_agent,
            task=task,
            context=ctx,
            pattern=CoordinationPattern.DELEGATION,
        )
        step.started_at = time.time()
        step.status = "running"
        result.steps.append(step)

        try:
            if fn is None:
                raise RuntimeError("No dispatch function configured")
            step.result = await fn(to_agent, task, ctx)
            step.status = "completed"
            result.result = step.result
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            result.status = "failed"
            result.error = str(exc)
        finally:
            step.completed_at = time.time()
            result.completed_at = time.time()

        if result.status != "failed":
            result.status = "completed"

        return result

    async def execute_aggregation(
        self,
        steps: list[CoordinationStep],
        aggregator_agent_id: str,
        aggregation_task: str = "aggregate",
        dispatch_fn: DispatchFn | None = None,
    ) -> CoordinatorResult:
        fn = dispatch_fn or self._dispatch_fn
        result = CoordinatorResult(pattern=CoordinationPattern.AGGREGATION.value)

        # Execute all steps
        for step in steps:
            step.started_at = time.time()
            step.status = "running"
            result.steps.append(step)
            try:
                if fn is None:
                    raise RuntimeError("No dispatch function configured")
                step.result = await fn(step.agent_id, step.task, step.context)
                step.status = "completed"
            except Exception as exc:
                step.status = "failed"
                step.error = str(exc)
            finally:
                step.completed_at = time.time()

        # Aggregate
        agg_ctx = {
            "results": [s.to_dict() for s in steps if s.status == "completed"],
            "failures": [s.to_dict() for s in steps if s.status == "failed"],
        }
        agg_step = CoordinationStep(
            agent_id=aggregator_agent_id,
            task=aggregation_task,
            context=agg_ctx,
            pattern=CoordinationPattern.AGGREGATION,
        )
        agg_step.started_at = time.time()
        agg_step.status = "running"
        result.steps.append(agg_step)
        try:
            if fn is None:
                raise RuntimeError("No dispatch function configured")
            agg_step.result = await fn(aggregator_agent_id, aggregation_task, agg_ctx)
            agg_step.status = "completed"
            result.result = agg_step.result
        except Exception as exc:
            agg_step.status = "failed"
            agg_step.error = str(exc)
        finally:
            agg_step.completed_at = time.time()

        has_failures = any(s.status == "failed" for s in steps)
        result.status = "failed" if has_failures and agg_step.status != "completed" else "completed"
        result.completed_at = time.time()
        return result

    async def execute_arbitration(
        self,
        candidate_steps: list[CoordinationStep],
        arbitrator_agent_id: str,
        arbitration_task: str = "select best result",
        dispatch_fn: DispatchFn | None = None,
    ) -> CoordinatorResult:
        fn = dispatch_fn or self._dispatch_fn
        result = CoordinatorResult(pattern=CoordinationPattern.ARBITRATION.value)

        # Execute all candidates in parallel
        for step in candidate_steps:
            step.started_at = time.time()
            step.status = "running"
            result.steps.append(step)

        if fn is None:
            raise RuntimeError("No dispatch function configured")

        async def _run(step: CoordinationStep) -> None:
            try:
                step.result = await fn(step.agent_id, step.task, step.context)
                step.status = "completed"
            except Exception as exc:
                step.status = "failed"
                step.error = str(exc)
            finally:
                step.completed_at = time.time()

        await asyncio.gather(*[_run(s) for s in candidate_steps])

        # Arbitration: let arbitrator pick the best
        arb_ctx = {
            "candidates": [s.to_dict() for s in candidate_steps if s.status == "completed"],
        }
        arb_step = CoordinationStep(
            agent_id=arbitrator_agent_id,
            task=arbitration_task,
            context=arb_ctx,
            pattern=CoordinationPattern.ARBITRATION,
        )
        arb_step.started_at = time.time()
        arb_step.status = "running"
        result.steps.append(arb_step)
        try:
            arb_step.result = await fn(arbitrator_agent_id, arbitration_task, arb_ctx)
            arb_step.status = "completed"
            result.result = arb_step.result
        except Exception as exc:
            arb_step.status = "failed"
            arb_step.error = str(exc)
        finally:
            arb_step.completed_at = time.time()

        result.status = "completed" if arb_step.status == "completed" else "failed"
        result.completed_at = time.time()
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_dispatch_fn": self._dispatch_fn is not None,
        }
