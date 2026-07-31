from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class UserProfile:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    username: str = ""
    display_name: str = ""
    email: str = ""
    role: str = "user"
    preferences: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "role": self.role,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class UserPreference:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    key: str = ""
    value: Any = None
    category: str = "general"
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class Project:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    status: str = "active"
    priority: int = 3
    owner_id: str | None = None
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "owner_id": self.owner_id,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class Objective:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str | None = None
    title: str = ""
    description: str = ""
    status: str = "active"
    priority: int = 3
    progress: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class PriorityEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    level: int = 3
    description: str = ""
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "description": self.description,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class HistoryEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RoadmapPhase:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    status: str = "pending"
    objectives: list[str] = field(default_factory=list)
    duration_months: int | None = None
    order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "objectives": self.objectives,
            "duration_months": self.duration_months,
            "order": self.order,
        }


@dataclass
class Roadmap:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    phases: list[RoadmapPhase] = field(default_factory=list)
    status: str = "draft"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "phases": [p.to_dict() for p in self.phases],
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
