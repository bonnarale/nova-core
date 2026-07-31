"""Resilience API routes for the Production Hardening subsystem."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["resilience"])

_engine: Any = None


def set_dependencies(engine: Any = None) -> None:
    global _engine
    _engine = engine


@router.get("/resilience/health", summary="Resilience health check")
async def resilience_health() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_health()}
    return {"success": True, "data": {"status": "unknown"}}


@router.get("/resilience/status", summary="Resilience status")
async def resilience_status() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_status()}
    return {"success": True, "data": {"state": "unknown"}}


@router.get("/resilience/circuit-breakers", summary="Circuit breaker status")
async def resilience_circuit_breakers() -> dict[str, Any]:
    if _engine:
        summary = _engine.circuit_breakers.get_summary()
        breakers = [b.get_stats() for b in _engine.circuit_breakers.get_all().values()]
        return {"success": True, "data": {"breakers": breakers, "summary": summary}}
    return {"success": True, "data": {"breakers": [], "summary": {}}}


@router.get("/resilience/retries", summary="Retry statistics")
async def resilience_retries() -> dict[str, Any]:
    if _engine:
        stats = _engine.retry.get_stats()
        return {"success": True, "data": stats}
    return {"success": True, "data": {"total": 0, "by_policy": {}, "success_rate": 1.0}}


@router.get("/resilience/failovers", summary="Failover events")
async def resilience_failovers() -> dict[str, Any]:
    if _engine:
        events = _engine.failover.get_events()
        return {"success": True, "data": {"events": events, "total": len(events)}}
    return {"success": True, "data": {"events": [], "total": 0}}


@router.get("/resilience/recoveries", summary="Recovery history")
async def resilience_recoveries() -> dict[str, Any]:
    if _engine:
        events = _engine.recovery.get_history()
        return {"success": True, "data": {"events": events, "total": len(events)}}
    return {"success": True, "data": {"events": [], "total": 0}}


@router.get("/resilience/diagnostics", summary="Resilience diagnostics")
async def resilience_diagnostics() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_diagnostics()}
    return {"success": True, "data": {}}


@router.get("/resilience/metrics", summary="Resilience metrics")
async def resilience_metrics() -> dict[str, Any]:
    if _engine:
        m = _engine.get_metrics()
        return {"success": True, "data": m.to_dict()}
    return {"success": True, "data": {}}


@router.get("/resilience/traces", summary="Resilience traces")
async def resilience_traces(limit: int = 50) -> dict[str, Any]:
    if _engine:
        traces = _engine.get_traces(limit)
        return {"success": True, "data": {"traces": traces, "total": len(traces)}}
    return {"success": True, "data": {"traces": [], "total": 0}}


@router.post("/resilience/reset", summary="Reset resilience state")
async def resilience_reset(components: list[str] | None = None) -> dict[str, Any]:
    if _engine:
        await _engine.reset(components)
        return {"success": True, "data": {"message": "Reset complete"}}
    return {"success": True, "data": {"message": "No engine"}}


@router.post("/resilience/recover", summary="Recover a component")
async def resilience_recover(component: str) -> dict[str, Any]:
    if _engine:
        success = await _engine.recover(component)
        return {"success": True, "data": {"component": component, "recovered": success}}
    return {"success": True, "data": {"component": component, "recovered": False}}
