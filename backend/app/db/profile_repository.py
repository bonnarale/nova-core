"""Data access repository for user profiles."""

import logging
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import UserProfile

logger = logging.getLogger(__name__)


class UserProfileRepository:
    """Repository for user profile data access."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def create_profile(
        self,
        profile_id: UUID,
        name: str | None = None,
        bio: str | None = None,
        preferences: dict | None = None,
        goals: list | None = None,
        facts: list | None = None,
    ) -> UserProfile:
        async with self._session_factory() as session:
            profile = UserProfile(
                id=profile_id,
                name=name,
                bio=bio,
                preferences=preferences or {},
                goals=goals or [],
                facts=facts or [],
            )
            session.add(profile)
            await session.commit()
            logger.debug("Profile created: %s", profile_id)
            return profile

    async def get_profile(self, profile_id: UUID) -> UserProfile | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserProfile).where(UserProfile.id == profile_id)
            )
            return result.scalar_one_or_none()

    async def update_profile(
        self,
        profile_id: UUID,
        name: str | None = None,
        bio: str | None = None,
        preferences: dict | None = None,
        goals: list | None = None,
        facts: list | None = None,
    ) -> UserProfile | None:
        async with self._session_factory() as session:
            profile = await session.get(UserProfile, profile_id)
            if profile is None:
                return None
            if name is not None:
                profile.name = name
            if bio is not None:
                profile.bio = bio
            if preferences is not None:
                profile.preferences = preferences
            if goals is not None:
                profile.goals = goals
            if facts is not None:
                profile.facts = facts
            await session.commit()
            logger.debug("Profile updated: %s", profile_id)
            return profile

    async def add_facts(
        self, profile_id: UUID, new_facts: list[str]
    ) -> UserProfile | None:
        async with self._session_factory() as session:
            profile = await session.get(UserProfile, profile_id)
            if profile is None:
                return None
            existing = set(profile.facts or [])
            for f in new_facts:
                if f not in existing:
                    profile.facts.append(f)
                    existing.add(f)
            await session.commit()
            logger.debug("Facts added to profile %s: %s", profile_id, new_facts)
            return profile
