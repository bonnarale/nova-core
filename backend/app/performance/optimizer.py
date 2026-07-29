"""Performance optimizer — top-level coordinator for all optimization subsystems."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.performance.benchmark import BenchmarkRunner
from app.performance.cache_optimizer import CacheOptimizer
from app.performance.diagnostics import DiagnosticsEngine, DiagnosticReport
from app.performance.enums import OptimizationArea, OptimizationSeverity
from app.performance.execution_optimizer import ExecutionOptimizer
from app.performance.metrics import PerformanceMetricsCollector, PerformanceMetrics
from app.performance.model_optimizer import ModelOptimizer
from app.performance.profiler import Profiler
from app.performance.query_optimizer import QueryOptimizer
from app.performance.rag_optimizer import RAGOptimizer
from app.performance.resource_optimizer import ResourceOptimizer
from app.performance.scheduler_optimizer import SchedulerOptimizer
from app.performance.tracing import PerformanceTracer
from app.performance.vector_optimizer import VectorOptimizer
from app.performance.workflow_optimizer import WorkflowOptimizer

logger = logging.getLogger(__name__)


class OptimizationResult:
    """Result of an optimization run."""

    __slots__ = ("area", "success", "recommendations", "metrics", "duration_ms")

    def __init__(
        self,
        area: str,
        success: bool,
        recommendations: list[dict[str, Any]] | None = None,
        metrics: dict[str, Any] | None = None,
        duration_ms: float = 0.0,
    ) -> None:
        self.area = area
        self.success = success
        self.recommendations = recommendations or []
        self.metrics = metrics or {}
        self.duration_ms = duration_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "area": self.area,
            "success": self.success,
            "recommendations": self.recommendations,
            "metrics": self.metrics,
            "duration_ms": self.duration_ms,
        }


class PerformanceOptimizer:
    """Top-level performance optimizer coordinating all optimization subsystems."""

    def __init__(self) -> None:
        self._profiler = Profiler()
        self._benchmark = BenchmarkRunner()
        self._cache = CacheOptimizer()
        self._query = QueryOptimizer()
        self._execution = ExecutionOptimizer()
        self._scheduler = SchedulerOptimizer()
        self._workflow = WorkflowOptimizer()
        self._vector = VectorOptimizer()
        self._rag = RAGOptimizer()
        self._model = ModelOptimizer()
        self._resource = ResourceOptimizer()
        self._diagnostics = DiagnosticsEngine()
        self._metrics = PerformanceMetricsCollector()
        self._tracer = PerformanceTracer()
        self._recommendations: list[dict[str, Any]] = []
        self._start_time: float = 0.0
        self._running = False

    @property
    def profiler(self) -> Profiler:
        return self._profiler

    @property
    def benchmark(self) -> BenchmarkRunner:
        return self._benchmark

    @property
    def cache_optimizer(self) -> CacheOptimizer:
        return self._cache

    @property
    def query_optimizer(self) -> QueryOptimizer:
        return self._query

    @property
    def execution_optimizer(self) -> ExecutionOptimizer:
        return self._execution

    @property
    def scheduler_optimizer(self) -> SchedulerOptimizer:
        return self._scheduler

    @property
    def workflow_optimizer(self) -> WorkflowOptimizer:
        return self._workflow

    @property
    def vector_optimizer(self) -> VectorOptimizer:
        return self._vector

    @property
    def rag_optimizer(self) -> RAGOptimizer:
        return self._rag

    @property
    def model_optimizer(self) -> ModelOptimizer:
        return self._model

    @property
    def resource_optimizer(self) -> ResourceOptimizer:
        return self._resource

    @property
    def diagnostics(self) -> DiagnosticsEngine:
        return self._diagnostics

    @property
    def metrics(self) -> PerformanceMetricsCollector:
        return self._metrics

    @property
    def tracer(self) -> PerformanceTracer:
        return self._tracer

    async def start(self) -> None:
        self._start_time = time.time()
        self._metrics.start()
        self._profiler.start()
        self._running = True
        logger.info("Performance optimizer started")

    async def shutdown(self) -> None:
        self._running = False
        self._profiler.shutdown()
        logger.info("Performance optimizer stopped")

    def is_running(self) -> bool:
        return self._running

    def get_recommendations(self) -> list[dict[str, Any]]:
        all_recs: list[dict[str, Any]] = []
        all_recs.extend(self._cache.get_recommendations())
        all_recs.extend(self._query.get_recommendations())
        all_recs.extend(self._execution.get_recommendations())
        all_recs.extend(self._scheduler.get_recommendations())
        all_recs.extend(self._workflow.get_recommendations())
        all_recs.extend(self._vector.get_recommendations())
        all_recs.extend(self._rag.get_recommendations())
        all_recs.extend(self._model.get_recommendations())
        all_recs.extend(self._resource.get_recommendations())
        self._recommendations = all_recs
        return all_recs

    def run_diagnostics(self) -> DiagnosticReport:
        trace_id = self._tracer.start_trace("diagnostics.run")
        report = self._diagnostics.analyze(
            latency_stats=self._metrics.get_latency_stats(),
            cache_stats=self._cache.get_stats(),
            query_stats=self._query.get_stats(),
            execution_stats=self._execution.get_stats(),
            resource_stats=self._resource.get_stats(),
        )
        self._tracer.finish_trace(trace_id)
        return report

    def get_health(self) -> dict[str, Any]:
        return {
            "status": "healthy" if self._running else "stopped",
            "profiler_active": self._profiler.is_running(),
            "active_sessions": len(self._profiler.get_active_sessions()),
            "total_benchmarks": self._benchmark.suite.count(),
        }

    def get_metrics(self) -> PerformanceMetrics:
        return self._metrics.snapshot()

    def get_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._tracer.get_traces(limit)

    def record_latency(self, operation: str, duration_ms: float) -> None:
        self._metrics.record_latency(operation, duration_ms)

    def record_cache_hit(self, cache_name: str) -> None:
        self._metrics.record_cache_hit()
        self._cache.record_hit(cache_name)

    def record_cache_miss(self, cache_name: str) -> None:
        self._metrics.record_cache_miss()
        self._cache.record_miss(cache_name)

    def record_query(self, query: str, duration_ms: float, rows: int = 0, table: str = "") -> None:
        self._metrics.record_query_time(duration_ms)
        self._query.record_query(query, duration_ms, rows, table)

    def record_execution(self, operation: str, duration_ms: float, parallel: bool = False, batched: bool = False) -> None:
        self._metrics.record_execution_time(duration_ms)
        self._execution.record_execution(operation, duration_ms, parallel, batched)

    def record_vector_search(self, query_size: int, result_count: int, duration_ms: float, indexed: bool = True) -> None:
        self._vector.record_search(query_size, result_count, duration_ms, indexed)

    def record_model_call(self, model: str, tokens: int, duration_ms: float, cached: bool = False) -> None:
        self._model.record_call(model, tokens, duration_ms, cached)

    def record_rag_retrieval(self, query_length: int, chunks: int, reranked: bool, duration_ms: float) -> None:
        self._rag.record_retrieval(query_length, chunks, reranked, duration_ms)
