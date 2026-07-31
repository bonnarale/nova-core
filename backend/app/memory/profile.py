"""Profile memory — minimal stub for CognitiveEngine imports."""

from __future__ import annotations

from typing import Any
from uuid import UUID


class UserProfileMemory:
    """Minimal UserProfileMemory stub for CognitiveEngine."""

    def __init__(self, database: Any = None) -> None:
        self._database = database

    async def get_profile(self, profile_id: UUID) -> dict[str, Any] | None:
        return None

    async def update_profile(self, profile_id: UUID) -> dict[str, Any]:
        return {"id": str(profile_id)}
