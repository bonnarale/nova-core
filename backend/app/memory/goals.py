"""Goal manager interface — minimal stub for CognitiveEngine imports."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class GoalManager:
    """Minimal GoalManager stub for CognitiveEngine."""

    def __init__(self, database: Any = None) -> None:
        self._database = database

    async def create_goal(
        self,
        user_id: UUID,
        title: str,
        description: str | None = None,
        priority: int = 3,
    ) -> dict[str, Any]:
        return {"id": str(UUID(int=0)), "title": title, "status": "active"}

    async def list_goals(self, user_id: UUID, status: str | None = None) -> list[dict[str, Any]]:
        return []
