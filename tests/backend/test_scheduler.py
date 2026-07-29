"""Comprehensive tests for Chapter 20 — Scheduler subsystem."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

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
    RetryPolicy,
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
    CustomTriggerStrategy,
    DateTimeTriggerStrategy,
    DependencyTriggerStrategy,
    EventTriggerStrategy,
    IntervalTriggerStrategy,
    ManualTriggerStrategy,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_job(
    job_id: str = "job-1",
    name: str = "test-job",
    job_type: JobType = JobType.MANUAL,
    status: JobStatus = JobStatus.PENDING,
    trigger_type: TriggerType = TriggerType.MANUAL,
    priority: JobPriority = JobPriority.NORMAL,
    max_retries: int = 3,
    timeout: int | None = None,
    payload: dict[str, Any] | None = None,
) -> Job:
    return Job(
        job_id=job_id,
        name=name,
        job_type=job_type,
        status=status,
        trigger=TriggerConfig(trigger_type=trigger_type),
        priority=priority,
        max_retries=max_retries,
        timeout=timeout,
        payload=payload or {},
    )


# ===================================================================
# SECTION 1 — Schemas
# ===================================================================

class TestSchemas:
    def test_job_default_values(self) -> None:
        job = Job()
        assert job.job_id
        assert job.status == JobStatus.PENDING
        assert job.job_type == JobType.MANUAL
        assert job.priority == JobPriority.NORMAL
        assert job.max_retries == 3
        assert job.retries == 0
        assert job.created_at is not None
        assert job.updated_at is not None

    def test_job_custom_values(self) -> None:
        job = _make_job(job_id="custom", name="custom-job")
        assert job.job_id == "custom"
        assert job.name == "custom-job"

    def test_job_types(self) -> None:
        for jtype in JobType:
            job = Job(job_type=jtype)
            assert job.job_type == jtype

    def test_job_status_values(self) -> None:
        assert JobStatus.PENDING == "pending"
        assert JobStatus.SCHEDULED == "scheduled"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.PAUSED == "paused"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"
        assert JobStatus.RETRYING == "retrying"

    def test_trigger_config_defaults(self) -> None:
        tc = TriggerConfig()
        assert tc.trigger_type == TriggerType.MANUAL
        assert tc.cron_expression is None
        assert tc.interval_seconds is None
        assert tc.run_at is None
        assert tc.event_type is None
        assert tc.dependency_job_ids == []
        assert tc.custom_config == {}

    def test_trigger_config_cron(self) -> None:
        tc = TriggerConfig(trigger_type=TriggerType.CRON, cron_expression="* * * * *")
        assert tc.cron_expression == "* * * * *"

    def test_trigger_config_interval(self) -> None:
        tc = TriggerConfig(trigger_type=TriggerType.INTERVAL, interval_seconds=30)
        assert tc.interval_seconds == 30

    def test_execution_record_defaults(self) -> None:
        er = ExecutionRecord()
        assert er.execution_id
        assert er.status == ExecutionStatus.PENDING
        assert er.retry_count == 0

    def test_retry_policy_defaults(self) -> None:
        rp = RetryPolicy()
        assert rp.max_retries == 3
        assert rp.base_delay == 1.0
        assert rp.max_delay == 60.0
        assert rp.backoff_factor == 2.0

    def test_create_job_request(self) -> None:
        req = CreateJobRequest(name="test", job_type=JobType.CRON, trigger=TriggerConfig(trigger_type=TriggerType.CRON, cron_expression="0 * * * *"))
        assert req.name == "test"
        assert req.job_type == JobType.CRON

    def test_update_job_request(self) -> None:
        req = UpdateJobRequest(name="updated")
        assert req.name == "updated"
        assert req.description is None

    def test_job_response(self) -> None:
        resp = JobResponse(success=True, job_id="j1", message="done")
        assert resp.success is True
        assert resp.job_id == "j1"

    def test_jobs_list_response(self) -> None:
        resp = JobsListResponse(jobs=[_make_job()], total=1)
        assert len(resp.jobs) == 1
        assert resp.total == 1

    def test_job_statistics(self) -> None:
        s = JobStatistics(total_jobs=10, scheduled_jobs=3)
        assert s.total_jobs == 10
        assert s.scheduled_jobs == 3

    def test_scheduler_metrics_response(self) -> None:
        r = SchedulerMetricsResponse(total_scheduled=5, total_executed=3)
        assert r.total_scheduled == 5

    def test_scheduler_health_response(self) -> None:
        h = SchedulerHealthResponse(status="ok", lifecycle_state="running")
        assert h.status == "ok"

    def test_scheduler_traces_response(self) -> None:
        t = SchedulerTracesResponse(traces=[{"name": "test"}], total=1)
        assert t.total == 1

    def test_job_model_dump(self) -> None:
        job = _make_job()
        d = job.model_dump()
        assert "job_id" in d
        assert "status" in d
        assert "trigger" in d


# ===================================================================
# SECTION 2 — Cron Expression
# ===================================================================

class TestCronExpression:
    def test_valid_expression(self) -> None:
        expr = CronExpression("* * * * *")
        assert expr.raw == "* * * * *"

    def test_invalid_too_few_fields(self) -> None:
        with pytest.raises(ValueError, match="Invalid cron expression"):
            CronExpression("* * *")

    def test_invalid_too_many_fields(self) -> None:
        with pytest.raises(ValueError, match="Invalid cron expression"):
            CronExpression("* * * * * *")

    def test_matches_every_minute(self) -> None:
        expr = CronExpression("* * * * *")
        dt = datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)
        assert expr.matches(dt) is True

    def test_matches_specific_minute(self) -> None:
        expr = CronExpression("30 * * * *")
        dt_match = datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)
        dt_no_match = datetime(2026, 1, 1, 12, 31, tzinfo=timezone.utc)
        assert expr.matches(dt_match) is True
        assert expr.matches(dt_no_match) is False

    def test_matches_specific_hour(self) -> None:
        expr = CronExpression("0 14 * * *")
        dt_match = datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc)
        dt_no_match = datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc)
        assert expr.matches(dt_match) is True
        assert expr.matches(dt_no_match) is False

    def test_matches_day_of_week(self) -> None:
        expr = CronExpression("0 0 * * 0")
        dt = datetime(2026, 1, 4, 0, 0, tzinfo=timezone.utc)
        assert expr.matches(dt) is True

    def test_matches_step_field(self) -> None:
        expr = CronExpression("*/15 * * * *")
        assert expr.matches(datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)) is True
        assert expr.matches(datetime(2026, 1, 1, 0, 15, tzinfo=timezone.utc)) is True
        assert expr.matches(datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)) is False

    def test_matches_range_field(self) -> None:
        expr = CronExpression("0 9-17 * * *")
        assert expr.matches(datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)) is True
        assert expr.matches(datetime(2026, 1, 1, 17, 0, tzinfo=timezone.utc)) is True
        assert expr.matches(datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc)) is False

    def test_matches_comma_field(self) -> None:
        expr = CronExpression("0 0,12 * * *")
        assert expr.matches(datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)) is True
        assert expr.matches(datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)) is True
        assert expr.matches(datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)) is False

    def test_next_run(self) -> None:
        expr = CronExpression("0 * * * *")
        after = datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)
        nxt = expr.next_run(after)
        assert nxt is not None
        assert nxt > after
        assert nxt.minute == 0


# ===================================================================
# SECTION 3 — Queue
# ===================================================================

class TestJobQueue:
    @pytest.fixture
    def queue(self) -> JobQueue:
        return JobQueue()

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self, queue: JobQueue) -> None:
        job = _make_job(job_id="q1")
        await queue.enqueue(job)
        assert queue.length == 1
        dequeued = await queue.dequeue()
        assert dequeued is not None
        assert dequeued.job_id == "q1"
        assert queue.length == 0

    @pytest.mark.asyncio
    async def test_dequeue_empty(self, queue: JobQueue) -> None:
        result = await queue.dequeue()
        assert result is None

    @pytest.mark.asyncio
    async def test_peek(self, queue: JobQueue) -> None:
        job = _make_job(job_id="p1")
        await queue.enqueue(job)
        peeked = await queue.peek()
        assert peeked is not None
        assert peeked.job_id == "p1"
        assert queue.length == 1

    @pytest.mark.asyncio
    async def test_peek_empty(self, queue: JobQueue) -> None:
        result = await queue.peek()
        assert result is None

    @pytest.mark.asyncio
    async def test_remove(self, queue: JobQueue) -> None:
        job = _make_job(job_id="r1")
        await queue.enqueue(job)
        removed = await queue.remove("r1")
        assert removed is True
        assert queue.length == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent(self, queue: JobQueue) -> None:
        removed = await queue.remove("nope")
        assert removed is False

    @pytest.mark.asyncio
    async def test_contains(self, queue: JobQueue) -> None:
        job = _make_job(job_id="c1")
        await queue.enqueue(job)
        assert await queue.contains("c1") is True
        assert await queue.contains("nope") is False

    @pytest.mark.asyncio
    async def test_clear(self, queue: JobQueue) -> None:
        await queue.enqueue(_make_job(job_id="a"))
        await queue.enqueue(_make_job(job_id="b"))
        count = await queue.clear()
        assert count == 2
        assert queue.length == 0

    @pytest.mark.asyncio
    async def test_list_all(self, queue: JobQueue) -> None:
        await queue.enqueue(_make_job(job_id="a"))
        await queue.enqueue(_make_job(job_id="b"))
        jobs = await queue.list_all()
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_priority_ordering(self, queue: JobQueue) -> None:
        low = _make_job(job_id="low", priority=JobPriority.LOW)
        critical = _make_job(job_id="critical", priority=JobPriority.CRITICAL)
        normal = _make_job(job_id="normal", priority=JobPriority.NORMAL)
        high = _make_job(job_id="high", priority=JobPriority.HIGH)
        await queue.enqueue(low)
        await queue.enqueue(critical)
        await queue.enqueue(normal)
        await queue.enqueue(high)
        first = await queue.dequeue()
        assert first is not None
        assert first.job_id == "critical"
        second = await queue.dequeue()
        assert second is not None
        assert second.job_id == "high"


# ===================================================================
# SECTION 4 — Persistence
# ===================================================================

class TestInMemorySchedulePersistence:
    @pytest.fixture
    def persistence(self) -> InMemorySchedulePersistence:
        return InMemorySchedulePersistence()

    @pytest.mark.asyncio
    async def test_store_and_get(self, persistence: InMemorySchedulePersistence) -> None:
        job = _make_job()
        await persistence.store_job(job)
        got = await persistence.get_job(job.job_id)
        assert got is not None
        assert got.job_id == job.job_id

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, persistence: InMemorySchedulePersistence) -> None:
        got = await persistence.get_job("nope")
        assert got is None

    @pytest.mark.asyncio
    async def test_update(self, persistence: InMemorySchedulePersistence) -> None:
        job = _make_job()
        await persistence.store_job(job)
        job.name = "updated"
        await persistence.update_job(job)
        got = await persistence.get_job(job.job_id)
        assert got is not None
        assert got.name == "updated"

    @pytest.mark.asyncio
    async def test_delete(self, persistence: InMemorySchedulePersistence) -> None:
        job = _make_job()
        await persistence.store_job(job)
        deleted = await persistence.delete_job(job.job_id)
        assert deleted is True
        assert await persistence.get_job(job.job_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, persistence: InMemorySchedulePersistence) -> None:
        deleted = await persistence.delete_job("nope")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_jobs(self, persistence: InMemorySchedulePersistence) -> None:
        await persistence.store_job(_make_job(job_id="a"))
        await persistence.store_job(_make_job(job_id="b", status=JobStatus.SCHEDULED))
        all_jobs = await persistence.list_jobs()
        assert len(all_jobs) == 2
        scheduled = await persistence.list_jobs(status=JobStatus.SCHEDULED)
        assert len(scheduled) == 1

    @pytest.mark.asyncio
    async def test_list_jobs_pagination(self, persistence: InMemorySchedulePersistence) -> None:
        for i in range(5):
            await persistence.store_job(_make_job(job_id=f"j{i}"))
        page = await persistence.list_jobs(limit=2, offset=0)
        assert len(page) == 2
        page2 = await persistence.list_jobs(limit=2, offset=2)
        assert len(page2) == 2

    @pytest.mark.asyncio
    async def test_count_jobs(self, persistence: InMemorySchedulePersistence) -> None:
        await persistence.store_job(_make_job())
        assert await persistence.count_jobs() == 1
        assert await persistence.count_jobs(JobStatus.PENDING) == 1
        assert await persistence.count_jobs(JobStatus.SCHEDULED) == 0

    @pytest.mark.asyncio
    async def test_store_and_list_executions(self, persistence: InMemorySchedulePersistence) -> None:
        record = ExecutionRecord(job_id="j1", status=ExecutionStatus.SUCCESS)
        await persistence.store_execution(record)
        records = await persistence.list_executions("j1")
        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_clear(self, persistence: InMemorySchedulePersistence) -> None:
        await persistence.store_job(_make_job())
        count = await persistence.clear()
        assert count == 1
        assert await persistence.count_jobs() == 0


# ===================================================================
# SECTION 5 — Repository
# ===================================================================

class TestInMemoryJobRepository:
    @pytest.fixture
    def repo(self) -> InMemoryJobRepository:
        return InMemoryJobRepository()

    @pytest.mark.asyncio
    async def test_save_and_get(self, repo: InMemoryJobRepository) -> None:
        job = _make_job()
        await repo.save(job)
        got = await repo.get(job.job_id)
        assert got is not None

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, repo: InMemoryJobRepository) -> None:
        assert await repo.get("nope") is None

    @pytest.mark.asyncio
    async def test_list(self, repo: InMemoryJobRepository) -> None:
        await repo.save(_make_job(job_id="a"))
        await repo.save(_make_job(job_id="b"))
        jobs = await repo.list()
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_list_with_status(self, repo: InMemoryJobRepository) -> None:
        await repo.save(_make_job(job_id="a", status=JobStatus.PENDING))
        await repo.save(_make_job(job_id="b", status=JobStatus.SCHEDULED))
        pending = await repo.list(status=JobStatus.PENDING)
        assert len(pending) == 1

    @pytest.mark.asyncio
    async def test_update(self, repo: InMemoryJobRepository) -> None:
        job = _make_job()
        await repo.save(job)
        job.name = "updated"
        await repo.update(job)
        got = await repo.get(job.job_id)
        assert got is not None
        assert got.name == "updated"

    @pytest.mark.asyncio
    async def test_delete(self, repo: InMemoryJobRepository) -> None:
        job = _make_job()
        await repo.save(job)
        assert await repo.delete(job.job_id) is True
        assert await repo.get(job.job_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, repo: InMemoryJobRepository) -> None:
        assert await repo.delete("nope") is False

    @pytest.mark.asyncio
    async def test_count(self, repo: InMemoryJobRepository) -> None:
        await repo.save(_make_job())
        assert await repo.count() == 1
        assert await repo.count(JobStatus.PENDING) == 1
        assert await repo.count(JobStatus.SCHEDULED) == 0

    @pytest.mark.asyncio
    async def test_with_persistence(self) -> None:
        persistence = InMemorySchedulePersistence()
        repo = InMemoryJobRepository(persistence)
        job = _make_job()
        await repo.save(job)
        got = await repo.get(job.job_id)
        assert got is not None
        persisted = await persistence.get_job(job.job_id)
        assert persisted is not None


# ===================================================================
# SECTION 6 — Executor
# ===================================================================

class TestInMemoryJobExecutor:
    @pytest.fixture
    def executor(self) -> InMemoryJobExecutor:
        return InMemoryJobExecutor()

    @pytest.mark.asyncio
    async def test_execute_success(self, executor: InMemoryJobExecutor) -> None:
        async def handler(job: Job) -> str:
            return "done"

        executor.register_handler("test-job", handler)
        job = _make_job(name="test-job")
        result = await executor.execute(job)
        assert result == "done"
        assert job.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_no_handler(self, executor: InMemoryJobExecutor) -> None:
        job = _make_job(name="unknown")
        with pytest.raises(ValueError, match="No handler"):
            await executor.execute(job)

    @pytest.mark.asyncio
    async def test_execute_timeout(self, executor: InMemoryJobExecutor) -> None:
        async def slow_handler(job: Job) -> str:
            await asyncio.sleep(10)
            return "never"

        executor.register_handler("slow", slow_handler)
        job = _make_job(name="slow", timeout=1)
        with pytest.raises(asyncio.TimeoutError):
            await executor.execute(job)
        assert job.status == JobStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_failure(self, executor: InMemoryJobExecutor) -> None:
        async def failing_handler(job: Job) -> str:
            raise RuntimeError("boom")

        executor.register_handler("fail", failing_handler)
        job = _make_job(name="fail")
        with pytest.raises(RuntimeError, match="boom"):
            await executor.execute(job)
        assert job.status == JobStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_default_handler(self, executor: InMemoryJobExecutor) -> None:
        async def default_handler(job: Job) -> str:
            return "default"

        executor.set_default_handler(default_handler)
        job = _make_job(name="anything")
        result = await executor.execute(job)
        assert result == "default"

    @pytest.mark.asyncio
    async def test_get_status(self, executor: InMemoryJobExecutor) -> None:
        async def handler(job: Job) -> str:
            return "ok"

        executor.register_handler("test", handler)
        job = _make_job(name="test")
        await executor.execute(job)
        status = await executor.get_status(job.job_id)
        assert status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_records(self, executor: InMemoryJobExecutor) -> None:
        async def handler(job: Job) -> str:
            return "ok"

        executor.register_handler("test", handler)
        job = _make_job(name="test")
        await executor.execute(job)
        records = executor.get_records(job.job_id)
        assert len(records) == 1
        assert records[0].status == ExecutionStatus.SUCCESS


# ===================================================================
# SECTION 7 — Dispatcher
# ===================================================================

class TestJobDispatcher:
    @pytest.fixture
    def dispatcher(self) -> JobDispatcher:
        queue = JobQueue()
        executor = InMemoryJobExecutor()
        return JobDispatcher(queue=queue, executor=executor, max_concurrency=2)

    @pytest.mark.asyncio
    async def test_start_stop(self, dispatcher: JobDispatcher) -> None:
        assert dispatcher.is_running is False
        await dispatcher.start()
        assert dispatcher.is_running is True
        await dispatcher.stop()
        assert dispatcher.is_running is False

    @pytest.mark.asyncio
    async def test_active_count(self, dispatcher: JobDispatcher) -> None:
        assert dispatcher.active_count == 0

    @pytest.mark.asyncio
    async def test_get_active_jobs(self, dispatcher: JobDispatcher) -> None:
        active = await dispatcher.get_active_jobs()
        assert active == []

    @pytest.mark.asyncio
    async def test_cancel_nonexistent(self, dispatcher: JobDispatcher) -> None:
        result = await dispatcher.cancel("nope")
        assert result is False


# ===================================================================
# SECTION 8 — Lifecycle
# ===================================================================

class TestSchedulerLifecycle:
    @pytest.fixture
    def lifecycle(self) -> SchedulerLifecycle:
        return SchedulerLifecycle()

    def test_initial_state(self, lifecycle: SchedulerLifecycle) -> None:
        assert lifecycle.state == SchedulerLifecycleState.REGISTERED

    def test_transition_initialized(self, lifecycle: SchedulerLifecycle) -> None:
        assert lifecycle.transition(SchedulerLifecycleState.INITIALIZED) is True
        assert lifecycle.state == SchedulerLifecycleState.INITIALIZED

    def test_transition_ready(self, lifecycle: SchedulerLifecycle) -> None:
        lifecycle.transition(SchedulerLifecycleState.INITIALIZED)
        assert lifecycle.transition(SchedulerLifecycleState.READY) is True
        assert lifecycle.state == SchedulerLifecycleState.READY

    def test_transition_running(self, lifecycle: SchedulerLifecycle) -> None:
        lifecycle.transition(SchedulerLifecycleState.INITIALIZED)
        lifecycle.transition(SchedulerLifecycleState.READY)
        assert lifecycle.transition(SchedulerLifecycleState.RUNNING) is True
        assert lifecycle.state == SchedulerLifecycleState.RUNNING

    def test_transition_paused(self, lifecycle: SchedulerLifecycle) -> None:
        lifecycle.transition(SchedulerLifecycleState.INITIALIZED)
        lifecycle.transition(SchedulerLifecycleState.READY)
        lifecycle.transition(SchedulerLifecycleState.RUNNING)
        assert lifecycle.transition(SchedulerLifecycleState.PAUSED) is True
        assert lifecycle.state == SchedulerLifecycleState.PAUSED

    def test_transition_stopped(self, lifecycle: SchedulerLifecycle) -> None:
        lifecycle.transition(SchedulerLifecycleState.INITIALIZED)
        lifecycle.transition(SchedulerLifecycleState.READY)
        lifecycle.transition(SchedulerLifecycleState.RUNNING)
        assert lifecycle.transition(SchedulerLifecycleState.STOPPED) is True
        assert lifecycle.state == SchedulerLifecycleState.STOPPED

    def test_transition_failed(self, lifecycle: SchedulerLifecycle) -> None:
        lifecycle.transition(SchedulerLifecycleState.INITIALIZED)
        lifecycle.transition(SchedulerLifecycleState.READY)
        lifecycle.transition(SchedulerLifecycleState.RUNNING)
        assert lifecycle.transition(SchedulerLifecycleState.FAILED) is True
        assert lifecycle.state == SchedulerLifecycleState.FAILED

    def test_transition_shutdown(self, lifecycle: SchedulerLifecycle) -> None:
        lifecycle.transition(SchedulerLifecycleState.INITIALIZED)
        lifecycle.transition(SchedulerLifecycleState.SHUTDOWN) is True
        assert lifecycle.state == SchedulerLifecycleState.SHUTDOWN

    def test_invalid_transition(self, lifecycle: SchedulerLifecycle) -> None:
        assert lifecycle.transition(SchedulerLifecycleState.RUNNING) is False
        assert lifecycle.state == SchedulerLifecycleState.REGISTERED

    def test_same_state_transition(self, lifecycle: SchedulerLifecycle) -> None:
        assert lifecycle.transition(SchedulerLifecycleState.REGISTERED) is True

    def test_can_transition(self, lifecycle: SchedulerLifecycle) -> None:
        assert lifecycle.can_transition(SchedulerLifecycleState.INITIALIZED) is True
        assert lifecycle.can_transition(SchedulerLifecycleState.RUNNING) is False

    def test_uptime(self, lifecycle: SchedulerLifecycle) -> None:
        assert lifecycle.uptime_seconds == 0.0
        lifecycle.transition(SchedulerLifecycleState.INITIALIZED)
        lifecycle.transition(SchedulerLifecycleState.READY)
        lifecycle.transition(SchedulerLifecycleState.RUNNING)
        assert lifecycle.uptime_seconds >= 0.0

    def test_transition_history(self, lifecycle: SchedulerLifecycle) -> None:
        lifecycle.transition(SchedulerLifecycleState.INITIALIZED)
        lifecycle.transition(SchedulerLifecycleState.READY)
        history = lifecycle.transition_history
        assert len(history) == 2

    def test_reset(self, lifecycle: SchedulerLifecycle) -> None:
        lifecycle.transition(SchedulerLifecycleState.INITIALIZED)
        lifecycle.reset()
        assert lifecycle.state == SchedulerLifecycleState.REGISTERED
        assert lifecycle.transition_history == []

    def test_shutdown_from_registered(self, lifecycle: SchedulerLifecycle) -> None:
        assert lifecycle.transition(SchedulerLifecycleState.SHUTDOWN) is True

    def test_shutdown_blocks_transitions(self, lifecycle: SchedulerLifecycle) -> None:
        lifecycle.transition(SchedulerLifecycleState.SHUTDOWN)
        assert lifecycle.transition(SchedulerLifecycleState.INITIALIZED) is False


# ===================================================================
# SECTION 9 — Metrics
# ===================================================================

class TestSchedulerMetrics:
    @pytest.fixture(autouse=True)
    def _reset(self) -> None:
        SchedulerMetrics.reset_singleton()

    def test_singleton(self) -> None:
        m1 = get_scheduler_metrics()
        m2 = get_scheduler_metrics()
        assert m1 is m2

    def test_record_scheduled(self) -> None:
        m = get_scheduler_metrics()
        m.record_scheduled()
        assert m.total_scheduled == 1

    def test_record_executed(self) -> None:
        m = get_scheduler_metrics()
        m.record_executed(100.0)
        assert m.total_executed == 1
        assert m.average_execution_time_ms == 100.0

    def test_record_failed(self) -> None:
        m = get_scheduler_metrics()
        m.record_failed()
        assert m.total_failed == 1

    def test_record_cancelled(self) -> None:
        m = get_scheduler_metrics()
        m.record_cancelled()
        assert m.total_cancelled == 1

    def test_record_retry(self) -> None:
        m = get_scheduler_metrics()
        m.record_retry()
        assert m.retry_count == 1

    def test_record_timeout(self) -> None:
        m = get_scheduler_metrics()
        m.record_timeout()
        assert m.timeout_count == 1

    def test_average_execution_time(self) -> None:
        m = get_scheduler_metrics()
        assert m.average_execution_time_ms == 0.0
        m.record_executed(100.0)
        m.record_executed(200.0)
        assert m.average_execution_time_ms == 150.0

    def test_to_response(self) -> None:
        m = get_scheduler_metrics()
        m.record_scheduled()
        resp = m.to_response(queue_length=5)
        assert resp.total_scheduled == 1
        assert resp.queue_length == 5

    def test_reset(self) -> None:
        m = get_scheduler_metrics()
        m.record_scheduled()
        m.record_executed(50.0)
        m.reset()
        assert m.total_scheduled == 0
        assert m.total_executed == 0

    def test_uptime(self) -> None:
        m = get_scheduler_metrics()
        assert m.uptime_seconds >= 0.0


# ===================================================================
# SECTION 10 — Tracing
# ===================================================================

class TestSchedulerTracer:
    @pytest.fixture
    def tracer(self) -> SchedulerTracer:
        return SchedulerTracer()

    def test_start_end_span(self, tracer: SchedulerTracer) -> None:
        span = tracer.start_span("test-op")
        assert span.name == "test-op"
        assert span.span_id
        tracer.end_span(span)
        assert span.end_time is not None
        assert span.duration_ms is not None
        assert span.duration_ms >= 0.0

    def test_span_attributes(self, tracer: SchedulerTracer) -> None:
        span = tracer.start_span("test")
        span.set_attribute("key", "value")
        assert span.attributes["key"] == "value"
        tracer.end_span(span)

    def test_span_error(self, tracer: SchedulerTracer) -> None:
        span = tracer.start_span("test")
        span.set_error("something went wrong")
        assert span.status == "error"
        assert span.error == "something went wrong"
        tracer.end_span(span)

    def test_get_traces(self, tracer: SchedulerTracer) -> None:
        span = tracer.start_span("op1")
        tracer.end_span(span)
        traces = tracer.get_traces()
        assert len(traces) == 1
        assert traces[0]["name"] == "op1"

    def test_get_traces_by_name(self, tracer: SchedulerTracer) -> None:
        s1 = tracer.start_span("op1")
        tracer.end_span(s1)
        s2 = tracer.start_span("op2")
        tracer.end_span(s2)
        op1_traces = tracer.get_traces(name="op1")
        assert len(op1_traces) == 1

    def test_get_span(self, tracer: SchedulerTracer) -> None:
        span = tracer.start_span("test")
        found = tracer.get_span(span.span_id)
        assert found is span
        tracer.end_span(span)

    def test_get_span_not_found(self, tracer: SchedulerTracer) -> None:
        assert tracer.get_span("nonexistent") is None

    def test_clear(self, tracer: SchedulerTracer) -> None:
        span = tracer.start_span("test")
        tracer.end_span(span)
        count = tracer.clear()
        assert count == 1
        assert tracer.span_count == 0

    def test_max_spans(self) -> None:
        tracer = SchedulerTracer(max_spans=3)
        for i in range(5):
            span = tracer.start_span(f"span-{i}")
            tracer.end_span(span)
        assert tracer.span_count == 3

    def test_to_response(self, tracer: SchedulerTracer) -> None:
        span = tracer.start_span("test")
        tracer.end_span(span)
        resp = tracer.to_response()
        assert resp.total == 1
        assert len(resp.traces) == 1

    def test_trace_counter(self, tracer: SchedulerTracer) -> None:
        tracer.start_span("a")
        tracer.start_span("b")
        assert tracer._trace_counter == 2


# ===================================================================
# SECTION 11 — Trigger Strategies
# ===================================================================

class TestTriggerStrategies:
    @pytest.mark.asyncio
    async def test_cron_trigger_name(self) -> None:
        strategy = CronTriggerStrategy()
        assert strategy.name == "cron"

    @pytest.mark.asyncio
    async def test_cron_trigger_next_run(self) -> None:
        strategy = CronTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.CRON, cron_expression="0 * * * *")
        next_run = await strategy.next_run_time(config)
        assert next_run is not None
        assert next_run > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_cron_trigger_next_run_no_expression(self) -> None:
        strategy = CronTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.CRON)
        assert await strategy.next_run_time(config) is None

    @pytest.mark.asyncio
    async def test_interval_trigger_name(self) -> None:
        strategy = IntervalTriggerStrategy()
        assert strategy.name == "interval"

    @pytest.mark.asyncio
    async def test_interval_trigger_next_run(self) -> None:
        strategy = IntervalTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.INTERVAL, interval_seconds=60)
        next_run = await strategy.next_run_time(config)
        assert next_run is not None
        assert next_run > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_interval_trigger_should_run_no_last(self) -> None:
        strategy = IntervalTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.INTERVAL, interval_seconds=60)
        assert await strategy.should_run(config) is True

    @pytest.mark.asyncio
    async def test_interval_trigger_should_run(self) -> None:
        strategy = IntervalTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.INTERVAL, interval_seconds=1)
        last_run = datetime.now(timezone.utc) - timedelta(seconds=2)
        assert await strategy.should_run(config, last_run) is True

    @pytest.mark.asyncio
    async def test_interval_trigger_should_not_run(self) -> None:
        strategy = IntervalTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.INTERVAL, interval_seconds=60)
        last_run = datetime.now(timezone.utc)
        assert await strategy.should_run(config, last_run) is False

    @pytest.mark.asyncio
    async def test_datetime_trigger_name(self) -> None:
        strategy = DateTimeTriggerStrategy()
        assert strategy.name == "datetime"

    @pytest.mark.asyncio
    async def test_datetime_trigger_next_run(self) -> None:
        strategy = DateTimeTriggerStrategy()
        run_at = datetime.now(timezone.utc) + timedelta(hours=1)
        config = TriggerConfig(trigger_type=TriggerType.DATETIME, run_at=run_at)
        assert await strategy.next_run_time(config) == run_at

    @pytest.mark.asyncio
    async def test_datetime_trigger_should_run(self) -> None:
        strategy = DateTimeTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.DATETIME, run_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        assert await strategy.should_run(config) is True

    @pytest.mark.asyncio
    async def test_datetime_trigger_should_not_run(self) -> None:
        strategy = DateTimeTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.DATETIME, run_at=datetime.now(timezone.utc) + timedelta(hours=1))
        assert await strategy.should_run(config) is False

    @pytest.mark.asyncio
    async def test_event_trigger_name(self) -> None:
        strategy = EventTriggerStrategy()
        assert strategy.name == "event"

    @pytest.mark.asyncio
    async def test_event_trigger_next_run_none(self) -> None:
        strategy = EventTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.EVENT)
        assert await strategy.next_run_time(config) is None

    @pytest.mark.asyncio
    async def test_event_trigger_should_not_run(self) -> None:
        strategy = EventTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.EVENT)
        assert await strategy.should_run(config) is False

    @pytest.mark.asyncio
    async def test_dependency_trigger_name(self) -> None:
        strategy = DependencyTriggerStrategy()
        assert strategy.name == "dependency"

    @pytest.mark.asyncio
    async def test_dependency_trigger_next_run_none(self) -> None:
        strategy = DependencyTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.DEPENDENCY)
        assert await strategy.next_run_time(config) is None

    @pytest.mark.asyncio
    async def test_custom_trigger_name(self) -> None:
        strategy = CustomTriggerStrategy()
        assert strategy.name == "custom"

    @pytest.mark.asyncio
    async def test_custom_trigger_should_run(self) -> None:
        strategy = CustomTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.CUSTOM, custom_config={"should_run": True})
        assert await strategy.should_run(config) is True

    @pytest.mark.asyncio
    async def test_custom_trigger_should_not_run(self) -> None:
        strategy = CustomTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.CUSTOM)
        assert await strategy.should_run(config) is False

    @pytest.mark.asyncio
    async def test_manual_trigger_name(self) -> None:
        strategy = ManualTriggerStrategy()
        assert strategy.name == "manual"

    @pytest.mark.asyncio
    async def test_manual_trigger_should_not_run(self) -> None:
        strategy = ManualTriggerStrategy()
        config = TriggerConfig(trigger_type=TriggerType.MANUAL)
        assert await strategy.should_run(config) is False


# ===================================================================
# SECTION 12 — Engine
# ===================================================================

class TestInMemorySchedulerEngine:
    @pytest.fixture
    def engine(self) -> InMemorySchedulerEngine:
        return SchedulerFactory.create_engine()

    @pytest.mark.asyncio
    async def test_schedule_job(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job()
        result = await engine.schedule_job(job)
        assert result.status == JobStatus.SCHEDULED
        assert engine.lifecycle.state == SchedulerLifecycleState.REGISTERED

    @pytest.mark.asyncio
    async def test_get_job(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job()
        await engine.schedule_job(job)
        got = await engine.get_job(job.job_id)
        assert got is not None
        assert got.job_id == job.job_id

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, engine: InMemorySchedulerEngine) -> None:
        assert await engine.get_job("nope") is None

    @pytest.mark.asyncio
    async def test_list_jobs(self, engine: InMemorySchedulerEngine) -> None:
        await engine.schedule_job(_make_job(job_id="a"))
        await engine.schedule_job(_make_job(job_id="b"))
        jobs = await engine.list_jobs()
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_cancel_job(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job()
        await engine.schedule_job(job)
        assert await engine.cancel_job(job.job_id) is True
        got = await engine.get_job(job.job_id)
        assert got is not None
        assert got.status == JobStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent(self, engine: InMemorySchedulerEngine) -> None:
        assert await engine.cancel_job("nope") is False

    @pytest.mark.asyncio
    async def test_pause_job(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job()
        await engine.schedule_job(job)
        assert await engine.pause_job(job.job_id) is True
        got = await engine.get_job(job.job_id)
        assert got is not None
        assert got.status == JobStatus.PAUSED

    @pytest.mark.asyncio
    async def test_pause_nonexistent(self, engine: InMemorySchedulerEngine) -> None:
        assert await engine.pause_job("nope") is False

    @pytest.mark.asyncio
    async def test_pause_wrong_status(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job(status=JobStatus.COMPLETED)
        await engine.repository.save(job)
        assert await engine.pause_job(job.job_id) is False

    @pytest.mark.asyncio
    async def test_resume_job(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job(status=JobStatus.PAUSED)
        await engine.repository.save(job)
        assert await engine.resume_job(job.job_id) is True
        got = await engine.get_job(job.job_id)
        assert got is not None
        assert got.status == JobStatus.SCHEDULED

    @pytest.mark.asyncio
    async def test_resume_nonexistent(self, engine: InMemorySchedulerEngine) -> None:
        assert await engine.resume_job("nope") is False

    @pytest.mark.asyncio
    async def test_resume_wrong_status(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job(status=JobStatus.COMPLETED)
        await engine.repository.save(job)
        assert await engine.resume_job(job.job_id) is False

    @pytest.mark.asyncio
    async def test_retry_job(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job(status=JobStatus.FAILED)
        await engine.repository.save(job)
        assert await engine.retry_job(job.job_id) is True
        got = await engine.get_job(job.job_id)
        assert got is not None
        assert got.status == JobStatus.RETRYING
        assert got.retries == 1

    @pytest.mark.asyncio
    async def test_retry_nonexistent(self, engine: InMemorySchedulerEngine) -> None:
        assert await engine.retry_job("nope") is False

    @pytest.mark.asyncio
    async def test_retry_wrong_status(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job(status=JobStatus.COMPLETED)
        await engine.repository.save(job)
        assert await engine.retry_job(job.job_id) is False

    @pytest.mark.asyncio
    async def test_retry_exhausted(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job(status=JobStatus.FAILED, max_retries=2)
        job.retries = 2
        await engine.repository.save(job)
        assert await engine.retry_job(job.job_id) is False

    @pytest.mark.asyncio
    async def test_delete_job(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job()
        await engine.schedule_job(job)
        assert await engine.delete_job(job.job_id) is True
        assert await engine.get_job(job.job_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, engine: InMemorySchedulerEngine) -> None:
        assert await engine.delete_job("nope") is False

    @pytest.mark.asyncio
    async def test_get_statistics(self, engine: InMemorySchedulerEngine) -> None:
        await engine.schedule_job(_make_job(job_id="a"))
        await engine.schedule_job(_make_job(job_id="b"))
        stats = await engine.get_statistics()
        assert stats["total_jobs"] == 2
        assert stats["scheduled_jobs"] == 2

    @pytest.mark.asyncio
    async def test_run_pending(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job(trigger_type=TriggerType.DATETIME, status=JobStatus.SCHEDULED)
        job.next_run = datetime.now(timezone.utc) - timedelta(seconds=1)
        await engine.repository.save(job)
        await engine.queue.enqueue(job)

        async def handler(job: Job) -> str:
            return "ok"

        engine._executor.register_handler(job.name, handler)
        executed = await engine.run_pending()
        assert executed == 1

    @pytest.mark.asyncio
    async def test_schedule_with_cron_trigger(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job(trigger_type=TriggerType.CRON)
        job.trigger.cron_expression = "0 * * * *"
        result = await engine.schedule_job(job)
        assert result.status == JobStatus.SCHEDULED
        assert result.next_run is not None

    @pytest.mark.asyncio
    async def test_schedule_with_interval_trigger(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job(trigger_type=TriggerType.INTERVAL)
        job.trigger.interval_seconds = 60
        result = await engine.schedule_job(job)
        assert result.status == JobStatus.SCHEDULED
        assert result.next_run is not None

    @pytest.mark.asyncio
    async def test_execute_job_success(self, engine: InMemorySchedulerEngine) -> None:
        job = _make_job(name="test-execute")
        await engine.schedule_job(job)

        async def handler(job: Job) -> str:
            return "result"

        engine._executor.register_handler("test-execute", handler)
        result = await engine.execute_job(job.job_id)
        assert result == "result"

    @pytest.mark.asyncio
    async def test_execute_job_not_found(self, engine: InMemorySchedulerEngine) -> None:
        with pytest.raises(ValueError, match="Job not found"):
            await engine.execute_job("nope")


# ===================================================================
# SECTION 13 — Scheduler Facade
# ===================================================================

class TestScheduler:
    @pytest_asyncio.fixture
    async def scheduler(self) -> Scheduler:
        s = SchedulerFactory.create_scheduler()
        await s.start()
        return s

    @pytest.mark.asyncio
    async def test_start_stop(self, scheduler: Scheduler) -> None:
        assert scheduler.is_running() is True
        await scheduler.stop()
        assert scheduler.is_running() is False

    @pytest.mark.asyncio
    async def test_shutdown(self, scheduler: Scheduler) -> None:
        await scheduler.shutdown()
        assert scheduler.lifecycle.state == SchedulerLifecycleState.SHUTDOWN

    @pytest.mark.asyncio
    async def test_schedule_job(self, scheduler: Scheduler) -> None:
        req = CreateJobRequest(name="test-schedule", job_type=JobType.MANUAL)
        job = await scheduler.schedule_job(req)
        assert job.job_id
        assert job.name == "test-schedule"

    @pytest.mark.asyncio
    async def test_get_job(self, scheduler: Scheduler) -> None:
        req = CreateJobRequest(name="test-get")
        created = await scheduler.schedule_job(req)
        got = await scheduler.get_job(created.job_id)
        assert got is not None
        assert got.name == "test-get"

    @pytest.mark.asyncio
    async def test_list_jobs(self, scheduler: Scheduler) -> None:
        await scheduler.schedule_job(CreateJobRequest(name="a"))
        await scheduler.schedule_job(CreateJobRequest(name="b"))
        jobs = await scheduler.list_jobs()
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_cancel_job(self, scheduler: Scheduler) -> None:
        job = await scheduler.schedule_job(CreateJobRequest(name="cancel-me"))
        assert await scheduler.cancel_job(job.job_id) is True

    @pytest.mark.asyncio
    async def test_pause_resume(self, scheduler: Scheduler) -> None:
        job = await scheduler.schedule_job(CreateJobRequest(name="pause-me"))
        assert await scheduler.pause_job(job.job_id) is True
        assert await scheduler.resume_job(job.job_id) is True

    @pytest.mark.asyncio
    async def test_delete_job(self, scheduler: Scheduler) -> None:
        job = await scheduler.schedule_job(CreateJobRequest(name="delete-me"))
        assert await scheduler.delete_job(job.job_id) is True
        assert await scheduler.get_job(job.job_id) is None

    @pytest.mark.asyncio
    async def test_retry_job(self, scheduler: Scheduler) -> None:
        from app.scheduler.schemas import Job, JobStatus
        job = _make_job(status=JobStatus.FAILED)
        await scheduler.engine.repository.save(job)
        assert await scheduler.retry_job(job.job_id) is True

    @pytest.mark.asyncio
    async def test_run_pending(self, scheduler: Scheduler) -> None:
        executed = await scheduler.run_pending()
        assert executed >= 0

    @pytest.mark.asyncio
    async def test_get_statistics(self, scheduler: Scheduler) -> None:
        stats = await scheduler.get_statistics()
        assert "total_jobs" in stats
        assert "scheduled_jobs" in stats

    @pytest.mark.asyncio
    async def test_get_metrics_response(self, scheduler: Scheduler) -> None:
        resp = scheduler.get_metrics_response()
        assert isinstance(resp, SchedulerMetricsResponse)

    @pytest.mark.asyncio
    async def test_get_traces_response(self, scheduler: Scheduler) -> None:
        resp = scheduler.get_traces_response()
        assert isinstance(resp, SchedulerTracesResponse)

    @pytest.mark.asyncio
    async def test_schedule_domain_job(self, scheduler: Scheduler) -> None:
        job = _make_job()
        result = await scheduler.schedule(job)
        assert result.status == JobStatus.SCHEDULED


# ===================================================================
# SECTION 14 — Factory
# ===================================================================

class TestSchedulerFactory:
    @pytest.mark.asyncio
    async def test_create_scheduler(self) -> None:
        scheduler = SchedulerFactory.create_scheduler()
        assert scheduler is not None
        assert scheduler.lifecycle is not None
        assert scheduler.engine is not None
        assert scheduler.queue is not None
        assert scheduler.metrics is not None
        assert scheduler.tracer is not None

    @pytest.mark.asyncio
    async def test_create_engine(self) -> None:
        engine = SchedulerFactory.create_engine()
        assert engine is not None
        assert engine.lifecycle is not None

    @pytest.mark.asyncio
    async def test_create_engine_with_custom_deps(self) -> None:
        repo = InMemoryJobRepository()
        queue = JobQueue()
        metrics = SchedulerMetrics()
        tracer = SchedulerTracer()
        engine = SchedulerFactory.create_engine(repository=repo, queue=queue, metrics=metrics, tracer=tracer)
        assert engine.repository is repo
        assert engine.queue is queue


# ===================================================================
# SECTION 15 — ABCs
# ===================================================================

class TestABCs:
    def test_scheduler_provider_is_abstract(self) -> None:
        assert hasattr(SchedulerProvider, "__abstractmethods__")

    def test_scheduler_engine_is_abstract(self) -> None:
        assert hasattr(SchedulerEngine, "__abstractmethods__")

    def test_job_repository_is_abstract(self) -> None:
        assert hasattr(JobRepository, "__abstractmethods__")

    def test_trigger_strategy_is_abstract(self) -> None:
        assert hasattr(TriggerStrategy, "__abstractmethods__")

    def test_job_executor_is_abstract(self) -> None:
        assert hasattr(JobExecutor, "__abstractmethods__")

    def test_schedule_persistence_is_abstract(self) -> None:
        assert hasattr(SchedulePersistence, "__abstractmethods__")

    def test_cannot_instantiate_scheduler_provider(self) -> None:
        with pytest.raises(TypeError):
            SchedulerProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_scheduler_engine(self) -> None:
        with pytest.raises(TypeError):
            SchedulerEngine()  # type: ignore[abstract]

    def test_cannot_instantiate_job_repository(self) -> None:
        with pytest.raises(TypeError):
            JobRepository()  # type: ignore[abstract]

    def test_cannot_instantiate_trigger_strategy(self) -> None:
        with pytest.raises(TypeError):
            TriggerStrategy()  # type: ignore[abstract]

    def test_cannot_instantiate_job_executor(self) -> None:
        with pytest.raises(TypeError):
            JobExecutor()  # type: ignore[abstract]

    def test_cannot_instantiate_schedule_persistence(self) -> None:
        with pytest.raises(TypeError):
            SchedulePersistence()  # type: ignore[abstract]


# ===================================================================
# SECTION 16 — TraceSpan
# ===================================================================

class TestTraceSpan:
    def test_creation(self) -> None:
        span = TraceSpan("test")
        assert span.name == "test"
        assert span.span_id
        assert span.start_time is not None
        assert span.end_time is None

    def test_set_attribute(self) -> None:
        span = TraceSpan("test")
        span.set_attribute("k", "v")
        assert span.attributes["k"] == "v"

    def test_set_error(self) -> None:
        span = TraceSpan("test")
        span.set_error("err")
        assert span.error == "err"
        assert span.status == "error"

    def test_finish(self) -> None:
        span = TraceSpan("test")
        span.finish()
        assert span.end_time is not None
        assert span.duration_ms is not None

    def test_to_dict(self) -> None:
        span = TraceSpan("test")
        span.set_attribute("key", "value")
        d = span.to_dict()
        assert d["name"] == "test"
        assert d["attributes"]["key"] == "value"
        assert d["status"] == "ok"

    def test_parent_id(self) -> None:
        parent = TraceSpan("parent")
        child = TraceSpan("child", parent_id=parent.span_id)
        assert child.parent_id == parent.span_id

    def test_to_dict_with_error(self) -> None:
        span = TraceSpan("test")
        span.set_error("fail")
        d = span.to_dict()
        assert d["error"] == "fail"
        assert d["status"] == "error"


# ===================================================================
# SECTION 17 — Integration / End-to-End
# ===================================================================

class TestSchedulerIntegration:
    @pytest.mark.asyncio
    async def test_full_job_lifecycle(self) -> None:
        scheduler = SchedulerFactory.create_scheduler()
        await scheduler.start()

        results: list[str] = []

        async def handler(job: Job) -> str:
            results.append(job.name)
            return "done"

        scheduler.engine._executor.register_handler("lifecycle-job", handler)

        req = CreateJobRequest(name="lifecycle-job", job_type=JobType.ONE_TIME)
        job = await scheduler.schedule_job(req)
        assert job.status == JobStatus.SCHEDULED

        result = await scheduler.execute_job(job.job_id)
        assert result == "done"
        assert len(results) == 1

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_schedule_cancel_delete(self) -> None:
        scheduler = SchedulerFactory.create_scheduler()
        await scheduler.start()

        job = await scheduler.schedule_job(CreateJobRequest(name="to-cancel"))
        assert await scheduler.cancel_job(job.job_id) is True
        assert await scheduler.delete_job(job.job_id) is True
        assert await scheduler.get_job(job.job_id) is None

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_pause_resume_cycle(self) -> None:
        scheduler = SchedulerFactory.create_scheduler()
        await scheduler.start()

        job = await scheduler.schedule_job(CreateJobRequest(name="pause-resume"))
        assert await scheduler.pause_job(job.job_id) is True
        paused = await scheduler.get_job(job.job_id)
        assert paused is not None
        assert paused.status == JobStatus.PAUSED

        assert await scheduler.resume_job(job.job_id) is True
        resumed = await scheduler.get_job(job.job_id)
        assert resumed is not None
        assert resumed.status == JobStatus.SCHEDULED

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_retry_cycle(self) -> None:
        scheduler = SchedulerFactory.create_scheduler()
        await scheduler.start()

        job = _make_job(status=JobStatus.FAILED)
        await scheduler.engine.repository.save(job)
        assert await scheduler.retry_job(job.job_id) is True
        retried = await scheduler.get_job(job.job_id)
        assert retried is not None
        assert retried.status == JobStatus.RETRYING
        assert retried.retries == 1

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_multiple_schedules(self) -> None:
        scheduler = SchedulerFactory.create_scheduler()
        await scheduler.start()

        for i in range(10):
            await scheduler.schedule_job(CreateJobRequest(name=f"job-{i}"))

        jobs = await scheduler.list_jobs()
        assert len(jobs) == 10

        stats = await scheduler.get_statistics()
        assert stats["total_jobs"] == 10

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_run_pending_with_due_jobs(self) -> None:
        scheduler = SchedulerFactory.create_scheduler()
        await scheduler.start()

        executed_jobs: list[str] = []

        async def handler(job: Job) -> str:
            executed_jobs.append(job.job_id)
            return "ok"

        scheduler.engine._executor.register_handler("pending-job", handler)

        job = _make_job(job_id="pending-1", name="pending-job", trigger_type=TriggerType.DATETIME, status=JobStatus.SCHEDULED)
        job.next_run = datetime.now(timezone.utc) - timedelta(seconds=1)
        await scheduler.engine.repository.save(job)
        await scheduler.engine.queue.enqueue(job)

        count = await scheduler.run_pending()
        assert count >= 1
        assert "pending-1" in executed_jobs

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_metrics_after_operations(self) -> None:
        SchedulerMetrics.reset_singleton()
        scheduler = SchedulerFactory.create_scheduler()
        await scheduler.start()

        await scheduler.schedule_job(CreateJobRequest(name="m1"))
        await scheduler.schedule_job(CreateJobRequest(name="m2"))

        metrics = scheduler.get_metrics_response()
        assert metrics.total_scheduled == 2

        await scheduler.shutdown()
        SchedulerMetrics.reset_singleton()

    @pytest.mark.asyncio
    async def test_traces_after_operations(self) -> None:
        scheduler = SchedulerFactory.create_scheduler()
        await scheduler.start()

        await scheduler.schedule_job(CreateJobRequest(name="t1"))

        traces = scheduler.get_traces_response()
        assert traces.total >= 1

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        scheduler = SchedulerFactory.create_scheduler()
        await scheduler.start()

        stats = await scheduler.get_statistics()
        health = SchedulerHealthResponse(
            status="ok" if scheduler.is_running() else "stopped",
            lifecycle_state=scheduler.lifecycle.state.value,
            total_jobs=stats.get("total_jobs", 0),
            active_jobs=stats.get("running_jobs", 0),
            uptime_seconds=scheduler.lifecycle.uptime_seconds,
        )
        assert health.status == "ok"
        assert health.lifecycle_state == "running"

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_schedule_with_cron(self) -> None:
        scheduler = SchedulerFactory.create_scheduler()
        await scheduler.start()

        req = CreateJobRequest(
            name="cron-job",
            job_type=JobType.CRON,
            trigger=TriggerConfig(trigger_type=TriggerType.CRON, cron_expression="0 * * * *"),
        )
        job = await scheduler.schedule_job(req)
        assert job.status == JobStatus.SCHEDULED
        assert job.next_run is not None

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_schedule_with_interval(self) -> None:
        scheduler = SchedulerFactory.create_scheduler()
        await scheduler.start()

        req = CreateJobRequest(
            name="interval-job",
            job_type=JobType.INTERVAL,
            trigger=TriggerConfig(trigger_type=TriggerType.INTERVAL, interval_seconds=30),
        )
        job = await scheduler.schedule_job(req)
        assert job.status == JobStatus.SCHEDULED
        assert job.next_run is not None

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_schedule_with_datetime(self) -> None:
        scheduler = SchedulerFactory.create_scheduler()
        await scheduler.start()

        future = datetime.now(timezone.utc) + timedelta(hours=1)
        req = CreateJobRequest(
            name="datetime-job",
            job_type=JobType.ONE_TIME,
            trigger=TriggerConfig(trigger_type=TriggerType.DATETIME, run_at=future),
        )
        job = await scheduler.schedule_job(req)
        assert job.status == JobStatus.SCHEDULED

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_custom_trigger_strategy_registration(self) -> None:
        engine = SchedulerFactory.create_engine()

        class MyStrategy(TriggerStrategy):
            @property
            def name(self) -> str:
                return "my_custom"

            async def next_run_time(self, config: Any, last_run: Any = None) -> Any:
                return datetime.now(timezone.utc) + timedelta(seconds=5)

            async def should_run(self, config: Any, last_run: Any = None) -> bool:
                return True

        engine.register_trigger(TriggerType.CUSTOM, MyStrategy())
        job = _make_job(trigger_type=TriggerType.CUSTOM)
        job.trigger.custom_config = {"strategy": "my_custom"}
        result = await engine.schedule_job(job)
        assert result.next_run is not None
