"""Autonomy API routes for the Autonomous Intelligence subsystem."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["autonomy"])

_engine: Any = None


def set_dependencies(engine: Any = None) -> None:
    global _engine
    _engine = engine


@router.get("/autonomy/status", summary="Autonomy status")
async def autonomy_status() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_status()}
    return {"success": True, "data": {"state": "unknown"}}


@router.get("/autonomy/objectives", summary="List objectives")
async def autonomy_objectives() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_objectives()}
    return {"success": True, "data": []}


@router.get("/autonomy/recommendations", summary="List recommendations")
async def autonomy_recommendations() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_recommendations()}
    return {"success": True, "data": []}


@router.get("/autonomy/reflections", summary="List reflections")
async def autonomy_reflections(limit: int = 50) -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_reflections(limit)}
    return {"success": True, "data": []}


@router.get("/autonomy/policies", summary="List policies")
async def autonomy_policies() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_policies()}
    return {"success": True, "data": {}}


@router.get("/autonomy/metrics", summary="Autonomy metrics")
async def autonomy_metrics() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_metrics()}
    return {"success": True, "data": {}}


@router.get("/autonomy/traces", summary="Autonomy traces")
async def autonomy_traces(limit: int = 50) -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_traces(limit)}
    return {"success": True, "data": []}


@router.post("/autonomy/evaluate", summary="Evaluate objectives")
async def autonomy_evaluate() -> dict[str, Any]:
    if _engine:
        result = await _engine.evaluate_objectives()
        return {"success": True, "data": result}
    return {"success": True, "data": []}


@router.post("/autonomy/recommend", summary="Generate recommendations")
async def autonomy_recommend() -> dict[str, Any]:
    if _engine:
        result = await _engine.recommend_improvements()
        return {"success": True, "data": result}
    return {"success": True, "data": []}


@router.post("/autonomy/approve", summary="Approve recommendation")
async def autonomy_approve(recommendation_id: str, approver: str = "human") -> dict[str, Any]:
    if _engine:
        success = await _engine.approve_recommendation(recommendation_id, approver)
        return {"success": True, "data": {"approved": success}}
    return {"success": True, "data": {"approved": False}}


@router.post("/autonomy/reject", summary="Reject recommendation")
async def autonomy_reject(recommendation_id: str, reason: str = "") -> dict[str, Any]:
    if _engine:
        success = await _engine.reject_recommendation(recommendation_id, reason)
        return {"success": True, "data": {"rejected": success}}
    return {"success": True, "data": {"rejected": False}}
