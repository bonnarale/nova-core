"""Scheduler engine — core engine implementing SchedulerEngine ABC."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.scheduler.base import JobRepository, TriggerStrategy
from app.scheduler.executor import InMemoryJobExecutor
from app.scheduler.lifecycle import SchedulerLifecycle
from app.scheduler.metrics import SchedulerMetrics, get_scheduler_metrics
from app.scheduler.queue import JobQueue
from app.scheduler.schemas import (
    ExecutionRecord,
    ExecutionStatus,
    Job,
    JobStatus,
    SchedulerLifecycleState,
    TriggerType,
)
from app.scheduler.tracing import SchedulerTracer
from app.scheduler.trigger import DEFAULT_STRATEGIES

logger = logging.getLogger(__name__)


class InMemorySchedulerEngine:
    """In-memory scheduler engine — core scheduling logic."""

    def __init__(
        self,
        repository: JobRepository,
        queue: JobQueue,
        executor: InMemoryJobExecutor,
        metrics: SchedulerMetrics | None = None,
        tracer: SchedulerTracer | None = None,
        lifecycle: SchedulerLifecycle | None = None,
    ) -> None:
        self._repository = repository
        self._queue = queue
        self._executor = executor
        self._metrics = metrics or get_scheduler_metrics()
        self._tracer = tracer or SchedulerTracer()
        self._lifecycle = lifecycle or SchedulerLifecycle()
        self._triggers: dict[TriggerType, TriggerStrategy] = dict(DEFAULT_STRATEGIES)

    @property
    def lifecycle(self) -> SchedulerLifecycle:
        return self._lifecycle

    @property
    def repository(self) -> JobRepository:
        return self._repository

    @property
    def queue(self) -> JobQueue:
        return self._queue

    def register_trigger(self, trigger_type: TriggerType, strategy: TriggerStrategy) -> None:
        self._triggers[trigger_type] = strategy

    async def schedule_job(self, job: Job) -> Job:
        span = self._tracer.start_span("schedule_job")
        span.set_attribute("job_id", job.job_id)
        span.set_attribute("job_type", job.job_type.value)
        try:
            trigger_strategy = self._triggers.get(job.trigger.trigger_type)
            if trigger_strategy:
                next_run = await trigger_strategy.next_run_time(job.trigger, job.last_run)
                if next_run:
                    job.next_run = next_run
            job.status = JobStatus.SCHEDULED
            job.updated_at = datetime.now(timezone.utc)
            await self._repository.save(job)
            await self._queue.enqueue(job)
            self._metrics.record_scheduled()
            self._tracer.end_span(span)
            logger.info("Scheduled job %s (type=%s)", job.job_id, job.job_type.value)
            return job
        except Exception as e:
            span.set_error(str(e))
            self._tracer.end_span(span)
            raise

    async def execute_job(self, job_id: str) -> Any:
        span = self._tracer.start_span("execute_job")
        span.set_attribute("job_id", job_id)
        try:
            job = await self._repository.get(job_id)
            if not job:
                span.set_error("Job not found")
                self._tracer.end_span(span)
                raise ValueError(f"Job not found: {job_id}")
            job.status = JobStatus.RUNNING
            job.last_run = datetime.now(timezone.utc)
            await self._repository.update(job)
            result = await self._executor.execute(job)
            job.status = JobStatus.COMPLETED
            job.updated_at = datetime.now(timezone.utc)
            await self._repository.update(job)
            self._metrics.record_executed(0.0)
            self._tracer.end_span(span)
            return result
        except Exception as e:
            span.set_error(str(e))
            self._tracer.end_span(span)
            raise

    async def cancel_job(self, job_id: str) -> bool:
        span = self._tracer.start_span("cancel_job")
        span.set_attribute("job_id", job_id)
        try:
            job = await self._repository.get(job_id)
            if not job:
                self._tracer.end_span(span)
                return False
            job.status = JobStatus.CANCELLED
            job.updated_at = datetime.now(timezone.utc)
            await self._repository.update(job)
            await self._queue.remove(job_id)
            self._metrics.record_cancelled()
            self._tracer.end_span(span)
            logger.info("Cancelled job %s", job_id)
            return True
        except Exception as e:
            span.set_error(str(e))
            self._tracer.end_span(span)
            return False

    async def pause_job(self, job_id: str) -> bool:
        job = await self._repository.get(job_id)
        if not job:
            return False
        if job.status not in (JobStatus.SCHEDULED, JobStatus.PENDING):
            return False
        job.status = JobStatus.PAUSED
        job.updated_at = datetime.now(timezone.utc)
        await self._repository.update(job)
        await self._queue.remove(job_id)
        logger.info("Paused job %s", job_id)
        return True

    async def resume_job(self, job_id: str) -> bool:
        job = await self._repository.get(job_id)
        if not job:
            return False
        if job.status != JobStatus.PAUSED:
            return False
        job.status = JobStatus.SCHEDULED
        job.updated_at = datetime.now(timezone.utc)
        trigger_strategy = self._triggers.get(job.trigger.trigger_type)
        if trigger_strategy:
            next_run = await trigger_strategy.next_run_time(job.trigger, job.last_run)
            if next_run:
                job.next_run = next_run
        await self._repository.update(job)
        await self._queue.enqueue(job)
        logger.info("Resumed job %s", job_id)
        return True

    async def retry_job(self, job_id: str) -> bool:
        job = await self._repository.get(job_id)
        if not job:
            return False
        if job.status != JobStatus.FAILED:
            return False
        if job.retries >= job.max_retries:
            return False
        job.retries += 1
        job.status = JobStatus.RETRYING
        job.updated_at = datetime.now(timezone.utc)
        await self._repository.update(job)
        await self._queue.enqueue(job)
        self._metrics.record_retry()
        logger.info("Retrying job %s (attempt %d/%d)", job_id, job.retries, job.max_retries)
        return True

    async def delete_job(self, job_id: str) -> bool:
        job = await self._repository.get(job_id)
        if not job:
            return False
        if job.status == JobStatus.RUNNING:
            await self._executor.cancel(job_id)
        await self._queue.remove(job_id)
        deleted = await self._repository.delete(job_id)
        logger.info("Deleted job %s", job_id)
        return deleted

    async def list_jobs(self, status: JobStatus | None = None, limit: int = 100, offset: int = 0) -> list[Job]:
        return await self._repository.list(status=status, limit=limit, offset=offset)

    async def get_job(self, job_id: str) -> Job | None:
        return await self._repository.get(job_id)

    async def run_pending(self) -> int:
        span = self._tracer.start_span("run_pending")
        executed = 0
        try:
            jobs = await self._repository.list(status=JobStatus.SCHEDULED)
            now = datetime.now(timezone.utc)
            for job in jobs:
                if job.next_run and job.next_run <= now:
                    try:
                        await self.execute_job(job.job_id)
                        executed += 1
                    except Exception as e:
                        logger.error("Failed to execute job %s: %s", job.job_id, e)
                        if job.retries < job.max_retries:
                            await self.retry_job(job.job_id)
            self._tracer.end_span(span)
            return executed
        except Exception as e:
            span.set_error(str(e))
            self._tracer.end_span(span)
            return executed

    async def get_statistics(self) -> dict[str, int]:
        total = await self._repository.count()
        scheduled = await self._repository.count(JobStatus.SCHEDULED)
        running = await self._repository.count(JobStatus.RUNNING)
        completed = await self._repository.count(JobStatus.COMPLETED)
        failed = await self._repository.count(JobStatus.FAILED)
        cancelled = await self._repository.count(JobStatus.CANCELLED)
        pending = await self._repository.count(JobStatus.PENDING)
        paused = await self._repository.count(JobStatus.PAUSED)
        return {
            "total_jobs": total,
            "scheduled_jobs": scheduled,
            "running_jobs": running,
            "completed_jobs": completed,
            "failed_jobs": failed,
            "cancelled_jobs": cancelled,
            "pending_jobs": pending,
            "paused_jobs": paused,
        }
