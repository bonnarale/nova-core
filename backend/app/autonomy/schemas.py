from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ObjectivePlan:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    analysis: dict = field(default_factory=dict)
    milestones: list[dict] = field(default_factory=list)
    goals: list[dict] = field(default_factory=list)
    tasks: list[dict] = field(default_factory=list)
    workflows: list[dict] = field(default_factory=list)
    tools_needed: list[str] = field(default_factory=list)
    agents_needed: list[str] = field(default_factory=list)
    risk_assessment: dict = field(default_factory=dict)
    estimated_duration: str = ""
    requires_human_approval: bool = True
    requires_open_code: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ProjectOrchestration:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    objective: str = ""
    plan: ObjectivePlan | None = None
    status: str = "analyzing"
    progress: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Recommendation:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ""
    title: str = ""
    description: str = ""
    priority: str = "medium"
    status: str = "pending"
    impact: str = ""
    effort: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class OptimizationResult:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ""
    current_state: str = ""
    proposed_state: str = ""
    improvement: str = ""
    priority: int = 3
    estimated_impact: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SelfImprovementItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ""
    title: str = ""
    description: str = ""
    status: str = "identified"
    priority: int = 3
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DelegationTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str = ""
    assigned_to: str = ""
    delegation_type: str = "agent"
    status: str = "pending"
    context: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ResearchQuery:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    depth: str = "standard"
    findings: list[dict] = field(default_factory=list)
    summary: str = ""
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
