"""Job repository — repository implementation backed by persistence layer."""

from __future__ import annotations

import logging
from typing import Optional

from app.scheduler.base import JobRepository, SchedulePersistence
from app.scheduler.schemas import Job, JobStatus

logger = logging.getLogger(__name__)


class InMemoryJobRepository(JobRepository):
    """In-memory job repository backed by a persistence store."""

    def __init__(self, persistence: SchedulePersistence | None = None) -> None:
        self._persistence = persistence
        self._fallback: dict[str, Job] = {}

    async def save(self, job: Job) -> Job:
        if self._persistence:
            await self._persistence.store_job(job)
        else:
            self._fallback[job.job_id] = job
        logger.debug("Saved job %s", job.job_id)
        return job

    async def get(self, job_id: str) -> Job | None:
        if self._persistence:
            return await self._persistence.get_job(job_id)
        return self._fallback.get(job_id)

    async def list(self, status: JobStatus | None = None, limit: int = 100, offset: int = 0) -> list[Job]:
        if self._persistence:
            return await self._persistence.list_jobs(status=status, limit=limit, offset=offset)
        jobs = list(self._fallback.values())
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        return jobs[offset:offset + limit]

    async def update(self, job: Job) -> Job:
        if self._persistence:
            await self._persistence.update_job(job)
        else:
            self._fallback[job.job_id] = job
        logger.debug("Updated job %s", job.job_id)
        return job

    async def delete(self, job_id: str) -> bool:
        if self._persistence:
            return await self._persistence.delete_job(job_id)
        if job_id in self._fallback:
            del self._fallback[job_id]
            return True
        return False

    async def count(self, status: JobStatus | None = None) -> int:
        if self._persistence:
            return await self._persistence.count_jobs(status=status)
        if status is None:
            return len(self._fallback)
        return sum(1 for j in self._fallback.values() if j.status == status)
