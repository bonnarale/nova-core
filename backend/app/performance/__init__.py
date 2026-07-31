"""Performance Optimization — profiling, benchmarking, and optimization for the NOVA CORE platform."""

from __future__ import annotations

from app.performance.benchmark import BenchmarkResult, BenchmarkRunner, BenchmarkSuite
from app.performance.cache_optimizer import CacheOptimizer, CacheStats
from app.performance.diagnostics import DiagnosticReport, DiagnosticsEngine, Hotspot
from app.performance.execution_optimizer import ExecutionOptimizer
from app.performance.factory import PerformanceFactory
from app.performance.metrics import PerformanceMetrics, PerformanceMetricsCollector
from app.performance.model_optimizer import ModelOptimizer
from app.performance.optimizer import OptimizationArea, OptimizationResult, PerformanceOptimizer
from app.performance.profiler import CpuProfile, MemoryProfile, ProfileSession, Profiler
from app.performance.query_optimizer import QueryOptimizer
from app.performance.rag_optimizer import RAGOptimizer
from app.performance.resource_optimizer import ResourceOptimizer
from app.performance.schemas import (
    BenchmarkRunRequest,
    BenchmarkResponse,
    DiagnosticsResponse,
    HealthResponse,
    MetricsResponse,
    OptimizationRecommendation,
    ProfileRequest,
    ProfileResponse,
    RecommendationsResponse,
    TracesResponse,
)
from app.performance.scheduler_optimizer import SchedulerOptimizer
from app.performance.tracing import PerformanceTracer
from app.performance.vector_optimizer import VectorOptimizer
from app.performance.workflow_optimizer import WorkflowOptimizer

__all__ = [
    "BenchmarkResult",
    "BenchmarkResponse",
    "BenchmarkRunner",
    "BenchmarkRunRequest",
    "BenchmarkSuite",
    "CacheOptimizer",
    "CacheStats",
    "CpuProfile",
    "DiagnosticReport",
    "DiagnosticsEngine",
    "DiagnosticsResponse",
    "ExecutionOptimizer",
    "HealthResponse",
    "Hotspot",
    "MemoryProfile",
    "MetricsResponse",
    "ModelOptimizer",
    "OptimizationArea",
    "OptimizationRecommendation",
    "OptimizationResult",
    "PerformanceFactory",
    "PerformanceMetrics",
    "PerformanceMetricsCollector",
    "PerformanceOptimizer",
    "PerformanceTracer",
    "Profiler",
    "ProfileRequest",
    "ProfileResponse",
    "ProfileSession",
    "QueryOptimizer",
    "RAGOptimizer",
    "RecommendationsResponse",
    "ResourceOptimizer",
    "SchedulerOptimizer",
    "TracesResponse",
    "VectorOptimizer",
    "WorkflowOptimizer",
]
