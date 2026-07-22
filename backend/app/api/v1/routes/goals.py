"""Goal management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/goals", tags=["Goals"])


class CreateGoalRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: int = Field(default=3, ge=1, le=5)


class UpdateGoalRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = Field(default=None, pattern=r"^(active|blocked|completed|abandoned)$")
    priority: int | None = Field(default=None, ge=1, le=5)
    progress: int | None = Field(default=None, ge=0, le=100)
    block_reason: str | None = None


@router.get("/{user_id}")
async def list_goals(
    user_id: UUID,
    request: Request,
    status: str | None = Query(default=None, pattern=r"^(active|blocked|completed|abandoned)$"),
) -> list[dict]:
    goal_manager = request.app.state.goal_manager
    return await goal_manager.list_goals(user_id, status=status)


@router.post("/{user_id}")
async def create_goal(
    user_id: UUID,
    body: CreateGoalRequest,
    request: Request,
) -> dict:
    goal_manager = request.app.state.goal_manager
    return await goal_manager.create_goal(
        user_id, body.title, body.description, body.priority
    )


@router.get("/{user_id}/detail/{goal_id}")
async def get_goal(
    user_id: UUID,
    goal_id: UUID,
    request: Request,
) -> dict:
    goal_manager = request.app.state.goal_manager
    goal = await goal_manager.get_goal(goal_id)
    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )
    return goal


@router.patch("/{user_id}/detail/{goal_id}")
async def update_goal(
    user_id: UUID,
    goal_id: UUID,
    body: UpdateGoalRequest,
    request: Request,
) -> dict:
    goal_manager = request.app.state.goal_manager
    goal = await goal_manager.update_goal(
        goal_id,
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        progress=body.progress,
        block_reason=body.block_reason,
    )
    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )
    return goal


@router.delete("/{user_id}/detail/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    user_id: UUID,
    goal_id: UUID,
    request: Request,
) -> None:
    goal_manager = request.app.state.goal_manager
    deleted = await goal_manager.delete_goal(goal_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        )


@router.get("/{user_id}/next-actions")
async def next_actions(
    user_id: UUID,
    request: Request,
    limit: int = Query(default=3, ge=1, le=10),
) -> list[dict]:
    goal_manager = request.app.state.goal_manager
    return await goal_manager.get_next_actions(user_id, limit=limit)


@router.get("/{user_id}/blocked")
async def blocked_goals(
    user_id: UUID,
    request: Request,
) -> list[dict]:
    goal_manager = request.app.state.goal_manager
    return await goal_manager.get_blocked_goals(user_id)


@router.get("/{user_id}/analyze")
async def analyze(
    user_id: UUID,
    request: Request,
) -> dict:
    goal_manager = request.app.state.goal_manager
    return await goal_manager.analyze_progress(user_id)
