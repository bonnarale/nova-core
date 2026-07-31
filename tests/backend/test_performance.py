"""Tests for Chapter 33 — Performance Optimization."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.v1.router import router as api_router
from app.performance.base import BenchmarkProvider, OptimizerProvider, PerformanceProvider, ProfilerProvider
from app.performance.benchmark import BenchmarkResult, BenchmarkRunner, BenchmarkSuite
from app.performance.cache_optimizer import CacheOptimizer, CacheStats
from app.performance.diagnostics import DiagnosticReport, DiagnosticsEngine, Hotspot
from app.performance.enums import (
    BenchmarkCategory,
    CacheStrategy,
    OptimizationArea,
    OptimizationSeverity,
    ProfileState,
    ProfileType,
)
from app.performance.execution_optimizer import ExecutionOptimizer
from app.performance.factory import PerformanceFactory
from app.performance.metrics import PerformanceMetrics, PerformanceMetricsCollector
from app.performance.model_optimizer import ModelOptimizer
from app.performance.optimizer import OptimizationResult, PerformanceOptimizer
from app.performance.profiler import CpuProfile, MemoryProfile, ProfileSession, Profiler
from app.performance.query_optimizer import QueryOptimizer
from app.performance.rag_optimizer import RAGOptimizer
from app.performance.resource_optimizer import ResourceOptimizer
from app.performance.schemas import (
    BenchmarkResponse,
    BenchmarkRunRequest,
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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_optimization_area_values(self) -> None:
        assert OptimizationArea.COGNITIVE_ENGINE.value == "cognitive_engine"
        assert OptimizationArea.VECTOR_SEARCH.value == "vector_search"

    def test_profile_type_values(self) -> None:
        assert ProfileType.CPU.value == "cpu"
        assert ProfileType.MEMORY.value == "memory"
        assert ProfileType.COMPREHENSIVE.value == "comprehensive"

    def test_benchmark_category_values(self) -> None:
        assert BenchmarkCategory.API.value == "api"
        assert BenchmarkCategory.RAG.value == "rag"

    def test_cache_strategy_values(self) -> None:
        assert CacheStrategy.LRU.value == "lru"
        assert CacheStrategy.ADAPTIVE.value == "adaptive"

    def test_profile_state_values(self) -> None:
        assert ProfileState.IDLE.value == "idle"
        assert ProfileState.COLLECTING.value == "collecting"


# ---------------------------------------------------------------------------
# Profiler
# ---------------------------------------------------------------------------


class TestProfiler:
    def test_start_and_shutdown(self) -> None:
        p = Profiler()
        p.start()
        assert p.is_running()
        p.shutdown()
        assert not p.is_running()

    def test_session_lifecycle(self) -> None:
        p = Profiler()
        p.start()
        sid = p.start_session("comprehensive")
        assert sid
        active = p.get_active_sessions()
        assert len(active) == 1
        session = p.stop_session(sid)
        assert session is not None
        assert session.state == ProfileState.COMPLETE
        assert "memory" in session.results
        assert "cpu" in session.results

    def test_session_not_found(self) -> None:
        p = Profiler()
        assert p.stop_session("nonexistent") is None

    def test_completed_sessions(self) -> None:
        p = Profiler()
        p.start()
        sid = p.start_session("cpu")
        p.stop_session(sid)
        completed = p.get_completed_sessions()
        assert len(completed) == 1

    def test_memory_profile(self) -> None:
        p = Profiler()
        p.start()
        sid = p.start_session("memory")
        session = p.stop_session(sid)
        assert session is not None
        mem = session.results.get("memory", {})
        assert "current_bytes" in mem
        assert "peak_bytes" in mem

    def test_get_session(self) -> None:
        p = Profiler()
        p.start()
        sid = p.start_session("cpu")
        session = p.get_session(sid)
        assert session is not None
        assert session.session_id == sid

    def test_cpu_profile(self) -> None:
        cpu = CpuProfile()
        d = cpu.to_dict()
        assert "function_calls" in d
        assert "total_time_ms" in d

    def test_memory_profile_model(self) -> None:
        mem = MemoryProfile()
        mem.current_bytes = 1024
        mem.peak_bytes = 2048
        d = mem.to_dict()
        assert d["current_bytes"] == 1024


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


class TestBenchmark:
    @pytest.mark.asyncio
    async def test_run_async(self) -> None:
        runner = BenchmarkRunner()

        async def fast_func() -> None:
            pass

        result = await runner.run_async("test_op", fast_func, category="api", iterations=20, warmup=2)
        assert result.iterations == 20
        assert result.stats["avg"] >= 0
        assert result.stats["throughput"] >= 0

    def test_run_sync(self) -> None:
        runner = BenchmarkRunner()

        def fast_func() -> None:
            pass

        result = runner.run_sync("test_op", fast_func, category="api", iterations=20, warmup=2)
        assert result.iterations == 20
        assert result.stats["min"] >= 0

    @pytest.mark.asyncio
    async def test_benchmark_suite(self) -> None:
        runner = BenchmarkRunner()

        async def func() -> None:
            pass

        await runner.run_async("op1", func, category="api")
        await runner.run_async("op2", func, category="execution")
        assert runner.suite.count() == 2
        results = runner.get_results("api")
        assert len(results) == 1
        summary = runner.summary()
        assert "api" in summary

    def test_benchmark_result_stats(self) -> None:
        result = BenchmarkResult("test", "op", 5, [1.0, 2.0, 3.0, 4.0, 5.0])
        assert result.stats["min"] == 1.0
        assert result.stats["max"] == 5.0
        assert result.stats["avg"] == 3.0

    def test_benchmark_result_empty(self) -> None:
        result = BenchmarkResult("test", "op", 0, [])
        assert result.stats["throughput"] == 0

    def test_benchmark_result_to_dict(self) -> None:
        result = BenchmarkResult("test", "op", 10, [1.0] * 10)
        d = result.to_dict()
        assert d["category"] == "test"
        assert d["iterations"] == 10


# ---------------------------------------------------------------------------
# Cache Optimizer
# ---------------------------------------------------------------------------


class TestCacheOptimizer:
    def test_stats(self) -> None:
        co = CacheOptimizer()
        co.record_hit("memory_cache")
        co.record_hit("memory_cache")
        co.record_miss("memory_cache")
        stats = co.get_stats("memory_cache")
        assert stats["hits"] == 2
        assert stats["misses"] == 1

    def test_all_stats(self) -> None:
        co = CacheOptimizer()
        all_stats = co.get_stats()
        assert len(all_stats) > 0

    def test_recommendations_low_hit_ratio(self) -> None:
        co = CacheOptimizer()
        for _ in range(20):
            co.record_miss("memory_cache")
        for _ in range(5):
            co.record_hit("memory_cache")
        recs = co.get_recommendations()
        assert len(recs) > 0

    def test_optimize(self) -> None:
        co = CacheOptimizer()
        result = co.optimize("memory_cache")
        assert result["optimized"] is True

    def test_cache_stats_to_dict(self) -> None:
        s = CacheStats("test", 100, "lru")
        s.record_hit()
        d = s.to_dict()
        assert d["name"] == "test"
        assert d["hits"] == 1


# ---------------------------------------------------------------------------
# Query Optimizer
# ---------------------------------------------------------------------------


class TestQueryOptimizer:
    def test_record_query(self) -> None:
        qo = QueryOptimizer()
        qo.record_query("SELECT *", 50.0, 100, "users")
        stats = qo.get_stats()
        assert stats["total"] == 1
        assert stats["slow"] == 0

    def test_slow_query_detection(self) -> None:
        qo = QueryOptimizer()
        qo.record_query("SELECT * FROM large_table", 200.0, 10000, "large_table")
        slow = qo.get_slow_queries()
        assert len(slow) == 1

    def test_recommendations_with_slow(self) -> None:
        qo = QueryOptimizer()
        qo.record_query("slow query", 200.0, 1000)
        recs = qo.get_recommendations()
        assert len(recs) > 0

    def test_optimize(self) -> None:
        qo = QueryOptimizer()
        result = qo.optimize()
        assert result["optimized"] is True


# ---------------------------------------------------------------------------
# Execution Optimizer
# ---------------------------------------------------------------------------


class TestExecutionOptimizer:
    def test_record_execution(self) -> None:
        eo = ExecutionOptimizer()
        eo.record_execution("op1", 50.0, parallel=True)
        stats = eo.get_stats()
        assert stats["total"] == 1
        assert stats["parallel"] == 1

    def test_record_batch(self) -> None:
        eo = ExecutionOptimizer()
        eo.record_batch("batch1", 10, 100.0)
        stats = eo.get_stats()
        assert "batch1" in stats["batch_stats"]

    def test_low_parallelization_recommendation(self) -> None:
        eo = ExecutionOptimizer()
        for _ in range(20):
            eo.record_execution("serial_op", 50.0, parallel=False)
        recs = eo.get_recommendations()
        assert any("parallel" in r["title"].lower() for r in recs)

    def test_optimize(self) -> None:
        eo = ExecutionOptimizer()
        result = eo.optimize()
        assert result["optimized"] is True


# ---------------------------------------------------------------------------
# Scheduler Optimizer
# ---------------------------------------------------------------------------


class TestSchedulerOptimizer:
    def test_record_job(self) -> None:
        so = SchedulerOptimizer()
        now = time.time()
        so.record_job("job1", now, now + 0.01, 5.0)
        stats = so.get_stats()
        assert stats["total_jobs"] == 1

    def test_recommendations(self) -> None:
        so = SchedulerOptimizer()
        now = time.time()
        for i in range(10):
            so.record_job(f"job{i}", now, now + 0.1, 10.0)
        recs = so.get_recommendations()
        assert len(recs) > 0


# ---------------------------------------------------------------------------
# Workflow Optimizer
# ---------------------------------------------------------------------------


class TestWorkflowOptimizer:
    def test_record_workflow(self) -> None:
        wo = WorkflowOptimizer()
        wo.record_workflow("wf1", 5, 100.0, 2)
        stats = wo.get_stats()
        assert stats["total"] == 1

    def test_recommendations_low_parallel(self) -> None:
        wo = WorkflowOptimizer()
        for _ in range(5):
            wo.record_workflow("wf", 10, 100.0, 0)
        recs = wo.get_recommendations()
        assert len(recs) > 0


# ---------------------------------------------------------------------------
# Vector Optimizer
# ---------------------------------------------------------------------------


class TestVectorOptimizer:
    def test_record_search(self) -> None:
        vo = VectorOptimizer()
        vo.record_search(768, 10, 25.0, indexed=True)
        stats = vo.get_stats()
        assert stats["total"] == 1

    def test_recommendations_low_index(self) -> None:
        vo = VectorOptimizer()
        for _ in range(10):
            vo.record_search(768, 10, 25.0, indexed=False)
        recs = vo.get_recommendations()
        assert len(recs) > 0


# ---------------------------------------------------------------------------
# RAG Optimizer
# ---------------------------------------------------------------------------


class TestRAGOptimizer:
    def test_record_retrieval(self) -> None:
        ro = RAGOptimizer()
        ro.record_retrieval(100, 5, True, 150.0)
        stats = ro.get_stats()
        assert stats["total"] == 1

    def test_recommendations_high_latency(self) -> None:
        ro = RAGOptimizer()
        for _ in range(5):
            ro.record_retrieval(100, 5, False, 300.0)
        recs = ro.get_recommendations()
        assert len(recs) > 0


# ---------------------------------------------------------------------------
# Model Optimizer
# ---------------------------------------------------------------------------


class TestModelOptimizer:
    def test_record_call(self) -> None:
        mo = ModelOptimizer()
        mo.record_call("gpt-4", 500, 1000.0, cached=False)
        stats = mo.get_stats()
        assert stats["total"] == 1

    def test_recommendations_low_cache(self) -> None:
        mo = ModelOptimizer()
        for _ in range(10):
            mo.record_call("gpt-4", 500, 100.0, cached=False)
        recs = mo.get_recommendations()
        assert len(recs) > 0


# ---------------------------------------------------------------------------
# Resource Optimizer
# ---------------------------------------------------------------------------


class TestResourceOptimizer:
    def test_record_snapshot(self) -> None:
        ro = ResourceOptimizer()
        ro.record_snapshot(cpu_percent=50.0, memory_mb=256.0, open_files=100, threads=20)
        stats = ro.get_stats()
        assert stats["snapshots"] == 1

    def test_recommendations_high_cpu(self) -> None:
        ro = ResourceOptimizer()
        ro.record_snapshot(cpu_percent=90.0, memory_mb=200.0)
        recs = ro.get_recommendations()
        assert any("cpu" in r["title"].lower() for r in recs)


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


class TestDiagnosticsEngine:
    def test_analyze(self) -> None:
        de = DiagnosticsEngine()
        report = de.analyze(
            latency_stats={"op1": {"avg": 150, "min": 10, "max": 300}},
            cache_stats=[{"name": "mem", "hit_ratio": 0.3, "hits": 3, "misses": 7}],
            query_stats={"slow": 2, "total": 10},
            execution_stats={"total": 20, "parallel": 5},
        )
        assert isinstance(report, DiagnosticReport)
        assert len(report.hotspots) > 0 or len(report.bottlenecks) > 0

    def test_report_to_dict(self) -> None:
        report = DiagnosticReport()
        d = report.to_dict()
        assert "hotspots" in d
        assert "bottlenecks" in d

    def test_report_summary(self) -> None:
        report = DiagnosticReport()
        h = Hotspot("test", "high", "metric", 200, 100, "message")
        report.hotspots.append(h)
        s = report.summary()
        assert s["total_hotspots"] == 1

    def test_get_recommendations(self) -> None:
        de = DiagnosticsEngine()
        report = DiagnosticReport()
        report.hotspots.append(Hotspot("latency", "high", "op", 200, 100, "slow"))
        recs = de.get_recommendations(report)
        assert len(recs) > 0

    def test_get_reports(self) -> None:
        de = DiagnosticsEngine()
        de.analyze()
        reports = de.get_reports()
        assert len(reports) == 1


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestPerformanceMetrics:
    def test_collector(self) -> None:
        mc = PerformanceMetricsCollector()
        mc.start()
        mc.record_latency("op1", 50.0)
        mc.record_latency("op1", 70.0)
        mc.record_cache_hit()
        mc.record_cache_hit()
        mc.record_cache_miss()
        mc.record_query_time(30.0)
        mc.record_execution_time(40.0)
        snap = mc.snapshot()
        assert snap.latency["op1"] == 60.0
        assert snap.cache_hit_ratio == 2 / 3

    def test_latency_stats(self) -> None:
        mc = PerformanceMetricsCollector()
        mc.start()
        for i in range(10):
            mc.record_latency("op", float(i))
        stats = mc.get_latency_stats()
        assert "op" in stats
        assert stats["op"]["count"] == 10

    def test_metrics_to_dict(self) -> None:
        m = PerformanceMetrics(latency={"op": 1.0}, cache_hit_ratio=0.8)
        d = m.to_dict()
        assert d["cache_hit_ratio"] == 0.8


# ---------------------------------------------------------------------------
# Tracing
# ---------------------------------------------------------------------------


class TestPerformanceTracer:
    def test_trace_lifecycle(self) -> None:
        t = PerformanceTracer()
        tid = t.start_trace("op1")
        assert t.count() == 1
        t.finish_trace(tid)
        trace = t.get_trace(tid)
        assert trace is not None
        assert trace["status"] == "completed"
        assert trace["duration_ms"] is not None

    def test_trace_error(self) -> None:
        t = PerformanceTracer()
        tid = t.start_trace("op1")
        t.finish_trace(tid, status="error", error="boom")
        trace = t.get_trace(tid)
        assert trace["error"] == "boom"

    def test_get_traces_limit(self) -> None:
        t = PerformanceTracer()
        for i in range(10):
            t.start_trace(f"op_{i}")
        traces = t.get_traces(3)
        assert len(traces) == 3

    def test_clear(self) -> None:
        t = PerformanceTracer()
        t.start_trace("op1")
        t.clear()
        assert t.count() == 0


# ---------------------------------------------------------------------------
# Optimizer (main)
# ---------------------------------------------------------------------------


class TestPerformanceOptimizer:
    @pytest.mark.asyncio
    async def test_start_and_stop(self) -> None:
        opt = PerformanceOptimizer()
        await opt.start()
        assert opt.is_running()
        await opt.shutdown()
        assert not opt.is_running()

    @pytest.mark.asyncio
    async def test_health(self) -> None:
        opt = PerformanceOptimizer()
        await opt.start()
        h = opt.get_health()
        assert h["status"] == "healthy"
        assert h["profiler_active"] is True
        await opt.shutdown()

    @pytest.mark.asyncio
    async def test_recommendations(self) -> None:
        opt = PerformanceOptimizer()
        await opt.start()
        recs = opt.get_recommendations()
        assert isinstance(recs, list)
        await opt.shutdown()

    @pytest.mark.asyncio
    async def test_diagnostics(self) -> None:
        opt = PerformanceOptimizer()
        await opt.start()
        report = opt.run_diagnostics()
        assert isinstance(report, DiagnosticReport)
        await opt.shutdown()

    @pytest.mark.asyncio
    async def test_metrics(self) -> None:
        opt = PerformanceOptimizer()
        await opt.start()
        opt.record_latency("test_op", 50.0)
        opt.record_cache_hit("memory_cache")
        opt.record_query("SELECT 1", 10.0)
        opt.record_execution("op", 20.0)
        m = opt.get_metrics()
        assert m.latency.get("test_op", 0) > 0
        await opt.shutdown()

    @pytest.mark.asyncio
    async def test_traces(self) -> None:
        opt = PerformanceOptimizer()
        await opt.start()
        traces = opt.get_traces()
        assert isinstance(traces, list)
        await opt.shutdown()

    @pytest.mark.asyncio
    async def test_record_operations(self) -> None:
        opt = PerformanceOptimizer()
        await opt.start()
        opt.record_vector_search(768, 10, 25.0)
        opt.record_model_call("gpt-4", 500, 1000.0)
        opt.record_rag_retrieval(100, 5, True, 150.0)
        opt.record_cache_miss("embedding_cache")
        await opt.shutdown()

    def test_properties(self) -> None:
        opt = PerformanceOptimizer()
        assert opt.profiler is not None
        assert opt.benchmark is not None
        assert opt.cache_optimizer is not None
        assert opt.query_optimizer is not None
        assert opt.execution_optimizer is not None
        assert opt.scheduler_optimizer is not None
        assert opt.workflow_optimizer is not None
        assert opt.vector_optimizer is not None
        assert opt.rag_optimizer is not None
        assert opt.model_optimizer is not None
        assert opt.resource_optimizer is not None
        assert opt.diagnostics is not None
        assert opt.metrics is not None
        assert opt.tracer is not None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestPerformanceFactory:
    def test_create(self) -> None:
        engine = PerformanceFactory.create()
        assert engine is not None
        assert isinstance(engine, PerformanceOptimizer)

    def test_create_default(self) -> None:
        engine = PerformanceFactory.create_default()
        assert engine is not None

    def test_get_or_create(self) -> None:
        PerformanceFactory.reset()
        engine = PerformanceFactory.get_or_create()
        engine2 = PerformanceFactory.get_or_create()
        assert engine is engine2

    def test_reset(self) -> None:
        PerformanceFactory.reset()
        assert PerformanceFactory._instance is None


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(api_router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAPIEndpoints:
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient) -> None:
        resp = await client.get("/performance/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_profile(self, client: AsyncClient) -> None:
        resp = await client.get("/performance/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert "active" in data["data"]

    @pytest.mark.asyncio
    async def test_benchmarks(self, client: AsyncClient) -> None:
        resp = await client.get("/performance/benchmarks")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data["data"]

    @pytest.mark.asyncio
    async def test_diagnostics(self, client: AsyncClient) -> None:
        resp = await client.get("/performance/diagnostics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_recommendations(self, client: AsyncClient) -> None:
        resp = await client.get("/performance/recommendations")
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data["data"]

    @pytest.mark.asyncio
    async def test_metrics(self, client: AsyncClient) -> None:
        resp = await client.get("/performance/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_traces(self, client: AsyncClient) -> None:
        resp = await client.get("/performance/traces")
        assert resp.status_code == 200
        data = resp.json()
        assert "traces" in data["data"]

    @pytest.mark.asyncio
    async def test_profile_start(self, client: AsyncClient) -> None:
        resp = await client.post("/performance/profile/start?profile_type=cpu")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_profile_stop_nonexistent(self, client: AsyncClient) -> None:
        resp = await client.post("/performance/profile/stop?session_id=nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_benchmark_run(self, client: AsyncClient) -> None:
        resp = await client.post("/performance/benchmark/run?category=api&iterations=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["iterations"] == 10


# ---------------------------------------------------------------------------
# Integration — full workflow
# ---------------------------------------------------------------------------


class TestIntegrationWorkflow:
    @pytest.mark.asyncio
    async def test_full_optimization_cycle(self) -> None:
        opt = PerformanceOptimizer()
        await opt.start()
        for _ in range(20):
            opt.record_latency("op", 50.0)
            opt.record_cache_hit("memory_cache")
            opt.record_query("SELECT 1", 20.0)
            opt.record_execution("op", 30.0, parallel=True)
            opt.record_vector_search(768, 10, 25.0)
            opt.record_model_call("gpt-4", 500, 500.0)
        report = opt.run_diagnostics()
        assert isinstance(report, DiagnosticReport)
        recs = opt.get_recommendations()
        assert isinstance(recs, list)
        m = opt.get_metrics()
        assert m.latency.get("op", 0) > 0
        await opt.shutdown()

    @pytest.mark.asyncio
    async def test_profiling_with_benchmark(self) -> None:
        opt = PerformanceOptimizer()
        await opt.start()
        sid = opt.profiler.start_session("comprehensive")
        assert sid

        async def work() -> None:
            pass

        result = await opt.benchmark.run_async("quick_op", work, iterations=10)
        assert result.iterations == 10
        session = opt.profiler.stop_session(sid)
        assert session is not None
        await opt.shutdown()


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_profiling(self) -> None:
        p = Profiler()
        p.start()
        errors: list[Exception] = []

        async def profile_session() -> None:
            try:
                sid = p.start_session("memory")
                await asyncio.sleep(0.01)
                p.stop_session(sid)
            except Exception as exc:
                errors.append(exc)

        await asyncio.gather(*[profile_session() for _ in range(5)])
        assert not errors

    @pytest.mark.asyncio
    async def test_concurrent_metrics(self) -> None:
        mc = PerformanceMetricsCollector()
        mc.start()
        errors: list[Exception] = []

        async def record_metrics() -> None:
            try:
                for _ in range(100):
                    mc.record_latency("op", 10.0)
                    mc.record_cache_hit()
                    mc.record_query_time(5.0)
            except Exception as exc:
                errors.append(exc)

        await asyncio.gather(*[record_metrics() for _ in range(5)])
        assert not errors
        snap = mc.snapshot()
        assert snap.latency.get("op", 0) == 10.0

    @pytest.mark.asyncio
    async def test_concurrent_benchmarks(self) -> None:
        runner = BenchmarkRunner()

        async def fast() -> None:
            pass

        results = await asyncio.gather(*[
            runner.run_async(f"bench_{i}", fast, iterations=5)
            for i in range(5)
        ])
        assert len(results) == 5


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_diagnostics(self) -> None:
        de = DiagnosticsEngine()
        report = de.analyze()
        assert len(report.hotspots) == 0
        assert len(report.bottlenecks) == 0

    def test_empty_cache_stats(self) -> None:
        co = CacheOptimizer()
        recs = co.get_recommendations()
        assert len(recs) == 0

    def test_empty_query_stats(self) -> None:
        qo = QueryOptimizer()
        stats = qo.get_stats()
        assert stats["total"] == 0

    def test_empty_execution_stats(self) -> None:
        eo = ExecutionOptimizer()
        stats = eo.get_stats()
        assert stats["total"] == 0

    def test_profiler_without_start(self) -> None:
        p = Profiler()
        assert not p.is_running()

    def test_benchmark_zero_iterations(self) -> None:
        runner = BenchmarkRunner()

        def noop() -> None:
            pass

        result = runner.run_sync("noop", noop, iterations=0, warmup=0)
        assert result.iterations == 0

    def test_hotspot_to_dict(self) -> None:
        h = Hotspot("area", "high", "metric", 200, 100, "msg")
        d = h.to_dict()
        assert d["area"] == "area"
        assert d["severity"] == "high"

    def test_optimization_result(self) -> None:
        r = OptimizationResult("test", True, [{"key": "val"}], {"metric": 1.0}, 50.0)
        d = r.to_dict()
        assert d["area"] == "test"
        assert d["success"] is True

    def test_tracer_trim(self) -> None:
        t = PerformanceTracer(max_traces=3)
        for i in range(10):
            t.start_trace(f"op_{i}")
        assert t.count() <= 3
