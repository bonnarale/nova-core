"""Tool execution policies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class ToolPolicyType(str, Enum):
    IMMEDIATE = "immediate"
    BACKGROUND = "background"
    RETRYABLE = "retryable"
    EXCLUSIVE = "exclusive"
    PARALLEL = "parallel"
    IDEMPOTENT = "idempotent"


class ToolExecutionPolicy(ABC):
    """Strategy for how a tool execution should be scheduled."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def can_run_concurrently(self) -> bool: ...

    @abstractmethod
    def should_retry_on_failure(self) -> bool: ...

    @abstractmethod
    def is_idempotent(self) -> bool: ...

    @abstractmethod
    def should_run_in_background(self) -> bool: ...

    @property
    def max_retries(self) -> int:
        return 0

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name}


class ImmediatePolicy(ToolExecutionPolicy):
    @property
    def name(self) -> str:
        return ToolPolicyType.IMMEDIATE.value

    def can_run_concurrently(self) -> bool:
        return True

    def should_retry_on_failure(self) -> bool:
        return False

    def is_idempotent(self) -> bool:
        return False

    def should_run_in_background(self) -> bool:
        return False


class BackgroundPolicy(ToolExecutionPolicy):
    @property
    def name(self) -> str:
        return ToolPolicyType.BACKGROUND.value

    def can_run_concurrently(self) -> bool:
        return True

    def should_retry_on_failure(self) -> bool:
        return True

    def is_idempotent(self) -> bool:
        return False

    def should_run_in_background(self) -> bool:
        return True


class RetryablePolicy(ToolExecutionPolicy):
    def __init__(self, max_retries: int = 3) -> None:
        self._max_retries = max_retries

    @property
    def name(self) -> str:
        return ToolPolicyType.RETRYABLE.value

    def can_run_concurrently(self) -> bool:
        return True

    def should_retry_on_failure(self) -> bool:
        return True

    def is_idempotent(self) -> bool:
        return True

    def should_run_in_background(self) -> bool:
        return False

    @property
    def max_retries(self) -> int:
        return self._max_retries


class ExclusivePolicy(ToolExecutionPolicy):
    @property
    def name(self) -> str:
        return ToolPolicyType.EXCLUSIVE.value

    def can_run_concurrently(self) -> bool:
        return False

    def should_retry_on_failure(self) -> bool:
        return False

    def is_idempotent(self) -> bool:
        return False

    def should_run_in_background(self) -> bool:
        return False


class ParallelPolicy(ToolExecutionPolicy):
    @property
    def name(self) -> str:
        return ToolPolicyType.PARALLEL.value

    def can_run_concurrently(self) -> bool:
        return True

    def should_retry_on_failure(self) -> bool:
        return False

    def is_idempotent(self) -> bool:
        return False

    def should_run_in_background(self) -> bool:
        return False


class IdempotentPolicy(ToolExecutionPolicy):
    @property
    def name(self) -> str:
        return ToolPolicyType.IDEMPOTENT.value

    def can_run_concurrently(self) -> bool:
        return True

    def should_retry_on_failure(self) -> bool:
        return True

    def is_idempotent(self) -> bool:
        return True

    def should_run_in_background(self) -> bool:
        return False


TOOL_POLICY_REGISTRY: dict[str, type[ToolExecutionPolicy]] = {
    ToolPolicyType.IMMEDIATE.value: ImmediatePolicy,
    ToolPolicyType.BACKGROUND.value: BackgroundPolicy,
    ToolPolicyType.RETRYABLE.value: RetryablePolicy,
    ToolPolicyType.EXCLUSIVE.value: ExclusivePolicy,
    ToolPolicyType.PARALLEL.value: ParallelPolicy,
    ToolPolicyType.IDEMPOTENT.value: IdempotentPolicy,
}


def get_tool_policy(name: str, **kwargs: Any) -> ToolExecutionPolicy:
    cls = TOOL_POLICY_REGISTRY.get(name.lower())
    if cls is None:
        raise ValueError(f"Unknown tool policy: {name}")
    try:
        return cls(**kwargs)
    except TypeError:
        return cls()


def list_tool_policies() -> list[str]:
    return list(TOOL_POLICY_REGISTRY.keys())
