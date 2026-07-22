"""AgentRuntime — the top-level orchestrator for the Multi-Agent Runtime.

Provides register(), unregister(), dispatch(), delegate(), coordinate(),
cancel(), and shutdown() operations.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Awaitable

from app.agents.base import BaseAgent
from app.agents.capabilities import AgentCapability, CapabilityRegistry
from app.agents.context import AgentExecutionContext
from app.agents.coordinator import (
    AgentCoordinator,
    CoordinationPattern,
    CoordinationStep,
    CoordinatorResult,
)
from app.agents.dispatcher import AgentDispatcher, DispatchResult
from app.agents.executor import AgentExecutor, ExecutionResult
from app.agents.lifecycle import AgentLifecycle, AgentState
from app.agents.metrics import MetricsCollector
from app.agents.registry import AgentRegistry
from app.agents.scheduler import AgentScheduler
from app.agents.tracing import TraceSpan, Tracer

logger = logging.getLogger(__name__)

DispatchFn = Callable[[str, str, dict[str, Any]], Awaitable[dict[str, Any]]]


class AgentRuntime:
    """Top-level Multi-Agent Runtime.

    Manages agent registration, capability-based dispatch, coordination,
    scheduling, lifecycle, metrics, and tracing.
    """

    def __init__(
        self,
        max_concurrency: int = 10,
        default_timeout: float = 300.0,
        max_retries: int = 0,
    ) -> None:
        self._registry = AgentRegistry()
        self._dispatcher = AgentDispatcher(self._registry.capabilities)
        self._scheduler = AgentScheduler(max_concurrency=max_concurrency)
        self._executor = AgentExecutor(max_retries=max_retries, default_timeout=default_timeout)
        self._coordinator = AgentCoordinator(dispatch_fn=self._internal_dispatch)
        self._tracer = Tracer()
        self._metrics = MetricsCollector()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def registry(self) -> AgentRegistry:
        return self._registry

    @property
    def dispatcher(self) -> AgentDispatcher:
        return self._dispatcher

    @property
    def scheduler(self) -> AgentScheduler:
        return self._scheduler

    @property
    def coordinator(self) -> AgentCoordinator:
        return self._coordinator

    @property
    def tracer(self) -> Tracer:
        return self._tracer

    @property
    def metrics(self) -> MetricsCollector:
        return self._metrics

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        agent: BaseAgent,
        capability: AgentCapability | None = None,
    ) -> None:
        self._registry.register(agent, capability)
        self._metrics.increment("runtime.registered")
        logger.info("Runtime: registered agent %s", agent.agent_id)

    def unregister(self, agent_id: str) -> None:
        self._registry.unregister(agent_id)
        self._scheduler.set_agent_limit(agent_id, 0)
        self._metrics.increment("runtime.unregistered")
        logger.info("Runtime: unregistered agent %s", agent_id)

    def get_agent(self, agent_id: str) -> BaseAgent | None:
        return self._registry.get(agent_id)

    def list_agents(self) -> list[BaseAgent]:
        return self._registry.list_agents()

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch(
        self,
        agent_id: str,
        task: str,
        context: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        agent = self._registry.get(agent_id)
        if agent is None:
            self._metrics.increment("dispatch.errors.agent_not_found")
            return {"agent": agent_id, "status": "error", "error": f"Agent '{agent_id}' not found"}

        ctx = AgentExecutionContext.from_dict(context or {})
        ctx.assigned_agent = agent_id
        ctx.goal = task

        span = self._tracer.start_span(
            agent_id=agent_id,
            task=task,
            task_id=ctx.task_id,
            parent_span_id=ctx.parent_span_id,
            trace_id=ctx.trace_id,
            context=context or {},
        )

        self._metrics.increment("dispatch.total")
        self._metrics.increment(f"dispatch.{agent_id}")

        with self._metrics.time(f"execute.{agent_id}"):
            result = await self._executor.execute(
                agent=agent,
                task=task,
                context=context or {},
                lifecycle=self._registry.get_lifecycle(agent_id),
                timeout=timeout,
            )

        status = "success" if result.success else "error"
        span.close(status=status, output=result.to_dict())
        self._metrics.increment(f"dispatch.{agent_id}.{status}")

        if not result.success:
            self._metrics.increment(f"dispatch.{agent_id}.error")

        self._dispatcher.release(agent_id)
        return result.to_dict()

    async def delegate(
        self,
        from_agent: str,
        to_agent: str,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._metrics.increment("delegation.total")
        ctx = dict(context or {})
        ctx["delegated_from"] = from_agent
        ctx["delegated_to"] = to_agent

        result = await self.dispatch(to_agent, task, ctx)
        self._metrics.increment("delegation.completed")
        return result

    # ------------------------------------------------------------------
    # Coordination
    # ------------------------------------------------------------------

    async def coordinate(
        self,
        steps: list[dict[str, Any]],
        pattern: str = "sequential",
        aggregation_agent: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        coord_steps = [
            CoordinationStep(
                agent_id=s.get("agent", s.get("agent_id", "")),
                task=s.get("task", ""),
                context=s.get("context", {}),
                step_id=s.get("step_id", ""),
                depends_on=s.get("depends_on", []),
            )
            for s in steps
        ]

        pattern_enum = CoordinationPattern(pattern)

        if pattern_enum == CoordinationPattern.SEQUENTIAL:
            result = await self._coordinator.execute_sequential(coord_steps)
        elif pattern_enum == CoordinationPattern.PARALLEL:
            result = await self._coordinator.execute_parallel(coord_steps)
        elif pattern_enum == CoordinationPattern.FAN_OUT:
            agg = aggregation_agent or "executor"
            result = await self._coordinator.execute_fan_out_fan_in(coord_steps, agg)
        elif pattern_enum == CoordinationPattern.DELEGATION:
            if len(coord_steps) >= 2:
                result = await self._coordinator.execute_delegation(
                    coord_steps[0].agent_id, coord_steps[1].agent_id, coord_steps[1].task
                )
            else:
                result = CoordinatorResult(pattern=pattern)
                result.status = "failed"
                result.error = "Delegation requires at least 2 steps"
        elif pattern_enum == CoordinationPattern.AGGREGATION:
            agg = aggregation_agent or "executor"
            result = await self._coordinator.execute_aggregation(coord_steps, agg)
        elif pattern_enum == CoordinationPattern.ARBITRATION:
            arb = aggregation_agent or "executor"
            result = await self._coordinator.execute_arbitration(coord_steps, arb)
        else:
            result = CoordinatorResult(pattern=pattern)
            result.status = "failed"
            result.error = f"Unknown pattern: {pattern}"

        self._metrics.increment(f"coordinate.{pattern}")
        return result.to_dict()

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    async def cancel(self, task_id: str) -> bool:
        cancelled = self._scheduler.cancel(task_id)
        self._metrics.increment("runtime.cancelled")
        return cancelled

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def shutdown(self) -> None:
        for agent in self._registry.list_agents():
            lc = self._registry.get_lifecycle(agent.agent_id)
            if lc:
                lc.shutdown()
            try:
                await agent.shutdown()
            except Exception:
                logger.debug("Error shutting down agent %s", agent.agent_id)
        self._scheduler.clear()
        self._metrics.increment("runtime.shutdown")
        logger.info("Runtime: shutdown complete")

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health(self) -> dict[str, Any]:
        results = {}
        for agent in self._registry.list_agents():
            try:
                h = await agent.health()
                results[agent.agent_id] = h
            except Exception as exc:
                results[agent.agent_id] = {"status": "error", "error": str(exc)}
        return results

    # ------------------------------------------------------------------
    # Internal dispatch function for coordinator
    # ------------------------------------------------------------------

    async def _internal_dispatch(
        self, agent_id: str, task: str, context: dict[str, Any],
    ) -> dict[str, Any]:
        return await self.dispatch(agent_id, task, context)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "agents": self._registry.to_dict(),
            "dispatcher": self._dispatcher.to_dict(),
            "scheduler": self._scheduler.to_dict(),
            "coordinator": self._coordinator.to_dict(),
            "metrics": self.metrics.snapshot(),
        }
