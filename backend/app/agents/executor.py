"""Agent executor — wraps agent execution with lifecycle, timeout,
retry, tracing, and metrics.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.context import AgentExecutionContext
from app.agents.lifecycle import AgentLifecycle

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Result of an agent execution wrapped by the executor."""

    def __init__(
        self,
        agent_id: str = "",
        task_id: str = "",
        success: bool = False,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        duration_ms: float = 0.0,
        retries: int = 0,
    ) -> None:
        self.agent_id = agent_id
        self.task_id = task_id
        self.success = success
        self.result = result or {}
        self.error = error
        self.duration_ms = duration_ms
        self.retries = retries

    @property
    def status(self) -> str:
        return "completed" if self.success else "failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "retries": self.retries,
        }


class AgentExecutor:
    """Executes agent tasks with lifecycle management, timeout, and retry."""

    def __init__(
        self,
        max_retries: int = 0,
        default_timeout: float = 300.0,
    ) -> None:
        self._max_retries = max_retries
        self._default_timeout = default_timeout

    async def execute(
        self,
        agent: BaseAgent,
        task: str,
        context: dict[str, Any] | None = None,
        lifecycle: AgentLifecycle | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> ExecutionResult:
        ctx = context or {}
        timeout = timeout or self._default_timeout
        retries_limit = max_retries if max_retries is not None else self._max_retries
        start = time.time()
        last_error: str | None = None
        retries = 0

        if lifecycle:
            lifecycle.start_running()

        try:
            if timeout > 0:
                result = await asyncio.wait_for(
                    agent.execute(task, ctx),
                    timeout=timeout,
                )
            else:
                result = await agent.execute(task, ctx)

            duration_ms = (time.time() - start) * 1000

            if lifecycle:
                lifecycle.complete()

            return ExecutionResult(
                agent_id=agent.agent_id,
                task_id=ctx.get("task_id", ""),
                success=True,
                result=result,
                duration_ms=duration_ms,
            )

        except asyncio.TimeoutError:
            last_error = f"Execution timed out after {timeout}s"
            retries += 1
            logger.warning("Agent %s timed out (attempt %d)", agent.agent_id, retries)

        except Exception as exc:
            last_error = str(exc)
            retries += 1
            logger.warning("Agent %s failed: %s (attempt %d)", agent.agent_id, exc, retries)

        # Retry loop
        for attempt in range(retries_limit):
            try:
                if timeout > 0:
                    result = await asyncio.wait_for(
                        agent.execute(task, ctx),
                        timeout=timeout,
                    )
                else:
                    result = await agent.execute(task, ctx)

                duration_ms = (time.time() - start) * 1000
                if lifecycle:
                    lifecycle.complete()

                return ExecutionResult(
                    agent_id=agent.agent_id,
                    task_id=ctx.get("task_id", ""),
                    success=True,
                    result=result,
                    duration_ms=duration_ms,
                    retries=retries + attempt + 1,
                )

            except asyncio.TimeoutError:
                last_error = f"Execution timed out after {timeout}s (attempt {attempt + 2})"
                retries += 1

            except Exception as exc:
                last_error = str(exc)
                retries += 1

        duration_ms = (time.time() - start) * 1000
        if lifecycle:
            lifecycle.fail(last_error or "execution failed")

        return ExecutionResult(
            agent_id=agent.agent_id,
            task_id=ctx.get("task_id", ""),
            success=False,
            error=last_error,
            duration_ms=duration_ms,
            retries=retries,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_retries": self._max_retries,
            "default_timeout": self._default_timeout,
        }
