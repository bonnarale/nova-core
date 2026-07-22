"""Base abstractions for the learning subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.learning.models import ExecutionOutcome


class OutcomeStore(ABC):
    """Abstract store for execution outcomes."""

    @abstractmethod
    async def create(self, outcome: ExecutionOutcome) -> ExecutionOutcome:
        """Persist an outcome record."""
        ...

    @abstractmethod
    async def get_by_execution(self, execution_id: str) -> Optional[ExecutionOutcome]:
        """Retrieve an outcome by execution ID."""
        ...

    @abstractmethod
    async def list_by_strategy(self, strategy: str) -> list[ExecutionOutcome]:
        """List all outcomes for a given strategy."""
        ...

    @abstractmethod
    async def list_by_agent(self, agent_id: str) -> list[ExecutionOutcome]:
        """List all outcomes where task_id matches agent_id."""
        ...

    @abstractmethod
    async def list_all(self, limit: int = 1000) -> list[ExecutionOutcome]:
        """List all outcomes with optional limit."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Return total number of outcomes."""
        ...
