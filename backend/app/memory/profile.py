"""Profile provider interface and UserProfileMemory service."""

import logging
from abc import ABC, abstractmethod
from uuid import UUID

from app.db.postgres import Database
from app.db.profile_repository import UserProfileRepository

logger = logging.getLogger(__name__)


class ProfileProvider(ABC):
    """Interface for profile backends."""

    @abstractmethod
    async def create_profile(
        self,
        profile_id: UUID,
        name: str | None = None,
        bio: str | None = None,
        preferences: dict | None = None,
        goals: list | None = None,
        facts: list | None = None,
    ) -> dict:
        ...

    @abstractmethod
    async def get_profile(self, profile_id: UUID) -> dict | None:
        ...

    @abstractmethod
    async def update_profile(
        self,
        profile_id: UUID,
        name: str | None = None,
        bio: str | None = None,
        preferences: dict | None = None,
        goals: list | None = None,
        facts: list | None = None,
    ) -> dict | None:
        ...

    @abstractmethod
    async def add_facts(
        self, profile_id: UUID, new_facts: list[str]
    ) -> dict | None:
        ...


class UserProfileMemory(ProfileProvider):
    """PostgreSQL-backed user profile memory."""

    def __init__(self, database: Database) -> None:
        self._repo = UserProfileRepository(database.session_factory)

    def _to_dict(self, profile) -> dict | None:
        if profile is None:
            return None
        return {
            "id": str(profile.id),
            "name": profile.name,
            "bio": profile.bio,
            "preferences": profile.preferences or {},
            "goals": profile.goals or [],
            "facts": profile.facts or [],
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }

    async def create_profile(
        self,
        profile_id: UUID,
        name: str | None = None,
        bio: str | None = None,
        preferences: dict | None = None,
        goals: list | None = None,
        facts: list | None = None,
    ) -> dict:
        profile = await self._repo.create_profile(
            profile_id, name, bio, preferences, goals, facts
        )
        logger.debug("UserProfileMemory: profile created %s", profile_id)
        return self._to_dict(profile)

    async def get_profile(self, profile_id: UUID) -> dict | None:
        profile = await self._repo.get_profile(profile_id)
        return self._to_dict(profile)

    async def update_profile(
        self,
        profile_id: UUID,
        name: str | None = None,
        bio: str | None = None,
        preferences: dict | None = None,
        goals: list | None = None,
        facts: list | None = None,
    ) -> dict | None:
        profile = await self._repo.update_profile(
            profile_id, name, bio, preferences, goals, facts
        )
        return self._to_dict(profile)

    async def add_facts(
        self, profile_id: UUID, new_facts: list[str]
    ) -> dict | None:
        profile = await self._repo.add_facts(profile_id, new_facts)
        return self._to_dict(profile)
