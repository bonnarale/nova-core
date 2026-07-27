"""Integration API routes for the System Integration subsystem."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["integration"])

_engine: Any = None


def set_dependencies(engine: Any = None) -> None:
    global _engine
    _engine = engine


@router.get("/integration/health", summary="Unified health check")
async def integration_health() -> dict[str, Any]:
    if _engine:
        status = await _engine.perform_health_check()
        return {"success": True, "data": status.to_dict()}
    return {"success": True, "data": {"status": "unknown", "message": "No integration engine"}}


@router.get("/integration/status", summary="Integration status")
async def integration_status() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_status()}
    return {"success": True, "data": {"state": "unknown"}}


@router.get("/integration/components", summary="List registered components")
async def integration_components() -> dict[str, Any]:
    if _engine:
        components = await _engine.coordinator.list_components()
        return {"success": True, "data": {"components": components, "total": len(components)}}
    return {"success": True, "data": {"components": [], "total": 0}}


@router.get("/integration/dependencies", summary="Dependency graph")
async def integration_dependencies() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.generate_dependency_graph()}
    return {"success": True, "data": {"nodes": [], "edges": []}}


@router.get("/integration/diagnostics", summary="System diagnostics")
async def integration_diagnostics() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.generate_diagnostics()}
    return {"success": True, "data": {}}


@router.get("/integration/compatibility", summary="Compatibility report")
async def integration_compatibility() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_compatibility_report()}
    return {"success": True, "data": {"compatible": True, "checks": [], "issues": []}}


@router.get("/integration/metrics", summary="Integration metrics")
async def integration_metrics() -> dict[str, Any]:
    if _engine:
        metrics = _engine.get_metrics()
        return {"success": True, "data": metrics.to_dict()}
    return {"success": True, "data": {}}


@router.get("/integration/traces", summary="Integration traces")
async def integration_traces(limit: int = 50) -> dict[str, Any]:
    if _engine:
        traces = _engine.get_traces(limit)
        return {"success": True, "data": {"traces": traces, "total": len(traces)}}
    return {"success": True, "data": {"traces": [], "total": 0}}


@router.post("/integration/validate", summary="Validate integrations")
async def integration_validate() -> dict[str, Any]:
    if _engine:
        results = await _engine.validate_integrations()
        findings = [r.to_dict() for r in results]
        valid = not any(r.severity.value in ("error", "critical") for r in results)
        return {"success": True, "data": {"valid": valid, "findings": findings, "summary": {"total": len(findings)}}}
    return {"success": True, "data": {"valid": True, "findings": [], "summary": {"total": 0}}}


@router.post("/integration/reinitialize", summary="Reinitialize components")
async def integration_reinitialize(components: list[str] | None = None) -> dict[str, Any]:
    if _engine:
        results = await _engine.reinitialize(components)
        return {"success": True, "data": {"results": results, "total": len(results)}}
    return {"success": True, "data": {"results": {}, "total": 0}}
