"""Scheduler facade — high-level scheduler interface."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.scheduler.base import JobExecutor
from app.scheduler.engine import InMemorySchedulerEngine
from app.scheduler.lifecycle import SchedulerLifecycle
from app.scheduler.metrics import SchedulerMetrics, get_scheduler_metrics
from app.scheduler.persistence import InMemorySchedulePersistence
from app.scheduler.queue import JobQueue
from app.scheduler.repository import InMemoryJobRepository
from app.scheduler.schemas import (
    CreateJobRequest,
    ExecutionRecord,
    Job,
    JobPriority,
    JobStatus,
    JobType,
    SchedulerLifecycleState,
    SchedulerMetricsResponse,
    SchedulerTracesResponse,
    UpdateJobRequest,
)
from app.scheduler.tracing import SchedulerTracer

logger = logging.getLogger(__name__)


class Scheduler:
    """High-level scheduler facade — integrates engine, queue, persistence, metrics, tracing."""

    def __init__(
        self,
        engine: InMemorySchedulerEngine | None = None,
        persistence: InMemorySchedulePersistence | None = None,
        repository: InMemoryJobRepository | None = None,
        queue: JobQueue | None = None,
        metrics: SchedulerMetrics | None = None,
        tracer: SchedulerTracer | None = None,
        lifecycle: SchedulerLifecycle | None = None,
    ) -> None:
        self._lifecycle = lifecycle or SchedulerLifecycle()
        self._persistence = persistence or InMemorySchedulePersistence()
        self._repository = repository or InMemoryJobRepository(self._persistence)
        self._queue = queue or JobQueue()
        self._metrics = metrics or get_scheduler_metrics()
        self._tracer = tracer or SchedulerTracer()
        executor: JobExecutor = __import__("app.scheduler.executor", fromlist=["InMemoryJobExecutor"]).InMemoryJobExecutor()
        self._engine = engine or InMemorySchedulerEngine(
            repository=self._repository,
            queue=self._queue,
            executor=executor,  # type: ignore[arg-type]
            metrics=self._metrics,
            tracer=self._tracer,
            lifecycle=self._lifecycle,
        )
        self._lifecycle.transition(SchedulerLifecycleState.INITIALIZED)

    @property
    def engine(self) -> InMemorySchedulerEngine:
        return self._engine

    @property
    def lifecycle(self) -> SchedulerLifecycle:
        return self._lifecycle

    @property
    def queue(self) -> JobQueue:
        return self._queue

    @property
    def metrics(self) -> SchedulerMetrics:
        return self._metrics

    @property
    def tracer(self) -> SchedulerTracer:
        return self._tracer

    async def start(self) -> None:
        self._lifecycle.transition(SchedulerLifecycleState.READY)
        self._lifecycle.transition(SchedulerLifecycleState.RUNNING)
        logger.info("Scheduler started")

    async def stop(self) -> None:
        self._lifecycle.transition(SchedulerLifecycleState.STOPPED)
        logger.info("Scheduler stopped")

    async def shutdown(self) -> None:
        self._lifecycle.transition(SchedulerLifecycleState.SHUTDOWN)
        logger.info("Scheduler shut down")

    def is_running(self) -> bool:
        return self._lifecycle.state == SchedulerLifecycleState.RUNNING

    async def schedule_job(self, request: CreateJobRequest) -> Job:
        job = Job(
            name=request.name,
            description=request.description,
            job_type=request.job_type,
            trigger=request.trigger,
            payload=request.payload,
            assigned_agent=request.assigned_agent,
            priority=request.priority,
            max_retries=request.max_retries,
            timeout=request.timeout,
            metadata=request.metadata,
        )
        return await self._engine.schedule_job(job)

    async def schedule(self, job: Job) -> Job:
        return await self._engine.schedule_job(job)

    async def execute_job(self, job_id: str) -> Any:
        return await self._engine.execute_job(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        return await self._engine.cancel_job(job_id)

    async def pause_job(self, job_id: str) -> bool:
        return await self._engine.pause_job(job_id)

    async def resume_job(self, job_id: str) -> bool:
        return await self._engine.resume_job(job_id)

    async def retry_job(self, job_id: str) -> bool:
        return await self._engine.retry_job(job_id)

    async def delete_job(self, job_id: str) -> bool:
        return await self._engine.delete_job(job_id)

    async def list_jobs(self, status: JobStatus | None = None, limit: int = 100, offset: int = 0) -> list[Job]:
        return await self._engine.list_jobs(status=status, limit=limit, offset=offset)

    async def get_job(self, job_id: str) -> Job | None:
        return await self._engine.get_job(job_id)

    async def run_pending(self) -> int:
        return await self._engine.run_pending()

    async def get_statistics(self) -> dict[str, int]:
        return await self._engine.get_statistics()

    def get_metrics_response(self) -> SchedulerMetricsResponse:
        return self._metrics.to_response(queue_length=self._queue.length)

    def get_traces_response(self, limit: int = 100) -> SchedulerTracesResponse:
        return self._tracer.to_response(limit=limit)
