"""Model Gateway context for tracking request metadata."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class RequestPriority(str, Enum):
    """Priority levels for model requests."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class RequestStatus(str, Enum):
    """Status of a model request."""

    PENDING = "pending"
    ROUTING = "routing"
    EXECUTING = "executing"
    CACHING = "caching"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CIRCUIT_BROKEN = "circuit_broken"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


@dataclass
class ModelContext:
    """Context for a model request, tracking metadata through the pipeline."""

    request_id: UUID = field(default_factory=uuid4)
    agent_id: Optional[str] = None
    session_id: Optional[UUID] = None
    user_id: Optional[str] = None

    provider: Optional[str] = None
    model: Optional[str] = None
    priority: RequestPriority = RequestPriority.NORMAL
    status: RequestStatus = RequestStatus.PENDING

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    messages: list[dict[str, str]] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    attempt: int = 0
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0

    cache_key: Optional[str] = None
    cache_hit: bool = False

    error: Optional[str] = None
    error_type: Optional[str] = None

    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0

    def mark_started(self) -> None:
        """Mark request as started."""
        self.started_at = datetime.now(timezone.utc)
        self.status = RequestStatus.EXECUTING

    def mark_completed(self) -> None:
        """Mark request as completed."""
        self.completed_at = datetime.now(timezone.utc)
        self.status = RequestStatus.COMPLETED
        if self.started_at:
            self.latency_ms = (self.completed_at - self.started_at).total_seconds() * 1000

    def mark_failed(self, error: str, error_type: str = "unknown") -> None:
        """Mark request as failed."""
        self.completed_at = datetime.now(timezone.utc)
        self.status = RequestStatus.FAILED
        self.error = error
        self.error_type = error_type
        if self.started_at:
            self.latency_ms = (self.completed_at - self.started_at).total_seconds() * 1000

    def mark_retrying(self) -> None:
        """Mark request as retrying."""
        self.status = RequestStatus.RETRYING
        self.attempt += 1

    def mark_circuit_broken(self) -> None:
        """Mark request as circuit broken."""
        self.status = RequestStatus.CIRCUIT_BROKEN
        self.completed_at = datetime.now(timezone.utc)

    def mark_timed_out(self) -> None:
        """Mark request as timed out."""
        self.status = RequestStatus.TIMED_OUT
        self.completed_at = datetime.now(timezone.utc)
        self.error = "Request timed out"
        self.error_type = "timeout"

    def mark_cancelled(self) -> None:
        """Mark request as cancelled."""
        self.status = RequestStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)

    def can_retry(self) -> bool:
        """Check if request can be retried."""
        return self.attempt < self.max_retries and self.status in (
            RequestStatus.FAILED,
            RequestStatus.TIMED_OUT,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "request_id": str(self.request_id),
            "agent_id": self.agent_id,
            "session_id": str(self.session_id) if self.session_id else None,
            "user_id": self.user_id,
            "provider": self.provider,
            "model": self.model,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "attempt": self.attempt,
            "max_retries": self.max_retries,
            "cache_hit": self.cache_hit,
            "error": self.error,
            "error_type": self.error_type,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "latency_ms": self.latency_ms,
        }
