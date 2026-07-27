"""Scheduler API endpoints — 14 routes for scheduler operations."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.scheduler.schemas import (
    CreateJobRequest,
    JobResponse,
    JobStatistics,
    JobsListResponse,
    JobStatus,
    SchedulerHealthResponse,
    SchedulerMetricsResponse,
    SchedulerTracesResponse,
    UpdateJobRequest,
)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def _get_scheduler(request: Request) -> Any:
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not available")
    return scheduler


@router.post("/jobs", response_model=JobResponse)
async def schedule_job(request: Request, body: CreateJobRequest) -> JobResponse:
    scheduler = _get_scheduler(request)
    job = await scheduler.schedule_job(body)
    return JobResponse(success=True, job_id=job.job_id, message="Job scheduled")


@router.get("/jobs", response_model=JobsListResponse)
async def list_jobs(
    request: Request,
    status: Optional[JobStatus] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> JobsListResponse:
    scheduler = _get_scheduler(request)
    jobs = await scheduler.list_jobs(status=status, limit=limit, offset=offset)
    total = await scheduler.get_statistics()
    return JobsListResponse(jobs=jobs, total=total.get("total_jobs", len(jobs)))


@router.get("/jobs/{job_id}", response_model=dict[str, Any])
async def get_job(request: Request, job_id: str) -> dict[str, Any]:
    scheduler = _get_scheduler(request)
    job = await scheduler.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump()


@router.delete("/jobs/{job_id}", response_model=JobResponse)
async def delete_job(request: Request, job_id: str) -> JobResponse:
    scheduler = _get_scheduler(request)
    deleted = await scheduler.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(success=True, job_id=job_id, message="Job deleted")


@router.post("/jobs/{job_id}/execute", response_model=JobResponse)
async def execute_job(request: Request, job_id: str) -> JobResponse:
    scheduler = _get_scheduler(request)
    try:
        await scheduler.execute_job(job_id)
        return JobResponse(success=True, job_id=job_id, message="Job executed")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(request: Request, job_id: str) -> JobResponse:
    scheduler = _get_scheduler(request)
    cancelled = await scheduler.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Job not found or not cancellable")
    return JobResponse(success=True, job_id=job_id, message="Job cancelled")


@router.post("/jobs/{job_id}/pause", response_model=JobResponse)
async def pause_job(request: Request, job_id: str) -> JobResponse:
    scheduler = _get_scheduler(request)
    paused = await scheduler.pause_job(job_id)
    if not paused:
        raise HTTPException(status_code=404, detail="Job not found or not pausable")
    return JobResponse(success=True, job_id=job_id, message="Job paused")


@router.post("/jobs/{job_id}/resume", response_model=JobResponse)
async def resume_job(request: Request, job_id: str) -> JobResponse:
    scheduler = _get_scheduler(request)
    resumed = await scheduler.resume_job(job_id)
    if not resumed:
        raise HTTPException(status_code=404, detail="Job not found or not resumable")
    return JobResponse(success=True, job_id=job_id, message="Job resumed")


@router.post("/jobs/{job_id}/retry", response_model=JobResponse)
async def retry_job(request: Request, job_id: str) -> JobResponse:
    scheduler = _get_scheduler(request)
    retried = await scheduler.retry_job(job_id)
    if not retried:
        raise HTTPException(status_code=404, detail="Job not found or not retryable")
    return JobResponse(success=True, job_id=job_id, message="Job retry queued")


@router.post("/run-pending", response_model=dict[str, Any])
async def run_pending(request: Request) -> dict[str, Any]:
    scheduler = _get_scheduler(request)
    executed = await scheduler.run_pending()
    return {"executed": executed}


@router.get("/statistics", response_model=JobStatistics)
async def get_statistics(request: Request) -> JobStatistics:
    scheduler = _get_scheduler(request)
    stats = await scheduler.get_statistics()
    return JobStatistics(**stats)


@router.get("/metrics", response_model=SchedulerMetricsResponse)
async def get_metrics(request: Request) -> SchedulerMetricsResponse:
    scheduler = _get_scheduler(request)
    return scheduler.get_metrics_response()


@router.get("/traces", response_model=SchedulerTracesResponse)
async def get_traces(
    request: Request,
    name: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> SchedulerTracesResponse:
    scheduler = _get_scheduler(request)
    return scheduler.get_traces_response(limit=limit)


@router.get("/health", response_model=SchedulerHealthResponse)
async def get_health(request: Request) -> SchedulerHealthResponse:
    scheduler = _get_scheduler(request)
    stats = await scheduler.get_statistics()
    return SchedulerHealthResponse(
        status="ok" if scheduler.is_running() else "stopped",
        lifecycle_state=scheduler.lifecycle.state.value,
        total_jobs=stats.get("total_jobs", 0),
        active_jobs=stats.get("running_jobs", 0),
        uptime_seconds=scheduler.lifecycle.uptime_seconds,
    )
