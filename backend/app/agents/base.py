"""Base agent interface for NOVA CORE."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentDefinition:
    """Static definition / configuration of an agent.

    This is the persistable representation stored in the database.
    """

    agent_id: str
    name: str
    role: str
    description: str = ""
    system_prompt: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    memory_scope: str = "session"
    permissions: dict[str, Any] = field(default_factory=dict)
    supported_models: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "allowed_tools": list(self.allowed_tools),
            "memory_scope": self.memory_scope,
            "permissions": dict(self.permissions),
            "supported_models": list(self.supported_models),
        }


class BaseAgent(ABC):
    """Abstract base class for all NOVA CORE agents.

    Extends the original interface with optional lifecycle hooks,
    capability introspection, cost estimation, and cancellation.
    All new methods have backward-compatible defaults so existing
    agents (PlannerAgent, CoderAgent, etc.) work unchanged.
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

    @property
    @abstractmethod
    def definition(self) -> AgentDefinition:
        """Return the static definition for this agent."""
        ...

    @abstractmethod
    async def execute(
        self,
        task: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a task."""
        ...

    # ------------------------------------------------------------------
    # Lifecycle hooks (optional overrides)
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Called once after registration before first execute."""

    async def shutdown(self) -> None:
        """Called once before the runtime is torn down."""

    async def health(self) -> dict[str, Any]:
        """Return health status. Override to add checks."""
        return {"agent_id": self.agent_id, "status": "healthy"}

    # ------------------------------------------------------------------
    # Capability & estimation (optional overrides)
    # ------------------------------------------------------------------

    def estimate_cost(self, task: str, context: dict[str, Any] | None = None) -> float:
        """Estimate monetary cost of executing this task. Default: 0."""
        return 0.0

    def estimate_duration(self, task: str, context: dict[str, Any] | None = None) -> float:
        """Estimate duration in seconds. Default: 0."""
        return 0.0

    # ------------------------------------------------------------------
    # Cancellation (optional override)
    # ------------------------------------------------------------------

    async def cancel(self) -> dict[str, Any]:
        """Request graceful cancellation. Default: no-op."""
        return {"agent_id": self.agent_id, "cancelled": False, "message": "cancel not supported"}

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def metadata(self) -> dict[str, Any]:
        """Return agent metadata."""
        return {
            "id": self.agent_id,
            "type": self.__class__.__name__,
        }

    def can_handle(self, task_type: str) -> bool:
        """Check whether this agent can handle a given task type."""
        return (
            task_type in self.definition.role.lower()
            or task_type in self.definition.allowed_tools
        )
