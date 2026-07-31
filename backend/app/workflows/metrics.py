"""Workflow metrics — singleton metrics tracker for workflow operations."""

from __future__ import annotations

import threading
import time
from typing import Any


class WorkflowMetrics:
    """Thread-safe singleton tracking workflow metrics."""

    _instance: WorkflowMetrics | None = None
    _lock = threading.Lock()

    def __new__(cls) -> WorkflowMetrics:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._workflows_created = 0
        self._workflows_executed = 0
        self._successful_executions = 0
        self._failed_executions = 0
        self._node_execution_count = 0
        self._execution_times: list[float] = []
        self._retry_count = 0
        self._rollback_count = 0
        self._started_at = time.monotonic()

    def record_created(self) -> None:
        self._workflows_created += 1

    def record_executed(self, duration_ms: float) -> None:
        self._workflows_executed += 1
        self._execution_times.append(duration_ms)

    def record_success(self) -> None:
        self._successful_executions += 1

    def record_failure(self) -> None:
        self._failed_executions += 1

    def record_node_execution(self) -> None:
        self._node_execution_count += 1

    def record_retry(self) -> None:
        self._retry_count += 1

    def record_rollback(self) -> None:
        self._rollback_count += 1

    @property
    def workflows_created(self) -> int:
        return self._workflows_created

    @property
    def workflows_executed(self) -> int:
        return self._workflows_executed

    @property
    def successful_executions(self) -> int:
        return self._successful_executions

    @property
    def failed_executions(self) -> int:
        return self._failed_executions

    @property
    def node_execution_count(self) -> int:
        return self._node_execution_count

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @property
    def rollback_count(self) -> int:
        return self._rollback_count

    @property
    def average_execution_time_ms(self) -> float:
        if not self._execution_times:
            return 0.0
        return sum(self._execution_times) / len(self._execution_times)

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflows_created": self._workflows_created,
            "workflows_executed": self._workflows_executed,
            "successful_executions": self._successful_executions,
            "failed_executions": self._failed_executions,
            "node_execution_count": self._node_execution_count,
            "average_execution_time_ms": self.average_execution_time_ms,
            "retry_count": self._retry_count,
            "rollback_count": self._rollback_count,
        }

    def reset(self) -> None:
        self._workflows_created = 0
        self._workflows_executed = 0
        self._successful_executions = 0
        self._failed_executions = 0
        self._node_execution_count = 0
        self._execution_times.clear()
        self._retry_count = 0
        self._rollback_count = 0
        self._started_at = time.monotonic()

    @classmethod
    def reset_singleton(cls) -> None:
        with cls._lock:
            cls._instance = None


def get_workflow_metrics() -> WorkflowMetrics:
    return WorkflowMetrics()
