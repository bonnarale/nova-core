"""Autonomy evolution system API routes."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException
from app.autonomy.autonomy_engine import AutonomyEngine
from app.autonomy.objective_manager import ObjectiveManager
from app.autonomy.project_manager import ProjectManager
from app.autonomy.roadmap_manager import RoadmapManager
from app.autonomy.recommendation_engine import RecommendationEngine
from app.autonomy.optimization_engine import OptimizationEngine
from app.autonomy.self_improvement import SelfImprovementEngine
from app.autonomy.approval_engine import ApprovalEngine
from app.autonomy.delegation_engine import DelegationEngine
from app.autonomy.research_manager import ResearchManager

router = APIRouter(prefix="/autonomy-system", tags=["autonomy-system"])
_engine = None

def _get():
    global _engine
    if _engine is None:
        _engine = {
            "autonomy": AutonomyEngine(),
            "objectives": ObjectiveManager(),
            "projects": ProjectManager(),
            "roadmaps": RoadmapManager(),
            "recommendations": RecommendationEngine(),
            "optimization": OptimizationEngine(),
            "self_improvement": SelfImprovementEngine(),
            "approvals": ApprovalEngine(),
            "delegation": DelegationEngine(),
            "research": ResearchManager(),
        }
    return _engine

@router.get("/status")
async def get_status() -> dict[str, Any]:
    m = _get()
    return {
        "autonomy_level": m["autonomy"].get_level(),
        "active_objectives": len(m["objectives"].list_active()),
        "backlog": len(m["objectives"].list_backlog()),
        "projects": len(m["projects"].list_projects()),
        "roadmaps": len(m["roadmaps"].list_roadmaps()),
        "recommendations": len(m["recommendations"].get_pending()),
        "improvements": len(m["self_improvement"].list_items()),
        "pending_approvals": len(m["approvals"].get_pending()),
    }

@router.get("/autonomy")
async def get_autonomy() -> dict[str, Any]:
    return _get()["autonomy"].to_dict()

@router.post("/autonomy/level")
async def set_level(data: dict[str, Any]) -> dict[str, Any]:
    _get()["autonomy"].set_level(data.get("level", 0.5))
    return {"level": _get()["autonomy"].get_level()}

@router.get("/autonomy/capabilities")
async def get_capabilities() -> list[str]:
    return _get()["autonomy"].get_capabilities()

@router.post("/objectives/analyze")
async def analyze_objective(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["objectives"].analyze_objective(data.get("objective", ""))

@router.post("/objectives")
async def create_objective(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["objectives"].add_objective(data.get("title", ""), data.get("description", ""), data.get("priority", 3))

@router.get("/objectives")
async def list_objectives() -> dict[str, Any]:
    m = _get()
    return {"active": m["objectives"].list_active(), "backlog": m["objectives"].list_backlog()}

@router.post("/projects")
async def create_project(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["projects"].create_project(data.get("objective", data.get("name", "")))

@router.get("/projects")
async def list_projects() -> list[dict[str, Any]]:
    return _get()["projects"].list_projects()

@router.post("/roadmaps")
async def create_roadmap(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["roadmaps"].create_roadmap(data.get("objective", data.get("name", "")), data.get("duration_years", 1))

@router.get("/roadmaps")
async def list_roadmaps() -> list[dict[str, Any]]:
    return _get()["roadmaps"].list_roadmaps()

@router.get("/recommendations")
async def list_recommendations() -> list[dict[str, Any]]:
    return _get()["recommendations"].list_recommendations()

@router.post("/recommendations")
async def create_recommendation(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["recommendations"].generate_recommendation(data.get("category", ""), data.get("title", ""), data.get("description", ""), data.get("priority", "medium"), data.get("impact", ""), data.get("effort", ""))

@router.post("/recommendations/{rec_id}/accept")
async def accept_recommendation(rec_id: str) -> dict[str, Any]:
    result = _get()["recommendations"].accept_recommendation(rec_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return result

@router.get("/optimization")
async def list_optimizations() -> list[dict[str, Any]]:
    return _get()["optimization"].list_results()

@router.get("/self-improvement")
async def list_improvements() -> list[dict[str, Any]]:
    return _get()["self_improvement"].list_items()

@router.post("/self-improvement")
async def identify_improvement(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["self_improvement"].identify(data.get("category", ""), data.get("title", ""), data.get("description", ""), data.get("priority", 3))

@router.post("/self-improvement/{item_id}/approve")
async def approve_improvement(item_id: str) -> dict[str, Any]:
    result = _get()["self_improvement"].approve(item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Improvement not found")
    return result

@router.get("/approvals/pending")
async def get_pending_approvals() -> list[dict[str, Any]]:
    return _get()["approvals"].get_pending()

@router.post("/approvals/request")
async def request_approval(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["approvals"].request_approval(data.get("action_type", ""), data.get("description", ""), data.get("metadata"))

@router.post("/approvals/{approval_id}/approve")
async def approve_action(approval_id: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    data = data or {}
    result = _get()["approvals"].approve(approval_id, data.get("reviewer", "user"), data.get("reason"))
    if result is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return result

@router.post("/delegation")
async def delegate_task(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["delegation"].delegate(data.get("task_description", ""), data.get("delegation_type", "agent"), data.get("context"))

@router.get("/delegation")
async def list_delegations() -> list[dict[str, Any]]:
    return _get()["delegation"].list_tasks()

@router.post("/research")
async def submit_research(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["research"].submit_research(data.get("query", ""), data.get("depth", "standard"))

@router.get("/research")
async def list_research() -> list[dict[str, Any]]:
    return _get()["research"].list_research()
