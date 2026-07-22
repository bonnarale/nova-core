"""Data models and enums for the Learning Engine."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ArtifactType(str, Enum):
    """Types of knowledge artifacts the learning engine can produce."""

    PROCEDURE = "procedure"
    PATTERN = "pattern"
    FACT = "fact"
    STRATEGY = "strategy"
    ERROR_HANDLING = "error_handling"
    OPTIMIZATION = "optimization"


class MemoryRankSource(str, Enum):
    """Sources used when ranking memories."""

    RECENCY = "recency"
    IMPORTANCE = "importance"
    RELEVANCE = "relevance"
    FREQUENCY = "frequency"


class LearningEventType(str, Enum):
    """Events emitted by the Learning Engine."""

    KNOWLEDGE_EXTRACTED = "learning.knowledge_extracted"
    ARTIFACT_STORED = "learning.artifact_stored"
    ARTIFACT_CONSOLIDATED = "learning.artifact_consolidated"
    MEMORY_RANKED = "learning.memory_ranked"
    RETRIEVAL_PERFORMED = "learning.retrieval_performed"
    EXECUTION_LEARNED = "learning.execution_learned"
    OUTCOME_RECORDED = "learning.outcome_recorded"


@dataclass
class LearningEvent:
    """An event emitted during the learning lifecycle."""

    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "payload": self.payload,
        }


@dataclass
class KnowledgeArtifact:
    """A single unit of extracted knowledge."""

    id: str
    artifact_type: str
    content: str
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    source_execution_id: str | None = None
    source_task_id: str | None = None
    user_id: str | None = None
    agent_id: str | None = None
    confidence: float = 0.0
    importance_score: float = 0.0
    access_count: int = 0
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "artifact_type": self.artifact_type,
            "content": self.content,
            "summary": self.summary,
            "tags": list(self.tags),
            "source_execution_id": self.source_execution_id,
            "source_task_id": self.source_task_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "confidence": self.confidence,
            "importance_score": self.importance_score,
            "access_count": self.access_count,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeArtifact:
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in data.items() if k in valid}
        return cls(**kwargs)


@dataclass
class ExtractedKnowledge:
    """Result of extracting knowledge from a completed execution."""

    artifacts: list[KnowledgeArtifact] = field(default_factory=list)
    execution_id: str = ""
    task_id: str = ""
    extraction_method: str = "default"
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifacts": [a.to_dict() for a in self.artifacts],
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
            "artifact_count": len(self.artifacts),
        }


@dataclass
class RankedMemory:
    """A memory artifact with a computed rank score."""

    artifact: KnowledgeArtifact
    score: float = 0.0
    rank_factors: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.artifact.to_dict(),
            "score": self.score,
            "rank_factors": dict(self.rank_factors),
        }


@dataclass
class ConsolidationResult:
    """Result of consolidating duplicate knowledge."""

    merged_count: int = 0
    duplicates_removed: int = 0
    artifacts_affected: list[str] = field(default_factory=list)
    consolidation_method: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "merged_count": self.merged_count,
            "duplicates_removed": self.duplicates_removed,
            "artifacts_affected": list(self.artifacts_affected),
            "consolidation_method": self.consolidation_method,
        }


@dataclass
class RetrievalResult:
    """Result of a semantic retrieval query."""

    results: list[RankedMemory] = field(default_factory=list)
    total: int = 0
    query: str = ""
    filters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "total": self.total,
            "query": self.query,
            "filters": dict(self.filters),
        }


@dataclass
class LearningSession:
    """Tracks a complete learning cycle from execution to storage."""

    session_id: str
    execution_id: str | None = None
    task_id: str | None = None
    user_id: str | None = None
    artifacts_extracted: int = 0
    artifacts_stored: int = 0
    consolidations_run: int = 0
    events: list[LearningEvent] = field(default_factory=list)
    status: str = "pending"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "artifacts_extracted": self.artifacts_extracted,
            "artifacts_stored": self.artifacts_stored,
            "consolidations_run": self.consolidations_run,
            "events": [e.to_dict() for e in self.events],
            "status": self.status,
            "error": self.error,
        }


@dataclass
class OutputQuality:
    """Quality metrics for an execution outcome."""

    score: int  # 0-100, None for partial/failure
    scoring_method: str = "manual"  # "manual" | "heuristic"

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValueError(f"Quality score must be between 0 and 100, got {self.score}")


@dataclass
class ResourceMetrics:
    """Resource utilization metrics for an execution outcome."""

    memory_used_mb: float | None = None
    cpu_time_ms: float | None = None
    tokens_used: int | None = None


@dataclass
class SystemImpact:
    """System impact metrics for an execution outcome."""

    latency_ms: float | None = None
    throughput_ops_per_sec: float | None = None


@dataclass
class ExecutionOutcome:
    """Records the outcome of a single task execution for success tracking."""

    id: str
    execution_id: str
    task_id: str | None = None
    strategy_used: str = "default"
    outcome: str = "success"  # "success" | "failure" | "partial"
    duration_ms: int = 0
    error_count: int = 0
    error_message: str | None = None
    user_satisfaction: float | None = None
    quality_score: int | None = None
    resource_metrics: ResourceMetrics | None = None
    system_impact: SystemImpact | None = None
    created_at: str = ""

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "strategy_used": self.strategy_used,
            "outcome": self.outcome,
            "duration_ms": self.duration_ms,
            "error_count": self.error_count,
            "error_message": self.error_message,
            "user_satisfaction": self.user_satisfaction,
            "quality_score": self.quality_score,
            "resource_metrics": {
                "memory_used_mb": self.resource_metrics.memory_used_mb,
                "cpu_time_ms": self.resource_metrics.cpu_time_ms,
                "tokens_used": self.resource_metrics.tokens_used,
            } if self.resource_metrics else None,
            "system_impact": {
                "latency_ms": self.system_impact.latency_ms,
                "throughput_ops_per_sec": self.system_impact.throughput_ops_per_sec,
            } if self.system_impact else None,
            "created_at": self.created_at,
        }
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionOutcome:
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in data.items() if k in valid}

        # Reconstruct nested dataclasses from dicts
        if isinstance(kwargs.get("resource_metrics"), dict):
            rm = kwargs["resource_metrics"]
            kwargs["resource_metrics"] = ResourceMetrics(
                memory_used_mb=rm.get("memory_used_mb"),
                cpu_time_ms=rm.get("cpu_time_ms"),
                tokens_used=rm.get("tokens_used"),
            )
        if isinstance(kwargs.get("system_impact"), dict):
            si = kwargs["system_impact"]
            kwargs["system_impact"] = SystemImpact(
                latency_ms=si.get("latency_ms"),
                throughput_ops_per_sec=si.get("throughput_ops_per_sec"),
            )

        return cls(**kwargs)


@dataclass
class ImprovementGoal:
    """A proposed improvement target identified by the self-improvement generator."""

    id: str
    target_strategy: str
    proposed_change: str
    confidence: float
    evidence: dict[str, Any] = field(default_factory=dict)
    status: str = "pending_approval"  # "pending_approval" | "approved" | "rejected" | "in_progress" | "completed" | "measured" | "evolving" | "measuring" | "validated" | "rolled_back"

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target_strategy": self.target_strategy,
            "proposed_change": self.proposed_change,
            "confidence": self.confidence,
            "evidence": dict(self.evidence),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImprovementGoal:
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in data.items() if k in valid}
        return cls(**kwargs)
