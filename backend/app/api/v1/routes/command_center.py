"""NOVA Command Center API routes."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException
from app.command_center import CommandCenter, CommandRequest

router = APIRouter(prefix="/command-center", tags=["command-center"])
_cc = None

def _get():
    global _cc
    if _cc is None:
        from app.command_center import CommandCenterFactory
        _cc = CommandCenterFactory.create_all().get("command_center") or CommandCenter()
    return _cc

# System
@router.get("/status")
async def get_status() -> dict[str, Any]:
    return await _get().get_status()

@router.get("/lifecycle")
async def get_lifecycle() -> dict[str, Any]:
    return _get().lifecycle.__dict__

# Objectives
@router.get("/objectives")
async def list_objectives(status: str | None = None) -> list[dict[str, Any]]:
    return [o.__dict__ for o in _get().objectives.list_all(status=status)]

@router.post("/objectives")
async def create_objective(data: dict[str, Any]) -> dict[str, Any]:
    obj = _get().objectives.create(data.get("title", ""), data.get("description", ""), data.get("category", "general"), data.get("priority", 3))
    return obj.__dict__

@router.get("/objectives/active")
async def list_active_objectives() -> list[dict[str, Any]]:
    return [o.__dict__ for o in _get().objectives.list_active()]

@router.get("/objectives/backlog")
async def list_backlog_objectives() -> list[dict[str, Any]]:
    return [o.__dict__ for o in _get().objectives.list_backlog()]

@router.post("/objectives/{objective_id}/complete")
async def complete_objective(objective_id: str) -> dict[str, Any]:
    result = _get().objectives.complete(objective_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Objective not found")
    return result.__dict__

@router.post("/objectives/{objective_id}/progress")
async def update_progress(objective_id: str, data: dict[str, Any]) -> dict[str, Any]:
    result = _get().objectives.update_progress(objective_id, data.get("progress", 0.0))
    if result is None:
        raise HTTPException(status_code=404, detail="Objective not found")
    return result.__dict__

# Projects
@router.get("/projects")
async def list_projects(status: str | None = None) -> list[dict[str, Any]]:
    return [p.__dict__ for p in _get().projects.list_all(status=status)]

@router.post("/projects")
async def create_project(data: dict[str, Any]) -> dict[str, Any]:
    proj = _get().projects.create(data.get("name", ""), data.get("description", ""), data.get("objective_id"))
    return proj.__dict__

@router.post("/projects/{project_id}/complete")
async def complete_project(project_id: str) -> dict[str, Any]:
    result = _get().projects.complete(project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return result.__dict__

# Roadmap
@router.get("/roadmap")
async def list_roadmaps() -> list[dict[str, Any]]:
    return [r.__dict__ for r in _get().roadmap.list_all()]

@router.post("/roadmap")
async def create_roadmap(data: dict[str, Any]) -> dict[str, Any]:
    rm = _get().roadmap.create(data.get("name", ""), data.get("description", ""), data.get("duration_years", 1))
    return rm.__dict__

# Backlog
@router.get("/backlog")
async def list_backlog(status: str | None = None, category: str | None = None) -> list[dict[str, Any]]:
    return [i.__dict__ for i in _get().backlog.list_items(status=status, category=category)]

@router.post("/backlog")
async def add_backlog_item(data: dict[str, Any]) -> dict[str, Any]:
    item = _get().backlog.add(data.get("title", ""), data.get("description", ""), data.get("category", "general"), data.get("priority", 3), data.get("source", "user"))
    return item.__dict__

@router.post("/backlog/{item_id}/approve")
async def approve_backlog_item(item_id: str) -> dict[str, Any]:
    result = _get().backlog.approve(item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return result.__dict__

# Milestones
@router.get("/milestones")
async def list_milestones(status: str | None = None) -> list[dict[str, Any]]:
    return [m.__dict__ for m in _get().milestones.list_all(status=status)]

@router.post("/milestones")
async def create_milestone(data: dict[str, Any]) -> dict[str, Any]:
    ms = _get().milestones.create(data.get("title", ""), data.get("description", ""), data.get("objective_id"), data.get("project_id"), data.get("due_date"))
    return ms.__dict__

@router.post("/milestones/{milestone_id}/complete")
async def complete_milestone(milestone_id: str) -> dict[str, Any]:
    result = _get().milestones.complete(milestone_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return result.__dict__

# Approvals
@router.get("/approvals/pending")
async def get_pending_approvals() -> list[dict[str, Any]]:
    return [a.__dict__ for a in _get().approvals.get_pending()]

@router.post("/approvals/request")
async def request_approval(data: dict[str, Any]) -> dict[str, Any]:
    result = _get().approvals.request(data.get("action_type", ""), data.get("description", ""), data.get("risk_level", "low"), data.get("requester", "nova"), data.get("metadata"))
    return result.__dict__

@router.post("/approvals/{approval_id}/approve")
async def approve_action(approval_id: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    data = data or {}
    result = _get().approvals.approve(approval_id, data.get("reviewer", "user"), data.get("reason"))
    if result is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return result.__dict__

@router.post("/approvals/{approval_id}/reject")
async def reject_action(approval_id: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    data = data or {}
    result = _get().approvals.reject(approval_id, data.get("reviewer", "user"), data.get("reason"))
    if result is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return result.__dict__

# Governor / Analysis
@router.post("/analyze")
async def analyze_objective(data: dict[str, Any]) -> dict[str, Any]:
    return await _get().governor.analyze_objective(data.get("objective", ""))

@router.post("/plan")
async def create_plan(data: dict[str, Any]) -> dict[str, Any]:
    return await _get().governor.create_plan(data.get("analysis", {}))

@router.post("/orchestrate")
async def orchestrate(data: dict[str, Any]) -> dict[str, Any]:
    return await _get().orchestrator.orchestrate(data.get("objective", ""))

# Decisions
@router.get("/decisions")
async def list_decisions(decision_type: str | None = None) -> list[dict[str, Any]]:
    return [d.__dict__ for d in _get().decisions.list_decisions(decision_type)]

# Recommendations
@router.get("/recommendations")
async def list_recommendations(status: str | None = None) -> list[dict[str, Any]]:
    return [r.__dict__ for r in _get().recommendations.list_all(status=status)]

@router.post("/recommendations")
async def create_recommendation(data: dict[str, Any]) -> dict[str, Any]:
    rec = _get().recommendations.create(data.get("category", ""), data.get("title", ""), data.get("description", ""), data.get("priority", "medium"), data.get("impact", ""), data.get("effort", ""))
    return rec.__dict__

@router.post("/recommendations/{rec_id}/accept")
async def accept_recommendation(rec_id: str) -> dict[str, Any]:
    result = _get().recommendations.accept(rec_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return result.__dict__

# Optimization
@router.get("/optimization")
async def list_optimizations() -> list[dict[str, Any]]:
    return [o.__dict__ for o in _get().optimization.list_all()]

@router.post("/optimization")
async def create_optimization(data: dict[str, Any]) -> dict[str, Any]:
    opt = _get().optimization.analyze(data.get("category", ""), data.get("current_state", ""), data.get("proposed_state", ""), data.get("improvement", ""), data.get("priority", 3), data.get("estimated_impact", ""))
    return opt.__dict__

# Metrics
@router.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    return _get().metrics.snapshot()

# Tracing
@router.get("/traces")
async def get_traces(limit: int = 50) -> list[dict[str, Any]]:
    return _get().tracing.list_spans(limit=limit)
