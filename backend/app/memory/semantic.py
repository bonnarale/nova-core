"""Semantic memory — minimal stub for CognitiveEngine imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SemanticMemoryConfig:
    """Configuration for semantic memory."""
    top_k: int = 3
    relevance_threshold: float = 0.5


class SemanticMemory:
    """Minimal SemanticMemory stub for CognitiveEngine."""

    def __init__(self, config: SemanticMemoryConfig | None = None) -> None:
        self.config = config or SemanticMemoryConfig()

    async def search(self, query: str, top_k: int = 3) -> list[Any]:
        return []

    async def auto_index(
        self,
        profile: dict[str, Any] | None = None,
        goals: list[dict[str, Any]] | None = None,
        tasks: list[dict[str, Any]] | None = None,
    ) -> None:
        pass
