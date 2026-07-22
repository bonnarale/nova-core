"""Workflow Engine API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.workflows.models import WorkflowDefinition
from app.workflows.schemas import (
    WorkflowCreate,
    WorkflowExecutionAction,
    WorkflowExecutionCreate,
    WorkflowExecutionResponse,
    WorkflowResponse,
    WorkflowUpdate,
)

router = APIRouter(prefix="/workflows", tags=["Workflows"])


def _get_engine(request: Request):
    engine = request.app.state.workflow_engine
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow engine not available",
        )
    return engine


# --- Workflow Definition CRUD ---


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(body: WorkflowCreate, request: Request):
    engine = _get_engine(request)
    definition = WorkflowDefinition(
        name=body.name,
        description=body.description,
        version=body.version,
        input_schema=body.input_schema,
        output_schema=body.output_schema,
        tags=body.tags,
        metadata=body.metadata,
    )
    import uuid as _uuid
    definition.id = str(_uuid.uuid4())
    engine.register_workflow(definition)
    return _definition_to_response(definition)


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(
    request: Request,
    tag: str | None = Query(default=None),
):
    engine = _get_engine(request)
    definitions = engine.list_workflows()
    if tag:
        definitions = [w for w in definitions if tag in w.tags]
    return [_definition_to_response(w) for w in definitions]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, request: Request):
    engine = _get_engine(request)
    definition = engine.get_workflow(workflow_id)
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return _definition_to_response(definition)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(workflow_id: str, body: WorkflowUpdate, request: Request):
    engine = _get_engine(request)
    definition = engine.get_workflow(workflow_id)
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    if body.name is not None:
        definition.name = body.name
    if body.description is not None:
        definition.description = body.description
    if body.version is not None:
        definition.version = body.version
    if body.tags is not None:
        definition.tags = body.tags
    if body.metadata is not None:
        definition.metadata = body.metadata
    engine.register_workflow(definition)
    return _definition_to_response(definition)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: str, request: Request):
    engine = _get_engine(request)
    engine._workflow_registry.unregister(workflow_id)


# --- Execution management ---


@router.post(
    "/executions",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_execution(body: WorkflowExecutionCreate, request: Request):
    engine = _get_engine(request)
    execution = await engine.create_execution(
        workflow_id=body.workflow_id,
        input_data=body.input,
        user_id=body.user_id,
        session_id=body.session_id,
        tags=body.tags,
        metadata=body.metadata,
    )
    return _execution_to_response(execution)


@router.get("/executions", response_model=list[WorkflowExecutionResponse])
async def list_executions(
    request: Request,
    workflow_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    engine = _get_engine(request)
    executions = engine.list_executions(
        workflow_id=workflow_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [_execution_to_response(e) for e in executions]


@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_execution(execution_id: str, request: Request):
    engine = _get_engine(request)
    execution = engine.get_execution(execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )
    return _execution_to_response(execution)


@router.post("/executions/{execution_id}/start", response_model=WorkflowExecutionResponse)
async def start_execution(execution_id: str, request: Request):
    engine = _get_engine(request)
    execution = await engine.start_execution(execution_id)
    return _execution_to_response(execution)


@router.post("/executions/{execution_id}/action", response_model=WorkflowExecutionResponse)
async def execute_action(
    execution_id: str, body: WorkflowExecutionAction, request: Request
):
    engine = _get_engine(request)
    action = body.action.lower()

    if action == "pause":
        execution = await engine.pause_execution(execution_id)
    elif action == "resume":
        execution = await engine.resume_execution(execution_id)
    elif action == "cancel":
        execution = await engine.cancel_execution(execution_id)
    elif action == "rollback":
        execution = await engine.rollback_execution(execution_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action: {action}. Supported: pause, resume, cancel, rollback",
        )
    return _execution_to_response(execution)


# --- Events ---


@router.get("/executions/{execution_id}/events")
async def get_execution_events(execution_id: str, request: Request):
    engine = _get_engine(request)
    events = engine.get_events(execution_id)
    return [e.to_dict() for e in events]


# -- Helpers --


def _definition_to_response(d: WorkflowDefinition) -> dict:
    import uuid

    steps = []
    for s in d.steps:
        step_dict = s if isinstance(s, dict) else s.to_dict() if hasattr(s, "to_dict") else {}
        steps.append(step_dict)

    return {
        "id": d.id if isinstance(d.id, str) else str(d.id),
        "name": d.name,
        "description": d.description,
        "version": d.version,
        "steps": steps,
        "input_schema": d.input_schema,
        "output_schema": d.output_schema,
        "tags": d.tags,
        "metadata": d.metadata,
    }


def _execution_to_response(e) -> dict:
    steps = []
    for s in e.step_executions:
        se = s.to_dict() if hasattr(s, "to_dict") else (s if isinstance(s, dict) else {})
        steps.append(se)

    return {
        "id": e.id if isinstance(e.id, str) else str(e.id),
        "workflow_id": e.workflow_id,
        "workflow_name": e.workflow_name,
        "status": e.status.value if hasattr(e.status, "value") else str(e.status),
        "error": e.error,
        "current_step_id": e.current_step_id,
        "input": e.input,
        "output": e.output,
        "steps": steps,
        "created_at": e.created_at,
        "started_at": e.started_at,
        "completed_at": e.completed_at,
        "duration_ms": e.duration_ms,
        "user_id": e.user_id,
        "tags": e.tags,
        "metadata": e.metadata,
    }
