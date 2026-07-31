"""Event System API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.events.schemas import (
    EventFilter,
    EventHealthResponse,
    EventMetricsResponse,
    EventResponse,
    EventStatistics,
    EventTracesResponse,
    EventsListResponse,
    PublishRequest,
    ReplayRequest,
    ReplayResult,
)

router = APIRouter(prefix="/events", tags=["Events"])


def _get_event_bus(request: Request) -> Any:
    bus = getattr(request.app.state, "event_bus", None)
    if bus is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event bus not available",
        )
    return bus


def _get_event_publisher(request: Request) -> Any:
    publisher = getattr(request.app.state, "event_publisher", None)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event publisher not available",
        )
    return publisher


def _get_event_metrics(request: Request) -> Any:
    metrics = getattr(request.app.state, "event_metrics", None)
    if metrics is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event metrics not available",
        )
    return metrics


def _get_event_tracer(request: Request) -> Any:
    tracer = getattr(request.app.state, "event_tracer", None)
    if tracer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event tracer not available",
        )
    return tracer


@router.post("/publish", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def publish_event(body: PublishRequest, request: Request):
    publisher = _get_event_publisher(request)
    event = await publisher.publish(
        event_type=body.event_type,
        payload=body.payload,
        aggregate_id=body.aggregate_id,
        aggregate_type=body.aggregate_type,
        source=body.source,
        correlation_id=body.correlation_id,
        causation_id=body.causation_id,
        session_id=body.session_id,
        user_id=body.user_id,
        priority=body.priority,
        metadata=body.metadata,
    )
    return EventResponse(
        success=True,
        event_id=event.event_id,
        message=f"Event {body.event_type} published successfully",
    )


@router.post("/replay", response_model=ReplayResult)
async def replay_events(body: ReplayRequest, request: Request):
    bus = _get_event_bus(request)
    result = await bus.replay(body)
    return result


@router.get("", response_model=EventsListResponse)
async def list_events(
    request: Request,
    event_type: str | None = Query(default=None),
    source: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    aggregate_id: str | None = Query(default=None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
):
    bus = _get_event_bus(request)
    filter_expr = EventFilter(
        event_types=[event_type] if event_type else [],
        sources=[source] if source else [],
        session_ids=[session_id] if session_id else [],
        user_ids=[user_id] if user_id else [],
        aggregate_ids=[aggregate_id] if aggregate_id else [],
    )
    events = await bus.list_events(filter_expr=filter_expr, limit=limit, offset=offset)
    total = await bus.get_statistics()
    return EventsListResponse(
        events=events,
        total=total.get("total_events", len(events)),
    )


@router.get("/statistics", response_model=EventStatistics)
async def get_statistics(request: Request):
    bus = _get_event_bus(request)
    stats = await bus.get_statistics()
    return EventStatistics(**stats)


@router.get("/metrics", response_model=EventMetricsResponse)
async def get_metrics(request: Request):
    metrics = _get_event_metrics(request)
    summary = metrics.get_summary()
    return EventMetricsResponse(**summary)


@router.get("/health", response_model=EventHealthResponse)
async def health_check(request: Request):
    bus = _get_event_bus(request)
    health = await bus.health()
    return EventHealthResponse(
        status=health.get("status", "unknown"),
        lifecycle_state="running" if health.get("running") else "stopped",
        total_events=health.get("total_events", 0),
        active_subscriptions=health.get("active_subscriptions", 0),
        dead_letter_count=health.get("dead_letter_count", 0),
    )


@router.get("/traces", response_model=EventTracesResponse)
async def get_traces(
    request: Request,
    limit: int = Query(default=100, le=1000),
):
    tracer = _get_event_tracer(request)
    traces = tracer.get_traces(limit=limit)
    return EventTracesResponse(
        traces=[{
            "trace_id": t.trace_id,
            "event_id": t.event_id,
            "event_type": t.event_type,
            "operation": t.operation,
            "status": t.status,
            "timestamp": t.timestamp,
            "latency_ms": t.latency_ms,
            "details": t.details,
        } for t in traces],
        total=len(traces),
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, request: Request):
    bus = _get_event_bus(request)
    event = await bus.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse(
        success=True,
        event_id=event.event_id,
        message=f"Event {event.event_type}",
    )
