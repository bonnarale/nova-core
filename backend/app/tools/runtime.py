"""ToolRuntime — top-level orchestrator for tool execution.

Provides execute_tool(), validate_request(), prepare_context(), run(),
collect_result(), and emit_events() with full lifecycle management.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.kernel.events import EventType, KernelEvent, emit
from app.tools.base import Tool, ToolSpec
from app.tools.context import ToolContext
from app.tools.exceptions import (
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolValidationError,
)
from app.tools.lifecycle import ToolState
from app.tools.manager import ToolManager
from app.tools.metrics import ToolMetrics
from app.tools.permissions import PermissionLevel
from app.tools.policies import ToolExecutionPolicy
from app.tools.registry import ToolRegistry
from app.tools.result import ToolResult
from app.tools.tracing import ToolTracer, ToolTrace

logger = logging.getLogger(__name__)


class ToolRuntime:
    """Top-level orchestrator for tool execution.

    Coordinates validation, permissions, context preparation, execution,
    result collection, tracing, metrics, and event emission.
    """

    def __init__(
        self,
        manager: ToolManager | None = None,
        default_timeout: float = 30.0,
        default_retries: int = 0,
        max_concurrency: int = 50,
    ) -> None:
        self._manager = manager or ToolManager()
        self._default_timeout = default_timeout
        self._default_retries = default_retries
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._active: dict[str, asyncio.Task[ToolResult]] = {}

    @property
    def manager(self) -> ToolManager:
        return self._manager

    @property
    def registry(self) -> ToolRegistry:
        return self._manager.registry

    @property
    def tracer(self) -> ToolTracer:
        return self._manager.tracer

    @property
    def metrics(self) -> ToolMetrics:
        return self._manager.metrics

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute_tool(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
        context: ToolContext | None = None,
        timeout: float | None = None,
        retries: int | None = None,
    ) -> ToolResult:
        """Execute a tool with full lifecycle management."""
        params = params or {}
        ctx = context or ToolContext(tool_id=tool_name)

        if not self.validate_request(tool_name, ctx):
            tool = self._manager.get_tool(tool_name)
            if tool is None:
                return ToolResult.error_result(
                    tool_name,
                    f"Tool '{tool_name}' not found",
                )
            return ToolResult.error_result(
                tool_name,
                f"Permission denied or not ready: '{tool_name}'",
            )

        tool = self._manager.get_tool(tool_name)
        if tool is None:
            return ToolResult.error_result(tool_name, f"Tool '{tool_name}' not found")

        ctx = self.prepare_context(tool_name, ctx)
        effective_timeout = timeout if timeout is not None else self._default_timeout
        effective_retries = retries if retries is not None else self._default_retries

        trace = self.tracer.start_trace(
            tool_id=tool_name,
            agent_id=ctx.agent_id,
            user_id=ctx.user_id,
            inputs_metadata={"params": _sanitize(params)},
            execution_id=ctx.execution_id,
        )

        policy = self._manager.get_policy(tool_name)
        if policy:
            effective_retries = max(effective_retries, policy.max_retries)

        result = await self.run(tool, params, ctx, effective_timeout, effective_retries)

        self.collect_result(trace, result)

        self.emit_events(tool_name, result, ctx)

        return result

    def validate_request(self, tool_name: str, context: ToolContext) -> bool:
        tool = self._manager.get_tool(tool_name)
        if tool is None:
            return False
        if not self._manager.check_permission(
            tool_name,
            agent_id=context.agent_id,
            user_id=context.user_id,
            required_level=PermissionLevel[tool.spec.permission_level.upper()],
        ):
            return False
        if not self._manager.check_dependencies(tool_name):
            return False
        lc = self._manager.get_lifecycle(tool_name)
        if lc and lc.state not in (ToolState.READY, ToolState.REGISTERED):
            return False
        return True

    def prepare_context(self, tool_name: str, context: ToolContext) -> ToolContext:
        return context.with_tool(tool_name)

    async def run(
        self,
        tool: Tool,
        params: dict[str, Any],
        context: ToolContext,
        timeout: float,
        retries: int,
    ) -> ToolResult:
        lc = self._manager.get_lifecycle(tool.spec.name)
        if lc:
            lc.start()

        start = time.time()
        last_error: Exception | None = None

        async with self._semaphore:
            for attempt in range(max(1, retries + 1)):
                try:
                    result = await asyncio.wait_for(
                        tool.execute(params, timeout=timeout),
                        timeout=timeout,
                    )
                    if not isinstance(result, ToolResult):
                        result = ToolResult(success=True, data=result, tool_name=tool.spec.name)

                    duration_ms = (time.time() - start) * 1000
                    result.duration_ms = duration_ms
                    result.tool_name = tool.spec.name

                    if lc:
                        lc.complete()

                    return result

                except asyncio.TimeoutError:
                    duration_ms = (time.time() - start) * 1000
                    if attempt < retries:
                        logger.warning(
                            "Tool %s timed out (attempt %d/%d), retrying...",
                            tool.spec.name, attempt + 1, retries + 1,
                        )
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    if lc:
                        lc.fail()
                    return ToolResult.error_result(
                        tool.spec.name,
                        f"Timed out after {timeout}s",
                        duration_ms=duration_ms,
                    )

                except (ToolValidationError, ToolPermissionError) as exc:
                    duration_ms = (time.time() - start) * 1000
                    if lc:
                        lc.fail()
                    return ToolResult.error_result(tool.spec.name, str(exc), duration_ms=duration_ms)

                except Exception as exc:
                    last_error = exc
                    if attempt < retries:
                        logger.warning(
                            "Tool %s failed (attempt %d/%d): %s, retrying...",
                            tool.spec.name, attempt + 1, retries + 1, exc,
                        )
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    break

        duration_ms = (time.time() - start) * 1000
        error_msg = str(last_error) if last_error else "Unknown error"
        if lc:
            lc.fail()
        return ToolResult.error_result(tool.spec.name, error_msg, duration_ms=duration_ms)

    def collect_result(self, trace: ToolTrace, result: ToolResult) -> None:
        trace.outputs_metadata = {
            "success": result.success,
            "error": result.error,
            "duration_ms": result.duration_ms,
        }
        status = "success" if result.success else "error"
        trace.close(
            status=status,
            error=result.error if not result.success else None,
            timed_out="Timed out" in (result.error or ""),
        )

        timed_out = "Timed out" in (result.error or "")
        self._manager.metrics.record_execution(
            result.tool_name,
            result.duration_ms,
            result.success,
            timed_out=timed_out,
        )

    def emit_events(self, tool_name: str, result: ToolResult, context: ToolContext) -> None:
        event_type = EventType.TASK_COMPLETED if result.success else EventType.TASK_FAILED
        emit(KernelEvent.create(
            event_type=event_type,
            agent_id=f"tool:{tool_name}",
            payload={
                "tool": tool_name,
                "execution_id": context.execution_id,
                "agent_id": context.agent_id,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "error": result.error,
            },
        ))

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    async def health(self) -> dict[str, Any]:
        return await self._manager.health_check()

    async def shutdown(self) -> None:
        await self._manager.shutdown_all()

    def list_tools(self) -> list[ToolSpec]:
        return self._manager.list_tools()

    def to_dict(self) -> dict[str, Any]:
        return {
            "manager": self._manager.to_dict(),
            "active_tasks": len(self._active),
        }


def _sanitize(params: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of params safe for logging (truncate long values)."""
    result: dict[str, Any] = {}
    for k, v in params.items():
        if isinstance(v, str) and len(v) > 200:
            result[k] = v[:200] + "..."
        else:
            result[k] = v
    return result
