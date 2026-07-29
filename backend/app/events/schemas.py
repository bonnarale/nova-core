"""Event system schemas — Pydantic models for events, requests, and responses."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    CONVERSATION_CREATED = "conversation.created"
    MESSAGE_STORED = "message.stored"
    MEMORY_UPDATED = "memory.updated"
    PROFILE_UPDATED = "profile.updated"
    KNOWLEDGE_LEARNED = "knowledge.learned"
    GOAL_CREATED = "goal.created"
    GOAL_COMPLETED = "goal.completed"
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    PLAN_CREATED = "plan.created"
    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    TOOL_EXECUTED = "tool.executed"
    AGENT_REGISTERED = "agent.registered"
    AGENT_STARTED = "agent.started"
    AGENT_FINISHED = "agent.finished"
    MODEL_INVOKED = "model.invoked"
    RETRIEVAL_COMPLETED = "retrieval.completed"
    VECTOR_STORED = "vector.stored"
    SYSTEM_EVENT = "system.event"
    CUSTOM = "custom"


class EventPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class DispatchType(str, Enum):
    SYNC = "sync"
    ASYNC = "async"
    PARALLEL = "parallel"
    ORDERED = "ordered"
    PRIORITY = "priority"


class EventStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    aggregate_id: str = ""
    aggregate_type: str = ""
    source: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str = ""
    causation_id: str = ""
    session_id: str = ""
    user_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    priority: EventPriority = EventPriority.NORMAL
    status: EventStatus = EventStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3


class Subscription(BaseModel):
    subscription_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    handler_name: str = ""
    filter_pattern: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScheduledEvent(BaseModel):
    schedule_id: str = Field(default_factory=lambda: str(uuid4()))
    event: Event = Field(default_factory=Event)
    run_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    interval_seconds: Optional[int] = None
    max_runs: Optional[int] = None
    run_count: int = 0
    active: bool = True


class DelayedEvent(BaseModel):
    delay_id: str = Field(default_factory=lambda: str(uuid4()))
    event: Event = Field(default_factory=Event)
    publish_at: datetime
    active: bool = True


class DeadLetterEvent(BaseModel):
    original_event: Event
    failed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str = ""
    retry_count: int = 0


class EventFilter(BaseModel):
    event_types: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    user_ids: list[str] = Field(default_factory=list)
    session_ids: list[str] = Field(default_factory=list)
    correlation_ids: list[str] = Field(default_factory=list)
    aggregate_ids: list[str] = Field(default_factory=list)
    time_from: Optional[datetime] = None
    time_to: Optional[datetime] = None
    priority_min: Optional[EventPriority] = None


class ReplayRequest(BaseModel):
    event_ids: list[str] = Field(default_factory=list)
    aggregate_ids: list[str] = Field(default_factory=list)
    session_ids: list[str] = Field(default_factory=list)
    user_ids: list[str] = Field(default_factory=list)
    event_types: list[str] = Field(default_factory=list)
    time_from: Optional[datetime] = None
    time_to: Optional[datetime] = None


class ReplayResult(BaseModel):
    total_events: int = 0
    replayed: int = 0
    failed: int = 0
    errors: list[str] = Field(default_factory=list)


class PublishRequest(BaseModel):
    event_type: str = Field(..., min_length=1)
    aggregate_id: str = ""
    aggregate_type: str = ""
    source: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    session_id: str = ""
    user_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    delay_seconds: Optional[int] = None


class EventResponse(BaseModel):
    success: bool = True
    event_id: str = ""
    message: str = ""


class EventsListResponse(BaseModel):
    events: list[Event] = Field(default_factory=list)
    total: int = 0


class EventStatistics(BaseModel):
    total_events: int = 0
    events_by_type: dict[str, int] = Field(default_factory=dict)
    events_by_status: dict[str, int] = Field(default_factory=dict)
    active_subscriptions: int = 0
    dead_letter_count: int = 0
    replay_count: int = 0


class EventHealthResponse(BaseModel):
    status: str = "ok"
    lifecycle_state: str = ""
    total_events: int = 0
    active_subscriptions: int = 0
    dead_letter_count: int = 0
    uptime_seconds: float = 0.0


class EventMetricsResponse(BaseModel):
    total_published: int = 0
    total_processed: int = 0
    total_failed: int = 0
    total_retries: int = 0
    average_latency_ms: float = 0.0
    subscriber_count: int = 0
    queue_size: int = 0
    replay_count: int = 0


class EventTracesResponse(BaseModel):
    traces: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
