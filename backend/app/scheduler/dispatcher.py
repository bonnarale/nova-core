"""Job dispatcher — dispatches jobs from the queue to the executor."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from app.scheduler.base import JobExecutor
from app.scheduler.queue import JobQueue
from app.scheduler.schemas import Job, JobStatus

logger = logging.getLogger(__name__)


class JobDispatcher:
    """Dispatches jobs from queue to executor with concurrency control."""

    def __init__(self, queue: JobQueue, executor: JobExecutor, max_concurrency: int = 10) -> None:
        self._queue = queue
        self._executor = executor
        self._max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._active_tasks: dict[str, asyncio.Task[Any]] = {}
        self._running = False

    @property
    def active_count(self) -> int:
        return len(self._active_tasks)

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        self._running = True
        logger.info("JobDispatcher started (max_concurrency=%d)", self._max_concurrency)

    async def stop(self) -> None:
        self._running = False
        for task in self._active_tasks.values():
            task.cancel()
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks.values(), return_exceptions=True)
        self._active_tasks.clear()
        logger.info("JobDispatcher stopped")

    async def dispatch(self, job: Job) -> Any:
        if not self._running:
            logger.warning("Dispatcher not running, executing job %s directly", job.job_id)
            return await self._executor.execute(job)

        task = asyncio.create_task(self._dispatch_with_semaphore(job))
        self._active_tasks[job.job_id] = task
        task.add_done_callback(lambda t, jid=job.job_id: self._active_tasks.pop(jid, None))
        return task

    async def _dispatch_with_semaphore(self, job: Job) -> Any:
        async with self._semaphore:
            try:
                job.status = JobStatus.RUNNING
                result = await self._executor.execute(job)
                job.status = JobStatus.COMPLETED
                logger.info("Job %s dispatched and completed", job.job_id)
                return result
            except asyncio.CancelledError:
                job.status = JobStatus.CANCELLED
                logger.info("Job %s dispatch cancelled", job.job_id)
                raise
            except Exception as e:
                job.status = JobStatus.FAILED
                logger.error("Job %s dispatch failed: %s", job.job_id, e)
                raise

    async def cancel(self, job_id: str) -> bool:
        task = self._active_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            logger.info("Cancelled dispatch for job %s", job_id)
            return True
        return False

    async def get_active_jobs(self) -> list[str]:
        return [jid for jid, t in self._active_tasks.items() if not t.done()]
