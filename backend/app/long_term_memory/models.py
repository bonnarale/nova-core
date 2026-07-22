"""Data models and enums for Long-Term Memory."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MemoryType(str, Enum):
    USER = "user"
    PROJECT = "project"
    AGENT = "agent"
    KNOWLEDGE = "knowledge"
    SYSTEM = "system"
    PREFERENCE = "preference"
    ERROR_PATTERN = "error_pattern"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    CONSOLIDATED = "consolidated"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class LongTermMemory:
    id: str
    memory_type: str
    content: str
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    importance_score: float = 0.0
    status: str = MemoryStatus.ACTIVE.value
    linked_memory_ids: list[str] = field(default_factory=list)
    source: str = "system"
    source_id: str | None = None
    user_id: str | None = None
    project_id: str | None = None
    agent_id: str | None = None
    access_count: int = 0
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    accessed_at: str = ""
    updated_at: str = ""
    archived_at: str | None = None

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for f in self.__dataclass_fields__:
            val = getattr(self, f)
            if isinstance(val, Enum):
                d[f] = val.value
            else:
                d[f] = val
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LongTermMemory:
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in data.items() if k in valid}
        return cls(**kwargs)


@dataclass
class ConsolidationSource:
    conversations: list[dict[str, Any]] = field(default_factory=list)
    profile: dict[str, Any] | None = None
    goals: list[dict[str, Any]] = field(default_factory=list)
    completed_tasks: list[dict[str, Any]] = field(default_factory=list)
    semantic_memories: list[dict[str, Any]] = field(default_factory=list)
    user_id: str | None = None
    project_id: str | None = None


@dataclass
class ConsolidationResult:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    duplicates_skipped: int = 0
    links_created: int = 0


@dataclass
class LifecycleResult:
    aged: int = 0
    archived: int = 0
    purged: int = 0


@dataclass
class RetrievalResult:
    results: list[LongTermMemory] = field(default_factory=list)
    total: int = 0
    query: str = ""
