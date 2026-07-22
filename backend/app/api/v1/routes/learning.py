"""Learning Engine API endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.learning.schemas import (
    ArtifactListResponse,
    ArtifactResponse,
    ArtifactUpdateRequest,
    ConsolidateRequest,
    ExtractKnowledgeRequest,
    LearningSessionResponse,
    LearningStatsResponse,
    SearchLearningRequest,
)

router = APIRouter(prefix="/learning", tags=["Learning"])


@router.post("/extract", response_model=LearningSessionResponse)
async def extract_knowledge(
    body: ExtractKnowledgeRequest,
    request: Request,
) -> dict:
    """Extract knowledge from a completed execution."""
    learning_engine = request.app.state.learning_engine
    execution_data = {
        "id": body.execution_id,
        "user_id": body.user_id,
        "agent_id": body.agent_id,
        **body.execution_data,
    }
    task_data = body.task_data or {}
    if body.task_id:
        task_data["id"] = body.task_id
    if body.user_id:
        task_data["user_id"] = body.user_id

    session = await learning_engine.learn_from_execution(execution_data, task_data or None)
    return session.to_dict()


@router.post("/search", response_model=ArtifactListResponse)
async def search_knowledge(
    body: SearchLearningRequest,
    request: Request,
) -> dict:
    """Search for learned knowledge artifacts."""
    learning_engine = request.app.state.learning_engine
    result = await learning_engine.search(
        query=body.query,
        user_id=body.user_id,
        artifact_type=body.artifact_type,
        limit=body.limit,
    )
    return {
        "artifacts": [r.artifact.to_dict() for r in result.results],
        "total": result.total,
    }


@router.get("/artifacts")
async def list_artifacts(
    request: Request,
    user_id: str | None = Query(default=None),
    artifact_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """List learning artifacts with optional filters."""
    learning_engine = request.app.state.learning_engine
    artifacts = await learning_engine.list_artifacts(
        user_id=user_id,
        artifact_type=artifact_type,
        limit=limit,
    )
    return {
        "artifacts": [a.to_dict() for a in artifacts],
        "total": len(artifacts),
    }


@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    request: Request,
) -> dict:
    """Get a single learning artifact by ID."""
    learning_engine = request.app.state.learning_engine
    artifact = await learning_engine.get_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )
    return artifact.to_dict()


@router.delete("/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    artifact_id: str,
    request: Request,
) -> None:
    """Delete a learning artifact."""
    learning_engine = request.app.state.learning_engine
    deleted = await learning_engine.delete_artifact(artifact_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )


@router.post("/consolidate")
async def consolidate(
    body: ConsolidateRequest,
    request: Request,
) -> dict:
    """Consolidate duplicate knowledge artifacts."""
    learning_engine = request.app.state.learning_engine
    result = await learning_engine.run_consolidation(
        user_id=body.user_id,
        artifact_type=body.artifact_type,
    )
    return result.to_dict()


@router.get("/stats")
async def stats(
    request: Request,
) -> dict:
    """Return learning engine statistics."""
    learning_engine = request.app.state.learning_engine
    return await learning_engine.stats()
