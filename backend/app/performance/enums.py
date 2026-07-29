"""Performance enums and state definitions."""

from __future__ import annotations

from enum import Enum


class OptimizationArea(str, Enum):
    """Areas of the platform that can be optimized."""

    COGNITIVE_ENGINE = "cognitive_engine"
    MEMORY_RETRIEVAL = "memory_retrieval"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    LEARNING_ENGINE = "learning_engine"
    REASONING_ENGINE = "reasoning_engine"
    GOAL_ENGINE = "goal_engine"
    TASK_ENGINE = "task_engine"
    PLANNING_ENGINE = "planning_engine"
    EXECUTION_ENGINE = "execution_engine"
    MULTI_AGENT = "multi_agent"
    TOOL_EXECUTION = "tool_execution"
    MODEL_GATEWAY = "model_gateway"
    RAG_RETRIEVAL = "rag_retrieval"
    VECTOR_SEARCH = "vector_search"
    SCHEDULER = "scheduler"
    WORKFLOW_EXECUTION = "workflow_execution"
    PLUGIN_LOADING = "plugin_loading"
    DATABASE_QUERIES = "database_queries"
    API_LATENCY = "api_latency"


class ProfileType(str, Enum):
    """Types of profiling."""

    CPU = "cpu"
    MEMORY = "memory"
    ASYNC = "async"
    LATENCY = "latency"
    ALLOCATIONS = "allocations"
    COMPREHENSIVE = "comprehensive"


class OptimizationSeverity(str, Enum):
    """Severity of optimization findings."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BenchmarkCategory(str, Enum):
    """Benchmark categories."""

    API = "api"
    WORKFLOWS = "workflows"
    SCHEDULER = "scheduler"
    VECTOR_SEARCH = "vector_search"
    RAG = "rag"
    EXECUTION = "execution"
    AGENTS = "agents"
    TOOLS = "tools"


class CacheStrategy(str, Enum):
    """Cache optimization strategies."""

    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    ADAPTIVE = "adaptive"


class ProfileState(str, Enum):
    """State of a profiling session."""

    IDLE = "idle"
    COLLECTING = "collecting"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    ERROR = "error"
