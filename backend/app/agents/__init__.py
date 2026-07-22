"""Agent system for NOVA CORE — Multi-Agent Runtime (Chapter 14)."""

from app.agents.agent_manager import AgentManager
from app.agents.base import AgentDefinition, BaseAgent
from app.agents.builtins import (
    CoderAgent,
    CoordinatorAgent,
    ExecutorAgent,
    MemoryAgent,
    PlannerAgent,
    ResearchAgent,
    ReviewerAgent,
)
from app.agents.capabilities import AgentCapability, CapabilityRegistry
from app.agents.context import AgentExecutionContext
from app.agents.coordinator import AgentCoordinator, CoordinationPattern, CoordinationStep, CoordinatorResult
from app.agents.dispatcher import AgentDispatcher, DispatchResult
from app.agents.executor import AgentExecutor, ExecutionResult
from app.agents.factory import AgentFactory
from app.agents.lifecycle import AgentLifecycle, AgentState
from app.agents.metrics import MetricsCollector
from app.agents.policies import (
    ExecutionPolicy,
    ExclusivePolicy,
    IdempotentPolicy,
    ImmediatePolicy,
    ParallelPolicy,
    PolicyType,
    RetryablePolicy,
    SequentialPolicy,
    BackgroundPolicy,
    get_policy,
    list_policies,
)
from app.agents.registry import AgentRegistry
from app.agents.runtime import AgentRuntime
from app.agents.scheduler import AgentScheduler, ScheduledTask
from app.agents.tracing import TraceSpan, Tracer

__all__ = [
    # Core
    "AgentDefinition",
    "AgentManager",
    "BaseAgent",
    # Runtime
    "AgentRuntime",
    "AgentRegistry",
    "AgentFactory",
    # Dispatch & Scheduling
    "AgentDispatcher",
    "AgentScheduler",
    "AgentExecutor",
    "AgentCoordinator",
    # Models
    "AgentCapability",
    "AgentExecutionContext",
    "AgentLifecycle",
    "AgentState",
    "CapabilityRegistry",
    "DispatchResult",
    "ExecutionResult",
    "ScheduledTask",
    "CoordinationStep",
    "CoordinationPattern",
    "CoordinatorResult",
    # Policies
    "ExecutionPolicy",
    "PolicyType",
    "ImmediatePolicy",
    "BackgroundPolicy",
    "ExclusivePolicy",
    "ParallelPolicy",
    "SequentialPolicy",
    "RetryablePolicy",
    "IdempotentPolicy",
    "get_policy",
    "list_policies",
    # Built-ins
    "CoordinatorAgent",
    "PlannerAgent",
    "ResearchAgent",
    "CoderAgent",
    "ReviewerAgent",
    "MemoryAgent",
    "ExecutorAgent",
    # Observability
    "MetricsCollector",
    "TraceSpan",
    "Tracer",
]
