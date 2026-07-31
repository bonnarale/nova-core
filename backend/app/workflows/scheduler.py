"""Scheduling, retry, and timeout management for workflow steps."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.workflows.base import StepHandler
from app.workflows.models import (
    RetryPolicy,
    StepStatus,
    TimeoutPolicy,
    WorkflowExecution,
    WorkflowStep,
    WorkflowStepExecution,
)

logger = logging.getLogger(__name__)


class RetryManager:
    """Manages retry logic for workflow step execution."""

    async def execute_with_retry(
        self,
        handler: StepHandler,
        step: WorkflowStep,
        execution: WorkflowExecution,
        context: dict,
        retry_policy: RetryPolicy | None = None,
    ) -> WorkflowStepExecution:
        policy = retry_policy or step.retry_policy or RetryPolicy()
        last_error: str | None = None

        for attempt in range(policy.max_retries + 1):
            try:
                step_exec = await handler.execute(step, execution, context)
                if step_exec.status == StepStatus.COMPLETED:
                    return step_exec
                last_error = step_exec.error
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Step %s attempt %d/%d failed: %s",
                    step.id, attempt + 1, policy.max_retries + 1, last_error,
                )

            if attempt < policy.max_retries:
                if policy.retryable_errors:
                    if last_error and not any(e in last_error for e in policy.retryable_errors):
                        break

                delay = min(
                    policy.delay_seconds * (policy.backoff_multiplier ** attempt),
                    policy.max_delay_seconds,
                )
                await asyncio.sleep(delay)

        return WorkflowStepExecution(
            step_id=step.id,
            step_name=step.name,
            status=StepStatus.FAILED,
            error=last_error or "Max retries exceeded",
            retry_count=policy.max_retries,
        )


class TimeoutManager:
    """Manages timeouts for workflow steps and executions."""

    async def execute_with_timeout(
        self,
        coro: Any,
        timeout_policy: TimeoutPolicy | None = None,
        default_timeout: float = 300.0,
    ) -> Any:
        timeout = (
            (timeout_policy.step_timeout_seconds if timeout_policy else None)
            or default_timeout
        )
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Step execution timed out after {timeout}s")
