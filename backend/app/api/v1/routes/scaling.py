"""Scaling API routes for the Scaling subsystem."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["scaling"])

_engine: Any = None


def set_dependencies(engine: Any = None) -> None:
    global _engine
    _engine = engine


@router.get("/scaling/health", summary="Scaling health check")
async def scaling_health() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": (await _engine.health()).to_dict()}
    return {"success": True, "data": {"status": "unknown", "message": "No scaling engine"}}


@router.get("/scaling/metrics", summary="Scaling metrics")
async def scaling_metrics() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.metrics.get_statistics()}
    return {"success": True, "data": {}}


@router.get("/scaling/statistics", summary="Scaling statistics")
async def scaling_statistics() -> dict[str, Any]:
    if _engine:
        stats = await _engine.statistics()
        return {"success": True, "data": stats.to_dict()}
    return {"success": True, "data": {}}


@router.get("/scaling/workers", summary="Worker pool status")
async def scaling_workers() -> dict[str, Any]:
    if _engine:
        status = await _engine.worker_pool.get_status()
        workers = _engine.worker_pool.get_workers()
        return {"success": True, "data": {**status, "workers": workers}}
    return {"success": True, "data": {"pool_size": 0, "workers": []}}


@router.get("/scaling/queues", summary="Queue status")
async def scaling_queues() -> dict[str, Any]:
    if _engine:
        stats = _engine.queue_manager.get_statistics()
        queues = _engine.queue_manager.list_queues()
        return {"success": True, "data": {**stats, "queues": queues}}
    return {"success": True, "data": {"total_queues": 0, "queues": []}}


@router.get("/scaling/cache", summary="Cache statistics")
async def scaling_cache() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.cache.get_stats().to_dict()}
    return {"success": True, "data": {}}


@router.get("/scaling/resources", summary="Resource utilization")
async def scaling_resources() -> dict[str, Any]:
    if _engine:
        snapshot = _engine.resource_manager.get_current()
        return {"success": True, "data": snapshot.to_dict()}
    return {"success": True, "data": {}}


@router.post("/scaling/scale-up", summary="Scale up workers")
async def scaling_scale_up(amount: int = 1) -> dict[str, Any]:
    if _engine:
        result = await _engine.scale_up(amount)
        return {"success": True, "data": result}
    return {"success": False, "data": {"error": "No scaling engine"}}


@router.post("/scaling/scale-down", summary="Scale down workers")
async def scaling_scale_down(amount: int = 1) -> dict[str, Any]:
    if _engine:
        result = await _engine.scale_down(amount)
        return {"success": True, "data": result}
    return {"success": False, "data": {"error": "No scaling engine"}}


@router.post("/scaling/cache/clear", summary="Clear cache")
async def scaling_cache_clear() -> dict[str, Any]:
    if _engine:
        cleared = await _engine.cache.clear()
        return {"success": True, "data": {"cleared": cleared, "success": True}}
    return {"success": True, "data": {"cleared": 0, "success": True}}
