"""Schedule persistence — in-memory persistence for scheduler state."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.scheduler.base import SchedulePersistence
from app.scheduler.schemas import ExecutionRecord, Job, JobStatus

logger = logging.getLogger(__name__)


class InMemorySchedulePersistence(SchedulePersistence):
    """In-memory persistence store for jobs and execution records."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._executions: dict[str, list[ExecutionRecord]] = {}
        self._execution_records: list[ExecutionRecord] = []

    async def store_job(self, job: Job) -> None:
        self._jobs[job.job_id] = job
        logger.debug("Stored job %s", job.job_id)

    async def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def update_job(self, job: Job) -> None:
        self._jobs[job.job_id] = job
        logger.debug("Updated job %s", job.job_id)

    async def delete_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            self._executions.pop(job_id, None)
            logger.debug("Deleted job %s", job_id)
            return True
        return False

    async def list_jobs(self, status: JobStatus | None = None, limit: int = 100, offset: int = 0) -> list[Job]:
        jobs = list(self._jobs.values())
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[offset:offset + limit]

    async def count_jobs(self, status: JobStatus | None = None) -> int:
        if status is None:
            return len(self._jobs)
        return sum(1 for j in self._jobs.values() if j.status == status)

    async def store_execution(self, record: ExecutionRecord) -> None:
        self._execution_records.append(record)
        self._executions.setdefault(record.job_id, []).append(record)
        logger.debug("Stored execution %s for job %s", record.execution_id, record.job_id)

    async def list_executions(self, job_id: str, limit: int = 100) -> list[ExecutionRecord]:
        return self._executions.get(job_id, [])[:limit]

    async def clear(self) -> int:
        count = len(self._jobs)
        self._jobs.clear()
        self._executions.clear()
        self._execution_records.clear()
        return count
