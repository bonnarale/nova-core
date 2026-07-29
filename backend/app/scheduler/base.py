"""Scheduler abstractions — ABCs for the scheduling subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.scheduler.schemas import Job, JobStatus, TriggerConfig


class SchedulerProvider(ABC):
    """Provider interface for the scheduler engine."""

    @abstractmethod
    async def initialize(self) -> None:
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        ...

    @abstractmethod
    async def schedule(self, job: Job) -> Job:
        ...

    @abstractmethod
    async def unschedule(self, job_id: str) -> bool:
        ...

    @abstractmethod
    async def get_next_run_time(self, job: Job) -> Any:
        ...


class SchedulerEngine(ABC):
    """Core scheduler engine interface."""

    @abstractmethod
    async def schedule_job(self, job: Job) -> Job:
        ...

    @abstractmethod
    async def execute_job(self, job_id: str) -> Any:
        ...

    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        ...

    @abstractmethod
    async def pause_job(self, job_id: str) -> bool:
        ...

    @abstractmethod
    async def resume_job(self, job_id: str) -> bool:
        ...

    @abstractmethod
    async def retry_job(self, job_id: str) -> bool:
        ...

    @abstractmethod
    async def delete_job(self, job_id: str) -> bool:
        ...

    @abstractmethod
    async def list_jobs(self, status: JobStatus | None = None, limit: int = 100, offset: int = 0) -> list[Job]:
        ...

    @abstractmethod
    async def get_job(self, job_id: str) -> Job | None:
        ...

    @abstractmethod
    async def run_pending(self) -> int:
        ...


class JobRepository(ABC):
    """Repository interface for job persistence."""

    @abstractmethod
    async def save(self, job: Job) -> Job:
        ...

    @abstractmethod
    async def get(self, job_id: str) -> Job | None:
        ...

    @abstractmethod
    async def list(self, status: JobStatus | None = None, limit: int = 100, offset: int = 0) -> list[Job]:
        ...

    @abstractmethod
    async def update(self, job: Job) -> Job:
        ...

    @abstractmethod
    async def delete(self, job_id: str) -> bool:
        ...

    @abstractmethod
    async def count(self, status: JobStatus | None = None) -> int:
        ...


class TriggerStrategy(ABC):
    """Strategy interface for job triggers."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def next_run_time(self, config: TriggerConfig, last_run: Any = None) -> Any | None:
        ...

    @abstractmethod
    async def should_run(self, config: TriggerConfig, last_run: Any = None) -> bool:
        ...


class JobExecutor(ABC):
    """Executor interface for running jobs."""

    @abstractmethod
    async def execute(self, job: Job) -> Any:
        ...

    @abstractmethod
    async def cancel(self, job_id: str) -> bool:
        ...

    @abstractmethod
    async def get_status(self, job_id: str) -> JobStatus | None:
        ...


class SchedulePersistence(ABC):
    """Persistence interface for scheduler state."""

    @abstractmethod
    async def store_job(self, job: Job) -> None:
        ...

    @abstractmethod
    async def get_job(self, job_id: str) -> Job | None:
        ...

    @abstractmethod
    async def update_job(self, job: Job) -> None:
        ...

    @abstractmethod
    async def delete_job(self, job_id: str) -> bool:
        ...

    @abstractmethod
    async def list_jobs(self, status: JobStatus | None = None, limit: int = 100, offset: int = 0) -> list[Job]:
        ...

    @abstractmethod
    async def count_jobs(self, status: JobStatus | None = None) -> int:
        ...

    @abstractmethod
    async def store_execution(self, record: Any) -> None:
        ...

    @abstractmethod
    async def list_executions(self, job_id: str, limit: int = 100) -> list[Any]:
        ...

    @abstractmethod
    async def clear(self) -> int:
        ...
