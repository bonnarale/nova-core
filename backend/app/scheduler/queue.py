"""Job queue — priority queue for pending scheduled jobs."""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from typing import Optional

from app.scheduler.schemas import Job, JobPriority, JobStatus

logger = logging.getLogger(__name__)

_PRIORITY_ORDER = {
    JobPriority.CRITICAL: 0,
    JobPriority.HIGH: 1,
    JobPriority.NORMAL: 2,
    JobPriority.LOW: 3,
}


class JobQueue:
    """Thread-safe in-memory priority queue for scheduled jobs."""

    def __init__(self) -> None:
        self._queue: OrderedDict[str, Job] = OrderedDict()
        self._lock = asyncio.Lock()

    @property
    def length(self) -> int:
        return len(self._queue)

    async def enqueue(self, job: Job) -> None:
        async with self._lock:
            self._queue[job.job_id] = job
            self._reindex()
            logger.debug("Enqueued job %s (priority=%s)", job.job_id, job.priority)

    async def dequeue(self) -> Optional[Job]:
        async with self._lock:
            if not self._queue:
                return None
            _, job = self._queue.popitem(last=False)
            logger.debug("Dequeued job %s", job.job_id)
            return job

    async def peek(self) -> Optional[Job]:
        async with self._lock:
            if not self._queue:
                return None
            _, job = next(iter(self._queue.items()))
            return job

    async def remove(self, job_id: str) -> bool:
        async with self._lock:
            if job_id in self._queue:
                del self._queue[job_id]
                logger.debug("Removed job %s from queue", job_id)
                return True
            return False

    async def contains(self, job_id: str) -> bool:
        async with self._lock:
            return job_id in self._queue

    async def clear(self) -> int:
        async with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count

    async def list_all(self) -> list[Job]:
        async with self._lock:
            return list(self._queue.values())

    def _reindex(self) -> None:
        sorted_items = sorted(self._queue.items(), key=lambda item: _PRIORITY_ORDER.get(item[1].priority, 2))
        self._queue = OrderedDict(sorted_items)
