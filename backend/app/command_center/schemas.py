from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CommandRequest:
    id: str = field(default_factory=_uuid)
    command: str = ""
    parameters: dict = field(default_factory=dict)
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class CommandResponse:
    id: str = field(default_factory=_uuid)
    command: str = ""
    status: str = "pending"
    result: object = None
    error: str | None = None
    suggestions: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=_utcnow)


@dataclass
class Objective:
    id: str = field(default_factory=_uuid)
    title: str = ""
    description: str = ""
    category: str = "general"
    status: str = "active"
    priority: int = 3
    analysis: dict = field(default_factory=dict)
    plan: dict | None = None
    milestones: list[dict] = field(default_factory=list)
    goals: list[dict] = field(default_factory=list)
    tasks: list[dict] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    progress: float = 0.0
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)


@dataclass
class Project:
    id: str = field(default_factory=_uuid)
    name: str = ""
    description: str = ""
    objective_id: str | None = None
    status: str = "planning"
    progress: float = 0.0
    phases: list[dict] = field(default_factory=list)
    milestones: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)


@dataclass
class Roadmap:
    id: str = field(default_factory=_uuid)
    name: str = ""
    description: str = ""
    start_year: int = 0
    end_year: int = 0
    duration_years: int = 1
    phases: list[dict] = field(default_factory=list)
    status: str = "draft"
    created_at: str = field(default_factory=_utcnow)
    updated_at: str = field(default_factory=_utcnow)


@dataclass
class RoadmapPhase:
    id: str = field(default_factory=_uuid)
    title: str = ""
    description: str = ""
    order: int = 0
    duration_months: int = 1
    status: str = "pending"
    objectives: list[str] = field(default_factory=list)
    milestones: list[str] = field(default_factory=list)


@dataclass
class Milestone:
    id: str = field(default_factory=_uuid)
    title: str = ""
    description: str = ""
    objective_id: str | None = None
    project_id: str | None = None
    status: str = "pending"
    due_date: str | None = None
    tasks: list[str] = field(default_factory=list)


@dataclass
class BacklogItem:
    id: str = field(default_factory=_uuid)
    title: str = ""
    description: str = ""
    category: str = "general"
    priority: int = 3
    status: str = "pending"
    source: str = "user"
    created_at: str = field(default_factory=_utcnow)


@dataclass
class GovernorDecision:
    id: str = field(default_factory=_uuid)
    decision_type: str = ""
    description: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    action_taken: str = ""
    requires_approval: bool = False
    approved: bool | None = None
    created_at: str = field(default_factory=_utcnow)


@dataclass
class ApprovalRequest:
    id: str = field(default_factory=_uuid)
    action_type: str = ""
    description: str = ""
    risk_level: str = "low"
    requester: str = "user"
    status: str = "pending"
    reviewer: str | None = None
    reason: str | None = None
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=_utcnow)


@dataclass
class Recommendation:
    id: str = field(default_factory=_uuid)
    category: str = ""
    title: str = ""
    description: str = ""
    priority: str = "medium"
    impact: str = ""
    effort: str = ""
    status: str = "pending"
    created_at: str = field(default_factory=_utcnow)


@dataclass
class Optimization:
    id: str = field(default_factory=_uuid)
    category: str = ""
    current_state: str = ""
    proposed_state: str = ""
    improvement: str = ""
    priority: int = 3
    estimated_impact: str = ""
    status: str = "identified"
    created_at: str = field(default_factory=_utcnow)


@dataclass
class LifecycleState:
    id: str = field(default_factory=_uuid)
    phase: str = "initializing"
    started_at: str | None = None
    stopped_at: str | None = None
    uptime_seconds: float = 0.0
    events: list[dict] = field(default_factory=list)


@dataclass
class CommandMetrics:
    total_commands: int = 0
    successful: int = 0
    failed: int = 0
    pending_approval: int = 0
    avg_processing_time_ms: float = 0.0
    active_objectives: int = 0
    active_projects: int = 0
    total_backlog: int = 0
