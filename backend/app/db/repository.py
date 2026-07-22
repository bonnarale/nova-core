"""Data access repository for conversation persistence."""

import json
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import ConversationMessage, ConversationSession

logger = logging.getLogger(__name__)


class ConversationRepository:
    """Repository for conversation data access."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def ensure_session(
        self, session_id: UUID, agent_id: str
    ) -> ConversationSession:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ConversationSession).where(
                    ConversationSession.id == session_id
                )
            )
            conv_session = result.scalar_one_or_none()
            if conv_session is None:
                conv_session = ConversationSession(
                    id=session_id, agent_id=agent_id
                )
                session.add(conv_session)
                await session.commit()
            return conv_session

    async def add_message(
        self, session_id: UUID, role: str, content: str
    ) -> ConversationMessage:
        async with self._session_factory() as session:
            message = ConversationMessage(
                session_id=session_id,
                role=role,
                content=content,
            )
            session.add(message)
            await session.commit()
            return message

    async def get_history(
        self, session_id: UUID, limit: int = 20
    ) -> list[dict[str, str]]:
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
        )
        logger.info(
            "=== MEMORY_AUDIT [ConversationRepository] SQL query ==="
        )
        logger.info(
            "session_id=%s  limit=%d  compiled=%s",
            session_id, limit, stmt,
        )

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
            messages = [
                {"role": m.role, "content": m.content}
                for m in rows
            ]

        logger.info(
            "=== MEMORY_AUDIT [ConversationRepository] query result ==="
        )
        logger.info("rows_returned=%d", len(rows))
        logger.info("messages=%s", json.dumps(messages, indent=2, ensure_ascii=False))

        return messages
