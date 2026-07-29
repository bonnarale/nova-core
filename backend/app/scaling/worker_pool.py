"""Worker pool with configurable size and priority queues."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from typing import Any

from app.scaling.base import WorkerPoolProvider
from app.scaling.enums import WorkerState
from app.scaling.models import WorkerInfo

logger = logging.getLogger(__name__)


class WorkerPool(WorkerPoolProvider):
    """Configurable worker pool with priority queues and graceful shutdown."""

    def __init__(self, pool_size: int = 4, max_queue_size: int = 100) -> None:
        self._pool_size = pool_size
        self._max_queue_size = max_queue_size
        self._lock = threading.Lock()
        self._workers: dict[str, WorkerInfo] = {}
        self._task_queue: asyncio.Queue[dict[str, Any]] | None = None
        self._running = False
        self._total_completed = 0
        self._total_failed = 0
        self._total_submitted = 0

    @property
    def pool_size(self) -> int:
        return self._pool_size

    async def start(self) -> None:
        self._task_queue = asyncio.Queue(maxsize=self._max_queue_size)
        self._running = True
        for i in range(self._pool_size):
            wid = f"worker-{i}"
            self._workers[wid] = WorkerInfo(worker_id=wid, state=WorkerState.IDLE.value)
        logger.info("Worker pool started with %d workers", self._pool_size)

    async def stop(self) -> None:
        self._running = False
        with self._lock:
            for w in self._workers.values():
                w.state = WorkerState.STOPPED.value
        logger.info("Worker pool stopped")

    async def add_worker(self, worker_id: str = "") -> str:
        wid = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._workers[wid] = WorkerInfo(worker_id=wid, state=WorkerState.IDLE.value)
            self._pool_size = len(self._workers)
        return wid

    async def remove_worker(self, worker_id: str) -> bool:
        with self._lock:
            if worker_id in self._workers:
                self._workers[worker_id].state = WorkerState.STOPPED.value
                del self._workers[worker_id]
                self._pool_size = len(self._workers)
                return True
            return False

    async def submit_task(self, task: dict[str, Any], priority: str = "normal") -> str:
        task_id = task.get("id", str(uuid.uuid4()))
        task_with_meta = {**task, "id": task_id, "priority": priority, "submitted_at": time.time()}
        if self._task_queue is not None:
            try:
                self._task_queue.put_nowait(task_with_meta)
            except asyncio.QueueFull:
                raise RuntimeError("Task queue full")
        self._total_submitted += 1
        return task_id

    async def process_next(self) -> dict[str, Any] | None:
        if self._task_queue is None or self._task_queue.empty():
            return None
        try:
            task = self._task_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

        worker = self._get_idle_worker()
        if worker:
            worker.state = WorkerState.BUSY.value
            worker.current_task = task.get("id", "")
            worker.last_active = time.time()
        self._total_completed += 1
        if worker:
            worker.tasks_completed += 1
            worker.state = WorkerState.IDLE.value
            worker.current_task = ""
        return task

    async def get_status(self) -> dict[str, Any]:
        with self._lock:
            idle = sum(1 for w in self._workers.values() if w.state == WorkerState.IDLE.value)
            busy = sum(1 for w in self._workers.values() if w.state == WorkerState.BUSY.value)
            return {
                "pool_size": self._pool_size,
                "running": self._running,
                "idle_workers": idle,
                "busy_workers": busy,
                "queue_size": self._task_queue.qsize() if self._task_queue else 0,
                "total_completed": self._total_completed,
                "total_failed": self._total_failed,
                "total_submitted": self._total_submitted,
            }

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            idle = sum(1 for w in self._workers.values() if w.state == WorkerState.IDLE.value)
            busy = sum(1 for w in self._workers.values() if w.state == WorkerState.BUSY.value)
            return {
                "pool_size": self._pool_size,
                "running": self._running,
                "idle_workers": idle,
                "busy_workers": busy,
                "queue_size": self._task_queue.qsize() if self._task_queue else 0,
                "total_completed": self._total_completed,
                "total_failed": self._total_failed,
                "total_submitted": self._total_submitted,
            }

    def get_workers(self) -> list[dict[str, Any]]:
        with self._lock:
            return [w.to_dict() for w in self._workers.values()]

    def _get_idle_worker(self) -> WorkerInfo | None:
        with self._lock:
            for w in self._workers.values():
                if w.state == WorkerState.IDLE.value:
                    return w
        return None
