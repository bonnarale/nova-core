"""Plan and Step data models for the Autonomous Planner."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class PlanStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"


@dataclass
class RetryPolicy:
    max_retries: int = 2
    delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0


@dataclass
class ToolCall:
    tool_name: str
    params: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    success: bool | None = None
    error: str | None = None


@dataclass
class Step:
    id: str = ""
    plan_id: str = ""
    title: str = ""
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    assigned_agent: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    retry_count: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid4())


@dataclass
class Plan:
    id: str = ""
    objective: str = ""
    status: PlanStatus = PlanStatus.DRAFT
    steps: list[Step] = field(default_factory=list)
    user_id: str | None = None
    session_id: str | None = None
    goal_id: str | None = None
    created_at: str = ""
    updated_at: str = ""
    completed_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid4())
        if not self.created_at:
            self.created_at = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    @property
    def progress(self) -> float:
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status in (StepStatus.SUCCEEDED, StepStatus.SKIPPED))
        return (completed / len(self.steps)) * 100.0

    @property
    def active_step(self) -> Step | None:
        for s in self.steps:
            if s.status == StepStatus.RUNNING:
                return s
        return None

    @property
    def next_ready_steps(self) -> list[Step]:
        dep_ids = {s.id for s in self.steps if s.status == StepStatus.SUCCEEDED}
        return [
            s for s in self.steps
            if s.status == StepStatus.PENDING
            and all(d in dep_ids for d in s.dependencies)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "objective": self.objective,
            "status": self.status.value,
            "steps_count": len(self.steps),
            "progress": self.progress,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "goal_id": self.goal_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }
