"""Profile API endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.memory.profile import ProfileProvider

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/{user_id}")
async def get_profile(user_id: UUID, request: Request) -> dict:
    """Retrieve a user's identity profile."""
    profile_memory: ProfileProvider = request.app.state.profile_memory
    profile = await profile_memory.get_profile(user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    return profile
