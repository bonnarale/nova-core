"""Conversation memory service for NOVA CORE.

Stores and retrieves conversation history through PostgreSQL.
Implements MemoryProvider for future interchangeability with
SemanticMemory (ChromaDB) and KnowledgeMemory backends.
"""

import logging
from uuid import UUID

from app.db.postgres import Database
from app.db.repository import ConversationRepository
from app.memory.base import MemoryProvider

logger = logging.getLogger(__name__)


class ConversationMemory(MemoryProvider):
    """PostgreSQL-backed conversational memory."""

    def __init__(self, database: Database) -> None:
        self._repo = ConversationRepository(database.session_factory)

    async def ensure_session(self, session_id: UUID, agent_id: str) -> None:
        await self._repo.ensure_session(session_id, agent_id)
        logger.debug("Session ensured in DB: %s (agent=%s)", session_id, agent_id)

    async def add_message(
        self, session_id: UUID, role: str, content: str
    ) -> None:
        await self._repo.add_message(session_id, role, content)
        logger.debug("Message saved: session=%s role=%s", session_id, role)

    async def get_history(
        self, session_id: UUID, limit: int = 20
    ) -> list[dict[str, str]]:
        return await self._repo.get_history(session_id, limit=limit)
