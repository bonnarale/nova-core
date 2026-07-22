"""Base agent interface for NOVA CORE."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentDefinition:
    """Metadata describing an agent's capabilities and configuration."""

    agent_id: str
    name: str
    role: str
    description: str
    system_prompt: str
    allowed_tools: list[str] = field(default_factory=list)
    memory_scope: str = "session"
    permissions: dict[str, Any] = field(default_factory=dict)
    supported_models: list[str] = field(default_factory=list)


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