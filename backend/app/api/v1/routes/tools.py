"""Tool System API endpoints — Chapter 15 Tool System."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.tools.context import ToolContext
from app.tools.manager import ToolManager
from app.tools.runtime import ToolRuntime

router = APIRouter(prefix="/tools", tags=["Tools"])


class RegisterToolRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    category: str = "general"
    policy: str = "immediate"
    permission_level: str = "read"
    timeout: float = 30.0
    retries: int = 0


class ExecuteToolRequest(BaseModel):
    params: dict[str, Any] = {}
    agent_id: str = ""
    user_id: str = ""
    timeout: float | None = None
    retries: int | None = None


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.get("")
async def list_tools(request: Request) -> dict:
    """List all registered tools."""
    runtime: ToolRuntime | None = getattr(request.app.state, "tool_runtime", None)
    if runtime is None:
        return {"tools": []}
    specs = runtime.list_tools()
    return {"tools": [s.to_dict() for s in specs], "total": len(specs)}


@router.get("/metrics")
async def get_metrics(request: Request) -> dict:
    """Get tool execution metrics."""
    runtime: ToolRuntime | None = getattr(request.app.state, "tool_runtime", None)
    if runtime is None:
        return {"metrics": {}}
    return {"metrics": runtime.metrics.snapshot()}


@router.get("/traces")
async def get_traces(request: Request) -> dict:
    """Get tool execution traces."""
    runtime: ToolRuntime | None = getattr(request.app.state, "tool_runtime", None)
    if runtime is None:
        return {"traces": []}
    return {"traces": runtime.tracer.to_dict()}


@router.get("/{tool_id}")
async def get_tool(tool_id: str, request: Request) -> dict:
    """Get a specific tool by ID."""
    runtime: ToolRuntime | None = getattr(request.app.state, "tool_runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Tool runtime not initialized")
    tool = runtime.registry.get_tool(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found")
    return {"tool": tool.spec.to_dict()}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_tool(body: RegisterToolRequest, request: Request) -> dict:
    """Register a tool."""
    manager: ToolManager | None = getattr(request.app.state, "tool_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="Tool manager not initialized")
    existing = manager.get_tool(body.name)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Tool '{body.name}' already registered")
    from app.tools.base import Tool, ToolSpec, ToolParam
    from app.tools.result import ToolResult

    class _GenericTool(Tool):
        def __init__(self, spec_val: ToolSpec) -> None:
            self._spec = spec_val

        @property
        def spec(self) -> ToolSpec:
            return self._spec

        async def run(self, params: dict) -> ToolResult:
            return ToolResult(success=True, data={"registered": True})

    spec = ToolSpec(
        name=body.name,
        description=body.description,
        category=body.category,
        policy=body.policy,
        permission_level=body.permission_level,
        timeout_default=body.timeout,
        retry_default=body.retries,
    )
    tool = _GenericTool(spec)
    manager.register(tool, policy=body.policy)
    return {"registered": True, "tool": spec.to_dict()}


@router.delete("/{tool_id}", status_code=status.HTTP_200_OK)
async def unregister_tool(tool_id: str, request: Request) -> dict:
    """Unregister a tool."""
    manager: ToolManager | None = getattr(request.app.state, "tool_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="Tool manager not initialized")
    tool = manager.get_tool(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found")
    manager.unregister(tool_id)
    return {"status": "deleted"}


@router.post("/{tool_id}/execute")
async def execute_tool(tool_id: str, body: ExecuteToolRequest, request: Request) -> dict:
    """Execute a tool by ID."""
    runtime: ToolRuntime | None = getattr(request.app.state, "tool_runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Tool runtime not initialized")
    ctx = ToolContext(
        tool_id=tool_id,
        agent_id=body.agent_id,
        user_id=body.user_id,
    )
    result = await runtime.execute_tool(
        tool_name=tool_id,
        params=body.params,
        context=ctx,
        timeout=body.timeout,
        retries=body.retries,
    )
    return result.to_dict()


@router.get("/{tool_id}/health")
async def tool_health(tool_id: str, request: Request) -> dict:
    """Check health of a specific tool."""
    runtime: ToolRuntime | None = getattr(request.app.state, "tool_runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Tool runtime not initialized")
    tool = runtime.registry.get_tool(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found")
    try:
        h = await tool.health()
        return h
    except Exception as exc:
        return {"tool_id": tool_id, "status": "error", "error": str(exc)}
