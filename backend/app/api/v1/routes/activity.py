"""Activity log API endpoints — recent autonomous activity for Dashboard."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.api.dependencies import get_current_token
from app.security.models import Token

router = APIRouter(prefix="/activity", tags=["activity"])


class ActivityEntry(BaseModel):
    id: str
    goal_id: str | None = None
    goal_title: str | None = None
    action: str
    status: str
    goal_priority: int | None = None
    approval_id: str | None = None
    reason: str | None = None
    details: dict[str, Any] = {}
    created_at: str


class ActivityListResponse(BaseModel):
    entries: list[ActivityEntry]
    total: int


def _get_activity_repo(request: Request) -> Any:
    repo = getattr(request.app.state, "activity_repository", None)
    if repo is None:
        raise HTTPException(status_code=503, detail="Activity repository not available")
    return repo


@router.get("/", response_model=ActivityListResponse)
async def list_activity(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
) -> ActivityListResponse:
    """List recent activity log entries ordered by timestamp descending."""
    repo = _get_activity_repo(request)
    entries = await repo.list_recent(limit=limit)
    return ActivityListResponse(
        entries=[
            ActivityEntry(
                id=str(e.id),
                goal_id=str(e.goal_id) if e.goal_id else None,
                goal_title=e.goal_title,
                action=e.action,
                status=e.status,
                goal_priority=e.goal_priority,
                approval_id=e.approval_id,
                reason=e.reason,
                details=e.details or {},
                created_at=e.created_at.isoformat() if e.created_at else "",
            )
            for e in entries
        ],
        total=len(entries),
    )


@router.get("/recent", response_model=ActivityListResponse, include_in_schema=False)
async def list_recent_activity(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
) -> ActivityListResponse:
    """Alias for list_activity — returns all recent entries (public endpoint)."""
    repo = _get_activity_repo(request)
    entries = await repo.list_recent(limit=limit)
    return ActivityListResponse(
        entries=[
            ActivityEntry(
                id=str(e.id),
                goal_id=str(e.goal_id) if e.goal_id else None,
                goal_title=e.goal_title,
                action=e.action,
                status=e.status,
                goal_priority=e.goal_priority,
                approval_id=e.approval_id,
                reason=e.reason,
                details=e.details or {},
                created_at=e.created_at.isoformat() if e.created_at else "",
            )
            for e in entries
        ],
        total=len(entries),
    )


@router.get("/goal/{goal_id}", response_model=ActivityListResponse)
async def list_activity_by_goal(
    request: Request,
    goal_id: str,
    limit: int = Query(20, ge=1, le=100),
) -> ActivityListResponse:
    """List activity log entries for a specific goal."""
    from uuid import UUID

    repo = _get_activity_repo(request)
    try:
        goal_uuid = UUID(goal_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid goal ID format")

    entries = await repo.list_by_goal(goal_uuid, limit=limit)
    return ActivityListResponse(
        entries=[
            ActivityEntry(
                id=str(e.id),
                goal_id=str(e.goal_id) if e.goal_id else None,
                goal_title=e.goal_title,
                action=e.action,
                status=e.status,
                goal_priority=e.goal_priority,
                approval_id=e.approval_id,
                reason=e.reason,
                details=e.details or {},
                created_at=e.created_at.isoformat() if e.created_at else "",
            )
            for e in entries
        ],
        total=len(entries),
    )
