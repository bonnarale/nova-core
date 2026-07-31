"""Task orchestration API endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class CreateTaskRequest(BaseModel):
    goal: str = Field(min_length=1)
    plan: dict | None = None
    steps: list | None = None
    dependencies: list[str] | None = None
    assigned_agent: str | None = None


class UpdateTaskRequest(BaseModel):
    status: str | None = Field(
        default=None,
        pattern=r"^(CREATED|QUEUED|RUNNING|WAITING|FAILED|COMPLETED)$",
    )
    current_step: int | None = Field(default=None, ge=0)
    plan: dict | None = None
    steps: list | None = None
    artifacts: dict | None = None
    assigned_agent: str | None = None


class AdvanceStepRequest(BaseModel):
    artifacts: dict | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(body: CreateTaskRequest, request: Request) -> dict:
    task_manager = request.app.state.task_manager
    deps = [UUID(d) for d in body.dependencies] if body.dependencies else None
    return await task_manager.create_task(
        goal=body.goal,
        plan=body.plan,
        steps=body.steps,
        dependencies=deps,
        assigned_agent=body.assigned_agent,
    )


@router.get("")
async def list_tasks(
    request: Request,
    status: str | None = Query(
        default=None,
        pattern=r"^(CREATED|QUEUED|RUNNING|WAITING|FAILED|COMPLETED)$",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    task_manager = request.app.state.task_manager
    return await task_manager.list_tasks(status=status, limit=limit, offset=offset)


@router.get("/{task_id}")
async def get_task(task_id: UUID, request: Request) -> dict:
    task_manager = request.app.state.task_manager
    task = await task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


@router.patch("/{task_id}")
async def update_task(
    task_id: UUID, body: UpdateTaskRequest, request: Request
) -> dict:
    task_manager = request.app.state.task_manager
    updates = {}
    if body.status is not None:
        result = await task_manager.transition_task(task_id, body.status)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        return result
    if body.current_step is not None:
        updates["current_step"] = body.current_step
    if body.plan is not None:
        updates["plan"] = body.plan
    if body.steps is not None:
        updates["steps"] = body.steps
    if body.artifacts is not None:
        updates["artifacts"] = body.artifacts
    if body.assigned_agent is not None:
        updates["assigned_agent"] = body.assigned_agent

    task = await task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    if updates:
        task = await task_manager.transition_task(task_id, task["status"], **updates)
    return task or {}


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(task_id: UUID, request: Request) -> dict:
    task_manager = request.app.state.task_manager
    deleted = await task_manager.delete_task(task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return {"status": "deleted"}


@router.post("/{task_id}/advance")
async def advance_step(
    task_id: UUID, body: AdvanceStepRequest, request: Request
) -> dict:
    task_manager = request.app.state.task_manager
    result = await task_manager.advance_step(task_id, artifacts=body.artifacts)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return result


@router.post("/{task_id}/transition")
async def transition_task(
    task_id: UUID, body: UpdateTaskRequest, request: Request
) -> dict:
    task_manager = request.app.state.task_manager
    if not body.status:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status is required",
        )
    result = await task_manager.transition_task(task_id, body.status)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return result
