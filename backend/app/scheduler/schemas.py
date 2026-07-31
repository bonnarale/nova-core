"""Scheduler schemas — Pydantic models for jobs, triggers, requests, and responses."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class JobType(str, Enum):
    ONE_TIME = "one_time"
    INTERVAL = "interval"
    CRON = "cron"
    DELAYED = "delayed"
    RECURRING = "recurring"
    EVENT_TRIGGERED = "event_triggered"
    MANUAL = "manual"


class JobStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TriggerType(str, Enum):
    CRON = "cron"
    INTERVAL = "interval"
    DATETIME = "datetime"
    EVENT = "event"
    DEPENDENCY = "dependency"
    CUSTOM = "custom"
    MANUAL = "manual"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class SchedulerLifecycleState(str, Enum):
    REGISTERED = "registered"
    INITIALIZED = "initialized"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    STOPPED = "stopped"
    SHUTDOWN = "shutdown"


class RetryPolicy(BaseModel):
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0


class TriggerConfig(BaseModel):
    trigger_type: TriggerType = TriggerType.MANUAL
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    run_at: Optional[datetime] = None
    event_type: Optional[str] = None
    dependency_job_ids: list[str] = Field(default_factory=list)
    custom_config: dict[str, Any] = Field(default_factory=dict)


class Job(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    job_type: JobType = JobType.MANUAL
    trigger: TriggerConfig = Field(default_factory=TriggerConfig)
    payload: dict[str, Any] = Field(default_factory=dict)
    assigned_agent: str = ""
    priority: JobPriority = JobPriority.NORMAL
    retries: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None
    status: JobStatus = JobStatus.PENDING
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionRecord(BaseModel):
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0


class CreateJobRequest(BaseModel):
    name: str = ""
    description: str = ""
    job_type: JobType = JobType.MANUAL
    trigger: TriggerConfig = Field(default_factory=TriggerConfig)
    payload: dict[str, Any] = Field(default_factory=dict)
    assigned_agent: str = ""
    priority: JobPriority = JobPriority.NORMAL
    max_retries: int = 3
    timeout: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateJobRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger: Optional[TriggerConfig] = None
    payload: Optional[dict[str, Any]] = None
    assigned_agent: Optional[str] = None
    priority: Optional[JobPriority] = None
    max_retries: Optional[int] = None
    timeout: Optional[int] = None
    metadata: Optional[dict[str, Any]] = None


class JobResponse(BaseModel):
    success: bool = True
    job_id: str = ""
    message: str = ""


class JobsListResponse(BaseModel):
    jobs: list[Job] = Field(default_factory=list)
    total: int = 0


class JobStatistics(BaseModel):
    total_jobs: int = 0
    scheduled_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    cancelled_jobs: int = 0
    pending_jobs: int = 0
    paused_jobs: int = 0


class SchedulerMetricsResponse(BaseModel):
    total_scheduled: int = 0
    total_executed: int = 0
    total_failed: int = 0
    total_cancelled: int = 0
    average_execution_time_ms: float = 0.0
    queue_length: int = 0
    retry_count: int = 0
    timeout_count: int = 0


class SchedulerHealthResponse(BaseModel):
    status: str = "ok"
    lifecycle_state: str = ""
    total_jobs: int = 0
    active_jobs: int = 0
    uptime_seconds: float = 0.0


class SchedulerTracesResponse(BaseModel):
    traces: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
