"""Abstract memory provider interface for NOVA CORE.

All memory implementations (ConversationMemory, SemanticMemory, KnowledgeMemory)
must implement this interface to remain swappable without refactoring consumers.
"""

from abc import ABC, abstractmethod
from uuid import UUID


class MemoryProvider(ABC):
    """Interface for memory backends."""

    @abstractmethod
    async def ensure_session(self, session_id: UUID, agent_id: str) -> None:
        """Ensure a conversation session exists in the backend."""
        ...

    @abstractmethod
    async def add_message(
        self, session_id: UUID, role: str, content: str
    ) -> None:
        """Persist a single message."""
        ...

    @abstractmethod
    async def get_history(
        self, session_id: UUID, limit: int = 20
    ) -> list[dict[str, str]]:
        """Retrieve recent message history for a session."""
        ...
