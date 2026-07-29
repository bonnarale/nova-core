"""Job executor — executes scheduled jobs with timeout, retry, and metrics support."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, Optional

from app.scheduler.base import JobExecutor as JobExecutorABC
from app.scheduler.schemas import ExecutionRecord, ExecutionStatus, Job, JobStatus

logger = logging.getLogger(__name__)

JobCallable = Callable[[Job], Coroutine[Any, Any, Any]]


class InMemoryJobExecutor(JobExecutorABC):
    """In-memory executor that runs job callables with timeout and retry."""

    def __init__(self) -> None:
        self._handlers: dict[str, JobCallable] = {}
        self._running: dict[str, asyncio.Task[Any]] = {}
        self._records: dict[str, list[ExecutionRecord]] = {}
        self._default_handler: Optional[JobCallable] = None

    def register_handler(self, job_name: str, handler: JobCallable) -> None:
        self._handlers[job_name] = handler
        logger.debug("Registered handler for job type: %s", job_name)

    def set_default_handler(self, handler: JobCallable) -> None:
        self._default_handler = handler

    async def execute(self, job: Job) -> Any:
        handler = self._handlers.get(job.name) or self._default_handler
        if handler is None:
            raise ValueError(f"No handler registered for job: {job.name}")

        record = ExecutionRecord(job_id=job.job_id, status=ExecutionStatus.RUNNING)
        record.started_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        self._records.setdefault(job.job_id, []).append(record)

        start_time = time.monotonic()
        try:
            result = await asyncio.wait_for(handler(job), timeout=job.timeout) if job.timeout else await handler(job)
            record.status = ExecutionStatus.SUCCESS
            record.result = result
            job.status = JobStatus.COMPLETED
            logger.info("Job %s executed successfully", job.job_id)
            return result
        except asyncio.TimeoutError:
            record.status = ExecutionStatus.TIMEOUT
            record.error = "Job timed out"
            job.status = JobStatus.FAILED
            logger.warning("Job %s timed out after %ds", job.job_id, job.timeout)
            raise
        except asyncio.CancelledError:
            record.status = ExecutionStatus.CANCELLED
            job.status = JobStatus.CANCELLED
            raise
        except Exception as e:
            record.status = ExecutionStatus.FAILED
            record.error = str(e)
            job.status = JobStatus.FAILED
            logger.error("Job %s failed: %s", job.job_id, e)
            raise
        finally:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            record.duration_ms = elapsed_ms
            record.completed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    async def cancel(self, job_id: str) -> bool:
        task = self._running.get(job_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    async def get_status(self, job_id: str) -> JobStatus | None:
        records = self._records.get(job_id, [])
        if not records:
            return None
        last = records[-1]
        status_map = {
            ExecutionStatus.PENDING: JobStatus.PENDING,
            ExecutionStatus.RUNNING: JobStatus.RUNNING,
            ExecutionStatus.SUCCESS: JobStatus.COMPLETED,
            ExecutionStatus.FAILED: JobStatus.FAILED,
            ExecutionStatus.TIMEOUT: JobStatus.FAILED,
            ExecutionStatus.CANCELLED: JobStatus.CANCELLED,
        }
        return status_map.get(last.status)

    def get_records(self, job_id: str) -> list[ExecutionRecord]:
        return self._records.get(job_id, [])
