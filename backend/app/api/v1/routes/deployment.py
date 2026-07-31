"""Deployment API routes for the Deployment subsystem."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["deployment"])

_deploy_manager: Any = None


def set_dependencies(manager: Any = None) -> None:
    global _deploy_manager
    _deploy_manager = manager


@router.get("/deployment/health", summary="Deployment health check")
async def deployment_health() -> dict[str, Any]:
    if _deploy_manager:
        return {"success": True, "data": await _deploy_manager.health()}
    return {"success": True, "data": {"status": "unknown", "message": "No deployment manager"}}


@router.get("/deployment/readiness", summary="Deployment readiness")
async def deployment_readiness() -> dict[str, Any]:
    if _deploy_manager:
        return {"success": True, "data": await _deploy_manager.readiness()}
    return {"success": True, "data": {"ready": True, "status": "no manager"}}


@router.get("/deployment/liveness", summary="Deployment liveness")
async def deployment_liveness() -> dict[str, Any]:
    if _deploy_manager:
        return {"success": True, "data": await _deploy_manager.liveness()}
    return {"success": True, "data": {"alive": True, "status": "no manager"}}


@router.get("/deployment/environment", summary="Environment variables")
async def deployment_environment() -> dict[str, Any]:
    if _deploy_manager:
        env = await _deploy_manager.environment()
        return {"success": True, "data": {"variables": env, "count": len(env)}}
    return {"success": True, "data": {"variables": {}, "count": 0}}


@router.get("/deployment/configuration", summary="Configuration")
async def deployment_configuration() -> dict[str, Any]:
    if _deploy_manager:
        config = _deploy_manager.configuration
        items = await config.get_all()
        validation = await config.validate()
        return {
            "success": True,
            "data": {
                "environment": config.environment.value,
                "items": items,
                "valid": validation["valid"],
            },
        }
    return {"success": True, "data": {"items": {}, "valid": True}}


@router.get("/deployment/diagnostics", summary="System diagnostics")
async def deployment_diagnostics() -> dict[str, Any]:
    if _deploy_manager:
        return {"success": True, "data": await _deploy_manager.diagnostics()}
    return {"success": True, "data": {}}


@router.get("/deployment/metrics", summary="Deployment metrics")
async def deployment_metrics() -> dict[str, Any]:
    if _deploy_manager:
        stats = _deploy_manager._metrics.get_statistics()
        return {"success": True, "data": stats}
    return {"success": True, "data": {}}


@router.get("/deployment/statistics", summary="Deployment statistics")
async def deployment_statistics() -> dict[str, Any]:
    if _deploy_manager:
        stats = await _deploy_manager.statistics()
        return {"success": True, "data": stats.to_dict()}
    return {"success": True, "data": {}}
