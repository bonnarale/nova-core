"""Autonomy enums and state definitions."""

from __future__ import annotations

from enum import Enum


class AutonomyLevel(str, Enum):
    """Levels of autonomous operation."""
    MANUAL = "manual"
    ASSISTED = "assisted"
    SUPERVISED = "supervised"
    AUTONOMOUS = "autonomous"
    FULL = "full"


class AutonomyState(str, Enum):
    """Lifecycle states for the autonomy layer."""
    REGISTERED = "registered"
    INITIALIZED = "initialized"
    READY = "ready"
    OBSERVING = "observing"
    ANALYZING = "analyzing"
    RECOMMENDING = "recommending"
    APPROVED = "approved"
    EXECUTING = "executing"
    LEARNING = "learning"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


class ObjectivePriority(str, Enum):
    """Objective priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


class ObjectiveStatus(str, Enum):
    """Objective lifecycle status."""
    PENDING = "pending"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class ReflectionType(str, Enum):
    """Types of reflection analysis."""
    EXECUTION_REVIEW = "execution_review"
    OUTCOME_EVALUATION = "outcome_evaluation"
    FAILURE_ANALYSIS = "failure_analysis"
    SUCCESS_ANALYSIS = "success_analysis"
    LESSON_EXTRACTION = "lesson_extraction"


class StrategyType(str, Enum):
    """Adaptive strategy types."""
    PLANNING = "planning"
    EXECUTION = "execution"
    RETRIEVAL = "retrieval"
    TOOL_SELECTION = "tool_selection"
    MODEL_SELECTION = "model_selection"
    WORKFLOW_OPTIMIZATION = "workflow_optimization"


class ApprovalType(str, Enum):
    """Types of approval mechanisms."""
    AUTOMATIC = "automatic"
    HUMAN = "human"
    POLICY = "policy"
    THRESHOLD = "threshold"


class SafetyLevel(str, Enum):
    """Safety constraint levels."""
    PERMISSIVE = "permissive"
    NORMAL = "normal"
    STRICT = "strict"
    MAXIMUM = "maximum"


class RecommendationStatus(str, Enum):
    """Status of recommendations."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"
