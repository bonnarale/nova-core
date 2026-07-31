"""Scheduler factory — creates and wires all scheduler components."""

from __future__ import annotations

import logging
from typing import Any

from app.scheduler.engine import InMemorySchedulerEngine
from app.scheduler.lifecycle import SchedulerLifecycle
from app.scheduler.metrics import SchedulerMetrics, get_scheduler_metrics
from app.scheduler.persistence import InMemorySchedulePersistence
from app.scheduler.queue import JobQueue
from app.scheduler.repository import InMemoryJobRepository
from app.scheduler.scheduler import Scheduler
from app.scheduler.tracing import SchedulerTracer

logger = logging.getLogger(__name__)


class SchedulerFactory:
    """Factory that creates all scheduler components and wires them together."""

    @staticmethod
    def create_scheduler() -> Scheduler:
        """Create a fully wired Scheduler instance."""
        persistence = InMemorySchedulePersistence()
        repository = InMemoryJobRepository(persistence)
        queue = JobQueue()
        metrics = get_scheduler_metrics()
        tracer = SchedulerTracer()
        lifecycle = SchedulerLifecycle()
        engine = InMemorySchedulerEngine(
            repository=repository,
            queue=queue,
            executor=__import__("app.scheduler.executor", fromlist=["InMemoryJobExecutor"]).InMemoryJobExecutor(),
            metrics=metrics,
            tracer=tracer,
            lifecycle=lifecycle,
        )
        scheduler = Scheduler(
            engine=engine,
            persistence=persistence,
            repository=repository,
            queue=queue,
            metrics=metrics,
            tracer=tracer,
            lifecycle=lifecycle,
        )
        logger.info("SchedulerFactory created scheduler")
        return scheduler

    @staticmethod
    def create_engine(
        repository: InMemoryJobRepository | None = None,
        queue: JobQueue | None = None,
        metrics: SchedulerMetrics | None = None,
        tracer: SchedulerTracer | None = None,
    ) -> InMemorySchedulerEngine:
        """Create an isolated engine for testing."""
        repo = repository or InMemoryJobRepository()
        q = queue or JobQueue()
        m = metrics or get_scheduler_metrics()
        t = tracer or SchedulerTracer()
        return InMemorySchedulerEngine(
            repository=repo,
            queue=q,
            executor=__import__("app.scheduler.executor", fromlist=["InMemoryJobExecutor"]).InMemoryJobExecutor(),
            metrics=m,
            tracer=t,
        )
