"""Agent management API endpoints — Chapter 14 Multi-Agent Runtime."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.agents.agent_manager import AgentManager

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
# CRUD endpoints — adapted to AgentManager's real interface
# ------------------------------------------------------------------


@router.get("")
async def list_agents(request: Request) -> dict:
    """List all registered runtime agents."""
    manager: AgentManager = request.app.state.agent_manager
    runtime_ids = [a.agent_id for a in manager.list_runtime_agents()]
    return {
        "runtime_agents": runtime_ids,
        "count": len(runtime_ids),
    }


@router.get("/available")
async def list_available_agents(request: Request) -> list[dict]:
    """List all available agents with their details for task assignment."""
    manager: AgentManager = request.app.state.agent_manager
    agents = []
    # Access the internal _agents dict to get actual agent objects
    for agent_id, agent in manager._agents.items():
        # Try to get definition from the agent object
        definition = getattr(agent, "definition", None)
        if definition:
            agents.append({
                "id": agent_id,
                "name": getattr(definition, "name", agent_id),
                "role": getattr(definition, "role", "unknown"),
                "description": getattr(definition, "description", ""),
            })
        else:
            agents.append({
                "id": agent_id,
                "name": agent_id,
                "role": "agent",
                "description": f"Agent: {agent_id}",
            })
    return agents


@router.get("/health")
async def health_check(request: Request) -> dict:
    """Health check for all registered agents.

    AgentManager agents don't expose a health() method, so we report
    presence as the health signal.
    """
    manager: AgentManager = request.app.state.agent_manager
    results = {}
    for agent in manager.list_runtime_agents():
        results[agent.agent_id] = {"status": "registered"}
    return {"agents": results}


@router.get("/capabilities")
async def get_capabilities(request: Request) -> dict:
    """Get capabilities of all registered agents.

    AgentManager agents don't expose a definition object, so we report
    agent_id as the only known attribute.
    """
    manager: AgentManager = request.app.state.agent_manager
    caps = {}
    for agent in manager.list_runtime_agents():
        caps[agent.agent_id] = {
            "agent_id": agent.agent_id,
        }
    return {"capabilities": caps}


@router.get("/{agent_id}")
async def get_agent(agent_id: str, request: Request) -> dict:
    """Get an agent by ID.

    Returns runtime presence info. AgentManager does not store
    definitions, so definition fields are not available.
    """
    manager: AgentManager = request.app.state.agent_manager
    agent = manager.get_runtime_agent(agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
    return {
        "agent_id": agent.agent_id,
        "runtime_available": True,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(body: CreateAgentRequest, request: Request) -> dict:
    """Register a new agent at runtime.

    AgentManager.register() requires an agent object with an execute()
    method — dynamic creation from JSON definitions is not supported.
    Use POST /agents/{agent_id}/register-with-sdk for programmatic registration,
    or register agents in main.py during startup.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Dynamic agent creation from JSON is not supported. "
            "AgentManager.register() requires an agent object with an execute() method. "
            "Register agents programmatically at startup via main.py."
        ),
    )


@router.patch("/{agent_id}")
async def update_agent(agent_id: str, body: UpdateAgentRequest, request: Request) -> dict:
    """Update an agent.

    AgentManager does not support updating registered agents.
    Agents are immutable once registered — unregister and re-register
    with a new instance to change behavior.
    """
    manager: AgentManager = request.app.state.agent_manager
    agent = manager.get_runtime_agent(agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "AgentManager does not support in-place updates. "
            "Unregister the agent and register a new instance instead."
        ),
    )


@router.delete("/{agent_id}", status_code=status.HTTP_200_OK)
async def delete_agent(agent_id: str, request: Request) -> dict[str, str]:
    """Unregister an agent by ID."""
    manager: AgentManager = request.app.state.agent_manager
    agent = manager.get_runtime_agent(agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
    manager.unregister(agent_id)
    return {"status": "deleted", "agent_id": agent_id}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_agent(body: CreateAgentRequest, request: Request) -> dict:
    """Register an agent at runtime.

    Same constraint as POST /agents — requires an agent object.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Dynamic agent registration from JSON is not supported. "
            "AgentManager.register() requires an agent object with an execute() method. "
            "Register agents programmatically at startup via main.py."
        ),
    )


# ------------------------------------------------------------------
# Runtime endpoints — depend on AgentRuntime (not yet initialized)
# ------------------------------------------------------------------


@router.post("/runtime/dispatch")
async def runtime_dispatch(body: DispatchRequest, request: Request) -> dict:
    """Dispatch a task via the AgentRuntime."""
    runtime = getattr(request.app.state, "agent_runtime", None)
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
    runtime = getattr(request.app.state, "agent_runtime", None)
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
    runtime = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        return {"metrics": {}}
    return {"metrics": runtime.metrics.snapshot()}


@router.get("/runtime/traces")
async def runtime_traces(request: Request) -> dict:
    """Get runtime execution traces."""
    runtime = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        return {"traces": []}
    return {"traces": runtime.tracer.to_dict()}


@router.get("/runtime/scheduler")
async def runtime_scheduler(request: Request) -> dict:
    """Get scheduler status."""
    runtime = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        return {"scheduler": {}}
    return {"scheduler": runtime.scheduler.to_dict()}


@router.post("/runtime/cancel/{task_id}")
async def runtime_cancel(task_id: str, request: Request) -> dict:
    """Cancel a scheduled task."""
    runtime = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AgentRuntime not initialized",
        )
    cancelled = await runtime.cancel(task_id)
    return {"cancelled": cancelled, "task_id": task_id}
