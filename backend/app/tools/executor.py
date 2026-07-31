"""ToolExecutor — async execution with validation, permissions, timeout, retry."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.agents.metrics import MetricsCollector
from app.agents.tracing import Tracer
from app.kernel.events import EventType, KernelEvent, emit
from app.tools.base import ToolSpec
from app.tools.exceptions import (
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolValidationError,
)
from app.tools.permissions import PermissionChecker, PermissionLevel
from app.tools.registry import ToolRegistry
from app.tools.result import ToolResult

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Unified executor for all tools.

    Every tool invocation goes through this class, ensuring:
    - Input validation against the tool's spec
    - Permission checks
    - Timeout enforcement
    - Retry on transient failures
    - Cancellation support
    - Standardized ToolResult
    - Tracing / metrics / events on every execution
    """

    def __init__(
        self,
        registry: ToolRegistry,
        permission_checker: PermissionChecker | None = None,
        tracer: Tracer | None = None,
        metrics: MetricsCollector | None = None,
        default_timeout: float = 30.0,
        default_retries: int = 0,
    ) -> None:
        self._registry = registry
        self._permission_checker = permission_checker or PermissionChecker()
        self._tracer = tracer
        self._metrics = metrics
        self._default_timeout = default_timeout
        self._default_retries = default_retries
        self._active_tasks: dict[str, asyncio.Task] = {}

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    @property
    def permission_checker(self) -> PermissionChecker:
        return self._permission_checker

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
        agent_id: str = "",
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        timeout: float | None = None,
        retries: int | None = None,
    ) -> ToolResult:
        """Execute a tool with full lifecycle.

        Returns a ``ToolResult`` — never raises (errors are captured
        in the result).
        """
        params = params or {}
        timeout = timeout if timeout is not None else self._default_timeout
        retries = retries if retries is not None else self._default_retries

        # Lookup
        try:
            tool = self._registry.lookup(tool_name)
        except ToolNotFoundError as exc:
            return ToolResult.error_result(tool_name, str(exc))

        spec = tool.spec

        # Permission check
        required_level = PermissionLevel[spec.permission_level.upper()]
        if not self._permission_checker.check(
            tool_name, agent_id=agent_id, required_level=required_level,
        ):
            return ToolResult.error_result(
                tool_name,
                f"Agent '{agent_id}' not permitted to use tool '{tool_name}'",
            )

        # Tracing span
        span = None
        if self._tracer:
            span = self._tracer.start_span(
                agent_id=f"tool:{tool_name}",
                task=spec.name,
                parent_span_id=parent_span_id,
                trace_id=trace_id,
                params=params,
                agent=agent_id,
            )

        # Metrics
        if self._metrics:
            self._metrics.increment(f"tool.{tool_name}.calls")

        # Event
        emit(KernelEvent.create(
            event_type=EventType.TASK_STARTED,
            agent_id=f"tool:{tool_name}",
            payload={"tool": tool_name, "params": params, "agent_id": agent_id},
        ))

        start = time.time()
        last_error: Exception | None = None

        for attempt in range(max(1, retries + 1)):
            try:
                result = await self._execute_single(tool, params, timeout)
                duration_ms = (time.time() - start) * 1000
                result.duration_ms = duration_ms
                result.tool_name = tool_name

                # Close span
                if span:
                    span.close(status="success" if result.success else "error", output=result.to_dict())

                # Metrics
                if self._metrics:
                    self._metrics.increment(f"tool.{tool_name}.{'success' if result.success else 'error'}")
                    self._metrics.record_duration(f"tool.{tool_name}.duration", duration_ms)

                # Event
                emit(KernelEvent.create(
                    event_type=EventType.TASK_COMPLETED if result.success else EventType.TASK_FAILED,
                    agent_id=f"tool:{tool_name}",
                    payload={"tool": tool_name, "result": result.to_dict(), "duration_ms": duration_ms, "attempt": attempt + 1},
                ))

                return result

            except ToolTimeoutError:
                duration_ms = (time.time() - start) * 1000
                if attempt < retries:
                    logger.warning("Tool %s timed out (attempt %d/%d), retrying…", tool_name, attempt + 1, retries + 1)
                    if self._metrics:
                        self._metrics.increment(f"tool.{tool_name}.retry")
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                result = ToolResult.error_result(tool_name, f"Timed out after {timeout}s", duration_ms=duration_ms)
                if span:
                    span.close(status="error", error=result.error)
                return result

            except (ToolValidationError, ToolPermissionError) as exc:
                # Non-retryable
                duration_ms = (time.time() - start) * 1000
                result = ToolResult.error_result(tool_name, str(exc), duration_ms=duration_ms)
                if span:
                    span.close(status="error", error=result.error)
                return result

            except Exception as exc:
                last_error = exc
                duration_ms = (time.time() - start) * 1000
                if attempt < retries:
                    logger.warning("Tool %s failed (attempt %d/%d): %s, retrying…", tool_name, attempt + 1, retries + 1, exc)
                    if self._metrics:
                        self._metrics.increment(f"tool.{tool_name}.retry")
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                break

        # All retries exhausted
        error_msg = str(last_error) if last_error else "Unknown error"
        result = ToolResult.error_result(tool_name, error_msg, duration_ms=(time.time() - start) * 1000)
        if span:
            span.close(status="error", error=result.error)
        return result

    async def cancel(self, tool_name: str) -> bool:
        """Cancel an active tool execution by name."""
        task = self._active_tasks.get(tool_name)
        if task and not task.done():
            task.cancel()
            return True
        return False

    async def get_spec(self, tool_name: str) -> ToolSpec | None:
        """Return the spec for a tool, or None if not found."""
        tool = self._registry.get_tool(tool_name)
        return tool.spec if tool else None

    async def list_tools(self) -> list[ToolSpec]:
        """Return specs for all registered tools."""
        return self._registry.list_tools()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _execute_single(self, tool: Any, params: dict[str, Any], timeout: float) -> ToolResult:
        """Run a single tool execution with timeout."""
        try:
            result = await asyncio.wait_for(
                tool.execute(params),
                timeout=timeout,
            )
            if not isinstance(result, ToolResult):
                return ToolResult(
                    success=True,
                    data=result,
                    tool_name=tool.spec.name,
                )
            return result
        except asyncio.TimeoutError:
            raise ToolTimeoutError(tool.spec.name, timeout)
        except ToolValidationError:
            raise
        except ToolPermissionError:
            raise
        except Exception as exc:
            raise ToolExecutionError(tool.spec.name, str(exc), cause=exc) from exc
