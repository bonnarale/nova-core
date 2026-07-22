"""Data access repository for agent definitions."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import Agent

logger = logging.getLogger(__name__)


class AgentRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        agent_id: str,
        name: str,
        role: str,
        description: str = "",
        system_prompt: str = "",
        allowed_tools: list[str] | None = None,
        memory_scope: str = "session",
        permissions: dict[str, Any] | None = None,
        supported_models: list[str] | None = None,
    ) -> Agent:
        async with self._session_factory() as session:
            agent = Agent(
                id=agent_id,
                name=name,
                role=role,
                description=description,
                system_prompt=system_prompt,
                allowed_tools=allowed_tools or [],
                memory_scope=memory_scope,
                permissions=permissions or {},
                supported_models=supported_models or [],
            )
            session.add(agent)
            await session.commit()
            logger.debug("Agent created: %s", agent_id)
            return agent

    async def get(self, agent_id: str) -> Agent | None:
        async with self._session_factory() as session:
            return await session.get(Agent, agent_id)

    async def list(self) -> list[Agent]:
        async with self._session_factory() as session:
            stmt = select(Agent).order_by(Agent.created_at.asc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update(self, agent_id: str, **kwargs: Any) -> Agent | None:
        async with self._session_factory() as session:
            agent = await session.get(Agent, agent_id)
            if agent is None:
                return None
            for key, value in kwargs.items():
                if value is not None and hasattr(agent, key):
                    setattr(agent, key, value)
            await session.commit()
            logger.debug("Agent updated: %s", agent_id)
            return agent

    async def delete(self, agent_id: str) -> bool:
        async with self._session_factory() as session:
            agent = await session.get(Agent, agent_id)
            if agent is None:
                return False
            await session.delete(agent)
            await session.commit()
            logger.debug("Agent deleted: %s", agent_id)
            return True
