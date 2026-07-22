"""Agent management API endpoints — Chapter 14 Multi-Agent Runtime."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.agents.agent_manager import AgentManager
from app.agents.runtime import AgentRuntime

router = APIRouter(prefix="/agents", tags=["Agents"])


class CreateAgentRequest(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=100)
    description: str = ""
    system_prompt: str = ""
    allowed_tools: list[str] = []
    memory_scope: str = "session"
    permissions: dict[str, Any] = {}
    supported_models: list[str] = []


class UpdateAgentRequest(BaseModel):
    name: str | None = None
    role: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    allowed_tools: list[str] | None = None
    memory_scope: str | None = None
    permissions: dict[str, Any] | None = None
    supported_models: list[str] | None = None
    status: str | None = Field(default=None, pattern=r"^(active|inactive)$")


class DispatchRequest(BaseModel):
    task: str = Field(min_length=1)
    context: dict[str, Any] = {}
    timeout: float | None = None


class CoordinateRequest(BaseModel):
    steps: list[dict[str, Any]]
    pattern: str = "sequential"
    aggregation_agent: str | None = None


# ------------------------------------------------------------------
# Existing endpoints (backward compatible)
# ------------------------------------------------------------------


@router.get("")
async def list_agents(request: Request) -> dict:
    """List all registered agent definitions."""
    manager: AgentManager = request.app.state.agent_manager
    definitions = await manager.list_agent_definitions()
    runtime_ids = [a.agent_id for a in manager.list_runtime_agents()]
    return {
        "definitions": definitions,
        "runtime_agents": runtime_ids,
        "tracing": manager.tracer.to_dict(),
        "metrics": manager.metrics.snapshot(),
    }


@router.get("/{agent_id}")
async def get_agent(agent_id: str, request: Request) -> dict:
    """Get an agent definition by ID."""
    manager: AgentManager = request.app.state.agent_manager
    definition = await manager.get_agent_definition(agent_id)
    runtime = manager.get_runtime_agent(agent_id)
    return {
        "definition": definition,
        "runtime_available": runtime is not None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(body: CreateAgentRequest, request: Request) -> dict:
    """Create a new agent definition."""
    manager: AgentManager = request.app.state.agent_manager
    result = await manager.create_agent_definition(
        agent_id=body.id,
        name=body.name,
        role=body.role,
        description=body.description,
        system_prompt=body.system_prompt,
        allowed_tools=body.allowed_tools,
        memory_scope=body.memory_scope,
        permissions=body.permissions,
        supported_models=body.supported_models,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent definition could not be created (may already exist)",
        )
    return result


@router.patch("/{agent_id}")
async def update_agent(agent_id: str, body: UpdateAgentRequest, request: Request) -> dict:
    """Update an agent definition."""
    manager: AgentManager = request.app.state.agent_manager
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields to update",
        )
    result = await manager.update_agent_definition(agent_id, **updates)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent definition not found",
        )
    return result


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str, request: Request) -> None:
    """Delete an agent definition."""
    manager: AgentManager = request.app.state.agent_manager
    deleted = await manager.delete_agent_definition(agent_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent definition not found",
        )


# ------------------------------------------------------------------
# Chapter 14 — Runtime endpoints
# ------------------------------------------------------------------


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_agent(body: CreateAgentRequest, request: Request) -> dict:
    """Register an agent definition."""
    manager: AgentManager = request.app.state.agent_manager
    result = await manager.create_agent_definition(
        agent_id=body.id,
        name=body.name,
        role=body.role,
        description=body.description,
        system_prompt=body.system_prompt,
        allowed_tools=body.allowed_tools,
        memory_scope=body.memory_scope,
        permissions=body.permissions,
        supported_models=body.supported_models,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent could not be registered",
        )
    return {"registered": True, "agent": result}


@router.get("/health")
async def health_check(request: Request) -> dict:
    """Health check for all registered agents."""
    manager: AgentManager = request.app.state.agent_manager
    results = {}
    for agent in manager.list_runtime_agents():
        try:
            h = await agent.health()
            results[agent.agent_id] = h
        except Exception as exc:
            results[agent.agent_id] = {"status": "error", "error": str(exc)}
    return {"agents": results}


@router.get("/capabilities")
async def get_capabilities(request: Request) -> dict:
    """Get capabilities of all registered agents."""
    manager: AgentManager = request.app.state.agent_manager
    caps = {}
    for agent in manager.list_runtime_agents():
        defn = agent.definition
        caps[agent.agent_id] = {
            "role": defn.role,
            "allowed_tools": list(defn.allowed_tools),
            "permissions": dict(defn.permissions),
            "supported_models": list(defn.supported_models),
        }
    return {"capabilities": caps}


@router.post("/runtime/dispatch")
async def runtime_dispatch(body: DispatchRequest, request: Request) -> dict:
    """Dispatch a task via the AgentRuntime."""
    runtime: AgentRuntime | None = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AgentRuntime not initialized",
        )
    result = await runtime.dispatch(
        agent_id=body.context.get("agent_id", "executor"),
        task=body.task,
        context=body.context,
        timeout=body.timeout,
    )
    return result


@router.post("/runtime/coordinate")
async def runtime_coordinate(body: CoordinateRequest, request: Request) -> dict:
    """Coordinate multi-agent execution via the AgentRuntime."""
    runtime: AgentRuntime | None = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AgentRuntime not initialized",
        )
    result = await runtime.coordinate(
        steps=body.steps,
        pattern=body.pattern,
        aggregation_agent=body.aggregation_agent,
    )
    return result


@router.get("/runtime/metrics")
async def runtime_metrics(request: Request) -> dict:
    """Get runtime metrics."""
    runtime: AgentRuntime | None = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        return {"metrics": {}}
    return {"metrics": runtime.metrics.snapshot()}


@router.get("/runtime/traces")
async def runtime_traces(request: Request) -> dict:
    """Get runtime execution traces."""
    runtime: AgentRuntime | None = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        return {"traces": []}
    return {"traces": runtime.tracer.to_dict()}


@router.get("/runtime/scheduler")
async def runtime_scheduler(request: Request) -> dict:
    """Get scheduler status."""
    runtime: AgentRuntime | None = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        return {"scheduler": {}}
    return {"scheduler": runtime.scheduler.to_dict()}


@router.post("/runtime/cancel/{task_id}")
async def runtime_cancel(task_id: str, request: Request) -> dict:
    """Cancel a scheduled task."""
    runtime: AgentRuntime | None = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AgentRuntime not initialized",
        )
    cancelled = await runtime.cancel(task_id)
    return {"cancelled": cancelled, "task_id": task_id}
