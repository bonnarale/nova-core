"""Projects API endpoints — manage Projects with Goal/Workflow lifecycle."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.command_center.schemas import ApprovalBudget

router = APIRouter(prefix="/projects", tags=["Projects"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    objective: str | None = Field(default=None, description="Optional business objective text to create a linked Goal and Workflow")
    user_id: str = Field(default="default", description="User ID for goal creation")


class ActivateProjectRequest(BaseModel):
    pass  # No body needed — activation uses existing workflow


class SetBudgetRequest(BaseModel):
    max_critical: int = Field(default=5, ge=1, le=100)
    max_high: int = Field(default=10, ge=1, le=200)
    max_total: int = Field(default=50, ge=1, le=1000)
    period: str = Field(default="monthly", pattern=r"^(daily|weekly|monthly)$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_bridge(request: Request):
    bridge = getattr(request.app.state, "project_goal_bridge", None)
    if bridge is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ProjectGoalBridge not available",
        )
    return bridge


def _get_projects_mgr(request: Request):
    mgr = getattr(request.app.state, "projects_manager", None)
    if mgr is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ProjectsManager not available",
        )
    return mgr


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(body: CreateProjectRequest, request: Request) -> dict:
    """Create a project. If objective text is provided, also creates a linked Goal and Workflow."""
    bridge = _get_bridge(request)

    if body.objective:
        project = await bridge.create_project_from_objective(
            user_id=body.user_id,
            title=body.title,
            description=body.objective,
        )
    else:
        mgr = _get_projects_mgr(request)
        project = await mgr.create_async(
            name=body.title,
            description=body.description,
        )

    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "goal_id": project.goal_id,
        "workflow_id": project.workflow_id,
    }


@router.get("/{project_id}")
async def get_project(project_id: str, request: Request) -> dict:
    """Get project with goal, workflow, budget, and decisions."""
    bridge = _get_bridge(request)
    result = await bridge.get_project_with_goal(project_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return result


@router.post("/{project_id}/activate")
async def activate_project(project_id: str, request: Request) -> dict:
    """Activate a project — generates workflow if not already linked."""
    mgr = _get_projects_mgr(request)
    project = await mgr.get_async(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.status == "active":
        return {"id": project.id, "status": "active", "message": "Already active"}

    updated = await mgr.update_async(project_id, status="active")
    return {
        "id": updated.id,
        "status": updated.status,
        "message": "Project activated",
    }


@router.get("/{project_id}/decisions")
async def list_decisions(project_id: str, request: Request) -> dict:
    """List decision history for a project."""
    mgr = _get_projects_mgr(request)
    project = await mgr.get_async(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return {
        "project_id": project.id,
        "decisions": [d.__dict__ for d in project.decision_history],
        "count": len(project.decision_history),
    }


@router.post("/{project_id}/budget")
async def set_budget(project_id: str, body: SetBudgetRequest, request: Request) -> dict:
    """Set or update the approval budget for a project."""
    mgr = _get_projects_mgr(request)
    project = await mgr.get_async(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    from datetime import datetime, timezone

    # Preserve existing usage counters when updating budget limits
    old_budget = project.approval_budget
    budget = ApprovalBudget(
        max_critical=body.max_critical,
        max_high=body.max_high,
        max_total=body.max_total,
        period=body.period,
        period_start=datetime.now(timezone.utc).isoformat(),
        used_critical=old_budget.used_critical if old_budget else 0,
        used_high=old_budget.used_high if old_budget else 0,
        used_total=old_budget.used_total if old_budget else 0,
    )
    updated = await mgr.update_async(project_id, approval_budget=budget)
    return {
        "project_id": updated.id,
        "budget": budget.__dict__,
        "message": "Budget set",
    }


# ---------------------------------------------------------------------------
# Documents endpoints
# ---------------------------------------------------------------------------

class AddDocumentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(description="Document type: proposal, report, contract, invoice")
    content: str = Field(description="Document content in markdown")
    status: str = Field(default="draft", description="Status: draft, pending_approval, approved, rejected")


@router.get("/{project_id}/documents")
async def list_documents(project_id: str, request: Request) -> dict:
    """List all documents for a project."""
    mgr = _get_projects_mgr(request)
    project = await mgr.get_async(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    docs = getattr(project, "documents", []) or []
    return {
        "project_id": project.id,
        "documents": docs,
        "count": len(docs),
    }


@router.post("/{project_id}/documents", status_code=status.HTTP_201_CREATED)
async def add_document(project_id: str, body: AddDocumentRequest, request: Request) -> dict:
    """Add a document to a project."""
    import uuid
    from datetime import datetime, timezone

    mgr = _get_projects_mgr(request)
    project = await mgr.get_async(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    doc = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "type": body.type,
        "content": body.content,
        "status": body.status,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    docs = getattr(project, "documents", []) or []
    docs.append(doc)
    await mgr.update_async(project_id, documents=docs)

    return {
        "project_id": project.id,
        "document": doc,
        "message": "Document added",
    }


@router.patch("/{project_id}/documents/{doc_id}")
async def update_document_status(
    project_id: str,
    doc_id: str,
    request: Request,
    status: str | None = None,
) -> dict:
    """Update a document's status (e.g., approve, reject)."""
    mgr = _get_projects_mgr(request)
    project = await mgr.get_async(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    docs = getattr(project, "documents", []) or []
    for doc in docs:
        if doc.get("id") == doc_id:
            if status:
                doc["status"] = status
            await mgr.update_async(project_id, documents=docs)
            return {
                "project_id": project.id,
                "document": doc,
                "message": "Document updated",
            }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Document not found",
    )


@router.delete("/{project_id}/documents/{doc_id}")
async def delete_document(project_id: str, doc_id: str, request: Request) -> dict:
    """Delete a document from a project."""
    mgr = _get_projects_mgr(request)
    project = await mgr.get_async(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    docs = getattr(project, "documents", []) or []
    new_docs = [d for d in docs if d.get("id") != doc_id]
    if len(new_docs) == len(docs):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    await mgr.update_async(project_id, documents=new_docs)
    return {
        "project_id": project.id,
        "message": "Document deleted",
    }
