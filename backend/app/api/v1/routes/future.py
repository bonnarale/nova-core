"""Future Roadmap API routes for the Future subsystem."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["future"])

_registry: Any = None


def set_dependencies(registry: Any = None) -> None:
    global _registry
    _registry = registry


@router.get("/future/features", summary="Feature flags")
async def future_features() -> dict[str, Any]:
    if _registry:
        flags = _registry.feature_flags.list_flags()
        summary = _registry.feature_flags.summary()
        return {
            "success": True,
            "data": {
                "total": summary["total"],
                "enabled": summary["enabled"],
                "disabled": summary["disabled"],
                "flags": [f.to_dict() for f in flags],
            },
        }
    return {"success": True, "data": {"total": 0, "enabled": 0, "disabled": 0, "flags": []}}


@router.get("/future/experiments", summary="Experiments")
async def future_experiments() -> dict[str, Any]:
    if _registry:
        experiments = _registry.experiments.get_experiments()
        summary = _registry.experiments.summary()
        return {
            "success": True,
            "data": {
                "total": summary["total"],
                "by_state": summary["by_state"],
                "experiments": [e.to_dict() for e in experiments],
            },
        }
    return {"success": True, "data": {"total": 0, "by_state": {}, "experiments": []}}


@router.get("/future/capabilities", summary="Capabilities")
async def future_capabilities() -> dict[str, Any]:
    if _registry:
        caps = _registry.capabilities.list_capabilities()
        summary = _registry.capabilities.summary()
        return {
            "success": True,
            "data": {
                "total": summary["total"],
                "by_state": summary["by_state"],
                "capabilities": [c.to_dict() for c in caps],
            },
        }
    return {"success": True, "data": {"total": 0, "by_state": {}, "capabilities": []}}


@router.get("/future/compatibility", summary="Compatibility report")
async def future_compatibility() -> dict[str, Any]:
    if _registry:
        report = _registry.compatibility.get_compatibility_report()
        return {"success": True, "data": report}
    return {"success": True, "data": {"components": {}, "checks": 0, "full": 0, "partial": 0, "incompatible": 0}}


@router.get("/future/deprecations", summary="Deprecations")
async def future_deprecations() -> dict[str, Any]:
    if _registry:
        entries = _registry.deprecation.get_entries()
        summary = _registry.deprecation.summary()
        return {
            "success": True,
            "data": {
                "total": summary["total"],
                "by_severity": summary["by_severity"],
                "deprecations": [e.to_dict() for e in entries],
            },
        }
    return {"success": True, "data": {"total": 0, "by_severity": {}, "deprecations": []}}


@router.get("/future/roadmap", summary="Roadmap")
async def future_roadmap() -> dict[str, Any]:
    if _registry:
        items = _registry.roadmap.list_items()
        summary = _registry.roadmap.summary()
        return {
            "success": True,
            "data": {
                "total": summary["total"],
                "by_state": summary["by_state"],
                "items": [i.to_dict() for i in items],
            },
        }
    return {"success": True, "data": {"total": 0, "by_state": {}, "items": []}}


@router.get("/future/metrics", summary="Future metrics")
async def future_metrics() -> dict[str, Any]:
    if _registry:
        return {"success": True, "data": _registry.metrics.summary()}
    return {"success": True, "data": {"metric_names": [], "total_points": 0, "by_name": {}}}


@router.get("/future/statistics", summary="Future statistics")
async def future_statistics() -> dict[str, Any]:
    if _registry:
        return {"success": True, "data": _registry.summary()}
    return {"success": True, "data": {}}
