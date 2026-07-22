"""StepReviewer — evaluates step results and decides next action."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.planner.plan import Step, StepStatus

logger = logging.getLogger(__name__)


class ReviewVerdict(str, Enum):
    SUCCESS = "SUCCESS"
    RETRY = "RETRY"
    REPLAN = "REPLAN"
    SKIP = "SKIP"
    FAIL = "FAIL"


@dataclass
class ReviewResult:
    verdict: ReviewVerdict
    reason: str = ""
    suggestions: list[str] = field(default_factory=list)


class StepReviewer(ABC):
    """Abstract strategy for reviewing a completed step."""

    @abstractmethod
    async def review(
        self,
        step: Step,
        plan_context: dict[str, Any] | None = None,
    ) -> ReviewResult:
        ...


class ResultStepReviewer(StepReviewer):
    """Reviews step results based on execution outcome and heuristics."""

    async def review(
        self,
        step: Step,
        plan_context: dict[str, Any] | None = None,
    ) -> ReviewResult:
        if step.status == StepStatus.SUCCEEDED:
            return self._review_success(step)
        if step.status == StepStatus.FAILED:
            return self._review_failure(step)
        return ReviewResult(verdict=ReviewVerdict.FAIL, reason=f"Unexpected status: {step.status}")

    def _review_success(self, step: Step) -> ReviewResult:
        result = step.result or {}
        error = result.get("error") or result.get("error_message")
        if error:
            step.status = StepStatus.FAILED
            step.error = str(error)
            return ReviewResult(
                verdict=ReviewVerdict.REPLAN,
                reason=f"Step succeeded but result contains error: {error}",
            )
        if step.retry_count > 0:
            logger.info("Step '%s' succeeded after %d retries", step.title, step.retry_count)
        return ReviewResult(verdict=ReviewVerdict.SUCCESS, reason="Step completed successfully")

    def _review_failure(self, step: Step) -> ReviewResult:
        max_retries = step.retry_policy.max_retries
        if step.retry_count < max_retries:
            step.retry_count += 1
            delay = step.retry_policy.delay_seconds * (
                step.retry_policy.backoff_multiplier ** (step.retry_count - 1)
            )
            return ReviewResult(
                verdict=ReviewVerdict.RETRY,
                reason=f"Step failed (attempt {step.retry_count}/{max_retries}). Retrying in {delay:.1f}s.",
                suggestions=[f"Retry with backoff delay={delay:.1f}"],
            )
        return ReviewResult(
            verdict=ReviewVerdict.REPLAN,
            reason=f"Step failed after {max_retries} retries. Replanning required.",
        )
