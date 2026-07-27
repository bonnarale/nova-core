"""Plugin system API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.plugins.engine import PluginEngine
from app.plugins.factory import PluginFactory
from app.plugins.schemas import (
    ExecutePluginRequest,
    HookListResponse,
    HookStatisticsResponse,
    PluginConfigResponse,
    PluginEventsResponse,
    PluginExecutionResponse,
    PluginHealthResponse,
    PluginListResponse,
    PluginResponse,
    PluginStatisticsResponse,
    RegisterPluginRequest,
    SandboxStatsResponse,
)

router = APIRouter(prefix="/plugins", tags=["plugins"])

_engine: PluginEngine | None = None


def _get_engine() -> PluginEngine:
    global _engine
    if _engine is None:
        _engine = PluginFactory.create_engine()
    return _engine


@router.on_event("startup")
async def _startup() -> None:
    engine = _get_engine()
    await engine.start()


@router.get("/", response_model=PluginListResponse)
async def list_plugins() -> PluginListResponse:
    engine = _get_engine()
    plugins = engine.list_plugins()
    return PluginListResponse(total=len(plugins), plugins=[PluginResponse(**p) for p in plugins])


@router.get("/health", response_model=PluginHealthResponse)
async def health_check() -> PluginHealthResponse:
    engine = _get_engine()
    data = await engine.health()
    return PluginHealthResponse(**data)


@router.get("/statistics", response_model=PluginStatisticsResponse)
async def statistics() -> PluginStatisticsResponse:
    engine = _get_engine()
    data = engine.get_statistics()
    return PluginStatisticsResponse(**data)


@router.get("/{plugin_id}", response_model=PluginResponse)
async def get_plugin(plugin_id: str) -> PluginResponse:
    engine = _get_engine()
    try:
        data = engine.get_plugin(plugin_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")
    return PluginResponse(**data)


@router.post("/", response_model=PluginResponse)
async def register_plugin(request: RegisterPluginRequest) -> PluginResponse:
    engine = _get_engine()
    try:
        from app.plugins.manifest import ManifestValidator
        manifest = ManifestValidator.parse_manifest(request.manifest)
        info = await engine.register_and_start(manifest, request.config or None)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return PluginResponse(**info)


@router.delete("/{plugin_id}")
async def unregister_plugin(plugin_id: str) -> dict[str, str]:
    engine = _get_engine()
    try:
        await engine.stop_and_unregister(plugin_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "unregistered", "plugin_id": plugin_id}


@router.post("/{plugin_id}/enable")
async def enable_plugin(plugin_id: str) -> dict[str, str]:
    engine = _get_engine()
    try:
        await engine.manager.enable_plugin(plugin_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "enabled", "plugin_id": plugin_id}


@router.post("/{plugin_id}/disable")
async def disable_plugin(plugin_id: str) -> dict[str, str]:
    engine = _get_engine()
    try:
        await engine.manager.disable_plugin(plugin_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "disabled", "plugin_id": plugin_id}


@router.post("/{plugin_id}/execute", response_model=PluginExecutionResponse)
async def execute_plugin(plugin_id: str, request: ExecutePluginRequest) -> PluginExecutionResponse:
    engine = _get_engine()
    try:
        result = await engine.execute(plugin_id, request.operation, request.params or None)
        if isinstance(result, dict):
            return PluginExecutionResponse(
                success=result.get("error") is None,
                plugin_id=plugin_id,
                operation=request.operation,
                result=result,
                error=result.get("error", ""),
            )
        return PluginExecutionResponse(
            success=True,
            plugin_id=plugin_id,
            operation=request.operation,
            result=result,
        )
    except Exception as exc:
        return PluginExecutionResponse(
            success=False,
            plugin_id=plugin_id,
            operation=request.operation,
            error=str(exc),
        )


@router.get("/hooks/list", response_model=HookListResponse)
async def list_hooks() -> HookListResponse:
    engine = _get_engine()
    hooks = engine.manager.hooks.registry.list_all_hooks()
    return HookListResponse(
        total=len(hooks),
        hooks=[h.to_dict() for h in hooks],
    )


@router.get("/hooks/statistics", response_model=HookStatisticsResponse)
async def hook_statistics() -> HookStatisticsResponse:
    engine = _get_engine()
    stats = engine.manager.hooks.get_statistics()
    return HookStatisticsResponse(**stats)


@router.get("/sandbox/stats", response_model=SandboxStatsResponse)
async def sandbox_stats() -> SandboxStatsResponse:
    engine = _get_engine()
    stats = engine.manager.sandbox.get_stats()
    return SandboxStatsResponse(**stats)


@router.get("/events/recent", response_model=PluginEventsResponse)
async def recent_events(limit: int = 50) -> PluginEventsResponse:
    engine = _get_engine()
    events = engine.manager.event_bus.get_events(limit=limit)
    return PluginEventsResponse(
        total=len(events),
        events=[e.to_dict() for e in events],
    )
