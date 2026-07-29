"""Scheduler subsystem — Chapter 20: Scheduling, Triggers, and Job Management."""

from __future__ import annotations

from app.scheduler.base import (
    JobExecutor,
    JobRepository,
    SchedulePersistence,
    SchedulerEngine,
    SchedulerProvider,
    TriggerStrategy,
)
from app.scheduler.cron import CronExpression
from app.scheduler.dispatcher import JobDispatcher
from app.scheduler.engine import InMemorySchedulerEngine
from app.scheduler.executor import InMemoryJobExecutor
from app.scheduler.factory import SchedulerFactory
from app.scheduler.lifecycle import SchedulerLifecycle
from app.scheduler.metrics import SchedulerMetrics, get_scheduler_metrics
from app.scheduler.persistence import InMemorySchedulePersistence
from app.scheduler.queue import JobQueue
from app.scheduler.repository import InMemoryJobRepository
from app.scheduler.scheduler import Scheduler
from app.scheduler.schemas import (
    CreateJobRequest,
    ExecutionRecord,
    ExecutionStatus,
    Job,
    JobPriority,
    JobResponse,
    JobStatistics,
    JobStatus,
    JobType,
    JobsListResponse,
    SchedulerHealthResponse,
    SchedulerLifecycleState,
    SchedulerMetricsResponse,
    SchedulerTracesResponse,
    TriggerConfig,
    TriggerType,
    UpdateJobRequest,
)
from app.scheduler.tracing import SchedulerTracer, TraceSpan
from app.scheduler.trigger import (
    CronTriggerStrategy,
    DateTimeTriggerStrategy,
    DependencyTriggerStrategy,
    EventTriggerStrategy,
    IntervalTriggerStrategy,
    ManualTriggerStrategy,
)

__all__ = [
    "CreateJobRequest",
    "CronExpression",
    "CronTriggerStrategy",
    "DateTimeTriggerStrategy",
    "DependencyTriggerStrategy",
    "EventTriggerStrategy",
    "ExecutionRecord",
    "ExecutionStatus",
    "InMemoryJobExecutor",
    "InMemoryJobRepository",
    "InMemorySchedulePersistence",
    "InMemorySchedulerEngine",
    "IntervalTriggerStrategy",
    "Job",
    "JobDispatcher",
    "JobExecutor",
    "JobPriority",
    "JobRepository",
    "JobResponse",
    "JobStatistics",
    "JobStatus",
    "JobType",
    "JobsListResponse",
    "ManualTriggerStrategy",
    "SchedulePersistence",
    "Scheduler",
    "SchedulerEngine",
    "SchedulerFactory",
    "SchedulerHealthResponse",
    "SchedulerLifecycle",
    "SchedulerLifecycleState",
    "SchedulerMetrics",
    "SchedulerMetricsResponse",
    "SchedulerProvider",
    "SchedulerTracer",
    "SchedulerTracesResponse",
    "TraceSpan",
    "TriggerConfig",
    "TriggerStrategy",
    "TriggerType",
    "UpdateJobRequest",
    "get_scheduler_metrics",
]
