"""Base agent interface for NOVA CORE."""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Abstract base class for all NOVA CORE agents."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

    @abstractmethod
    async def execute(
        self,
        task: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a task."""
        ...

    @property
    def metadata(self) -> dict[str, Any]:
        """Return agent metadata."""
        return {
            "id": self.agent_id,
            "type": self.__class__.__name__,
        }