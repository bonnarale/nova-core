"""Execution policies for agent task dispatch."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum


class PolicyType(str, Enum):
    IMMEDIATE = "immediate"
    BACKGROUND = "background"
    EXCLUSIVE = "exclusive"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    RETRYABLE = "retryable"
    IDEMPOTENT = "idempotent"


class ExecutionPolicy(ABC):
    """Strategy for how a task should be scheduled and executed."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def can_run_concurrently(self) -> bool:
        ...

    @abstractmethod
    def should_retry_on_failure(self) -> bool:
        ...

    @abstractmethod
    def is_idempotent(self) -> bool:
        ...

    @abstractmethod
    def should_run_in_background(self) -> bool:
        ...

    def to_dict(self) -> dict:
        return {"name": self.name}


class ImmediatePolicy(ExecutionPolicy):
    """Execute immediately when dispatched. No queuing."""

    @property
    def name(self) -> str:
        return PolicyType.IMMEDIATE.value

    def can_run_concurrently(self) -> bool:
        return True

    def should_retry_on_failure(self) -> bool:
        return False

    def is_idempotent(self) -> bool:
        return False

    def should_run_in_background(self) -> bool:
        return False


class BackgroundPolicy(ExecutionPolicy):
    """Execute in background without blocking the caller."""

    @property
    def name(self) -> str:
        return PolicyType.BACKGROUND.value

    def can_run_concurrently(self) -> bool:
        return True

    def should_retry_on_failure(self) -> bool:
        return True

    def is_idempotent(self) -> bool:
        return False

    def should_run_in_background(self) -> bool:
        return True


class ExclusivePolicy(ExecutionPolicy):
    """Only one task of this policy can run at a time per agent."""

    @property
    def name(self) -> str:
        return PolicyType.EXCLUSIVE.value

    def can_run_concurrently(self) -> bool:
        return False

    def should_retry_on_failure(self) -> bool:
        return False

    def is_idempotent(self) -> bool:
        return False

    def should_run_in_background(self) -> bool:
        return False


class ParallelPolicy(ExecutionPolicy):
    """Allow unlimited concurrency."""

    @property
    def name(self) -> str:
        return PolicyType.PARALLEL.value

    def can_run_concurrently(self) -> bool:
        return True

    def should_retry_on_failure(self) -> bool:
        return False

    def is_idempotent(self) -> bool:
        return False

    def should_run_in_background(self) -> bool:
        return False


class SequentialPolicy(ExecutionPolicy):
    """Execute one at a time in FIFO order."""

    @property
    def name(self) -> str:
        return PolicyType.SEQUENTIAL.value

    def can_run_concurrently(self) -> bool:
        return False

    def should_retry_on_failure(self) -> bool:
        return False

    def is_idempotent(self) -> bool:
        return False

    def should_run_in_background(self) -> bool:
        return False


class RetryablePolicy(ExecutionPolicy):
    """Retries on failure with exponential backoff."""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.0) -> None:
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor

    @property
    def name(self) -> str:
        return PolicyType.RETRYABLE.value

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

    @property
    def backoff_factor(self) -> float:
        return self._backoff_factor


class IdempotentPolicy(ExecutionPolicy):
    """Safe to re-execute with the same inputs; produces the same result."""

    @property
    def name(self) -> str:
        return PolicyType.IDEMPOTENT.value

    def can_run_concurrently(self) -> bool:
        return True

    def should_retry_on_failure(self) -> bool:
        return True

    def is_idempotent(self) -> bool:
        return True

    def should_run_in_background(self) -> bool:
        return False


POLICY_REGISTRY: dict[str, type[ExecutionPolicy]] = {
    PolicyType.IMMEDIATE.value: ImmediatePolicy,
    PolicyType.BACKGROUND.value: BackgroundPolicy,
    PolicyType.EXCLUSIVE.value: ExclusivePolicy,
    PolicyType.PARALLEL.value: ParallelPolicy,
    PolicyType.SEQUENTIAL.value: SequentialPolicy,
    PolicyType.RETRYABLE.value: RetryablePolicy,
    PolicyType.IDEMPOTENT.value: IdempotentPolicy,
}


def get_policy(name: str, **kwargs: Any) -> ExecutionPolicy:
    cls = POLICY_REGISTRY.get(name.lower())
    if cls is None:
        raise ValueError(f"Unknown execution policy: {name}")
    try:
        return cls(**kwargs)
    except TypeError:
        return cls()


def list_policies() -> list[str]:
    return list(POLICY_REGISTRY.keys())
