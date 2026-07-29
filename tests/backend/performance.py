"""NOVA CORE Performance Benchmark Suites — Chapter 29."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BenchmarkResult:
    """Result of a performance benchmark."""
    name: str
    iterations: int
    total_time: float
    min_time: float
    max_time: float
    avg_time: float
    p50_time: float
    p95_time: float
    p99_time: float
    throughput: float
    metadata: dict[str, Any] = field(default_factory=dict)


class BenchmarkSuite:
    """Generic benchmark runner for synchronous and async functions."""

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self._results: list[BenchmarkResult] = []

    def run_sync(
        self,
        name: str,
        func: Callable[[], Any],
        iterations: int = 100,
        warmup: int = 5,
    ) -> BenchmarkResult:
        for _ in range(warmup):
            func()
        times: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        result = self._compute_result(name, iterations, times)
        self._results.append(result)
        return result

    async def run_async(
        self,
        name: str,
        func: Callable[[], Coroutine[Any, Any, Any]],
        iterations: int = 100,
        warmup: int = 5,
    ) -> BenchmarkResult:
        for _ in range(warmup):
            await func()
        times: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            await func()
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        result = self._compute_result(name, iterations, times)
        self._results.append(result)
        return result

    @staticmethod
    def _compute_result(name: str, iterations: int, times: list[float]) -> BenchmarkResult:
        sorted_times = sorted(times)
        total = sum(times)
        p50_idx = int(len(sorted_times) * 0.50)
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)
        return BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time=total,
            min_time=sorted_times[0],
            max_time=sorted_times[-1],
            avg_time=total / len(times),
            p50_time=sorted_times[min(p50_idx, len(sorted_times) - 1)],
            p95_time=sorted_times[min(p95_idx, len(sorted_times) - 1)],
            p99_time=sorted_times[min(p99_idx, len(sorted_times) - 1)],
            throughput=iterations / total if total > 0 else 0,
        )

    @property
    def results(self) -> list[BenchmarkResult]:
        return list(self._results)

    def summary(self) -> str:
        lines = [f"Benchmark Suite: {self.name}", "=" * 60]
        for r in self._results:
            lines.append(f"  {r.name}: {r.iterations} iters, avg={r.avg_time*1000:.2f}ms, p95={r.p95_time*1000:.2f}ms, throughput={r.throughput:.1f} ops/s")
        return "\n".join(lines)


class PerformanceProfiler:
    """Profile memory and timing of a code block."""

    def __init__(self, name: str = "profile") -> None:
        self.name = name
        self._marks: list[tuple[str, float]] = []
        self._start_time: float | None = None

    def start(self) -> None:
        self._start_time = time.perf_counter()
        self._marks = [("start", self._start_time)]

    def mark(self, label: str) -> None:
        self._marks.append((label, time.perf_counter()))

    def stop(self) -> dict[str, Any]:
        end = time.perf_counter()
        self._marks.append(("end", end))
        durations: dict[str, float] = {}
        for i in range(1, len(self._marks)):
            label = self._marks[i][0]
            durations[label] = self._marks[i][1] - self._marks[i - 1][1]
        total = (end - self._marks[0][1]) if self._marks else 0.0
        return {"name": self.name, "total": total, "sections": durations}


def benchmark_cognitive_pipeline() -> BenchmarkSuite:
    """Create a benchmark suite for the cognitive pipeline."""
    suite = BenchmarkSuite("cognitive_pipeline")

    async def _dummy_cognitive() -> None:
        await asyncio.sleep(0)

    asyncio.run(suite.run_async("cognitive_decision", _dummy_cognitive, iterations=50))
    return suite


def benchmark_retrieval() -> BenchmarkSuite:
    """Create a benchmark suite for retrieval operations."""
    suite = BenchmarkSuite("retrieval")

    async def _dummy_retrieval() -> None:
        await asyncio.sleep(0)

    asyncio.run(suite.run_async("retrieval_query", _dummy_retrieval, iterations=50))
    return suite


def benchmark_vector_search() -> BenchmarkSuite:
    """Create a benchmark suite for vector search."""
    suite = BenchmarkSuite("vector_search")

    async def _dummy_search() -> None:
        await asyncio.sleep(0)

    asyncio.run(suite.run_async("vector_similarity", _dummy_search, iterations=50))
    return suite


def benchmark_execution_engine() -> BenchmarkSuite:
    """Create a benchmark suite for execution engine."""
    suite = BenchmarkSuite("execution_engine")

    async def _dummy_exec() -> None:
        await asyncio.sleep(0)

    asyncio.run(suite.run_async("task_execution", _dummy_exec, iterations=50))
    return suite


def benchmark_workflows() -> BenchmarkSuite:
    """Create a benchmark suite for workflows."""
    suite = BenchmarkSuite("workflows")

    async def _dummy_workflow() -> None:
        await asyncio.sleep(0)

    asyncio.run(suite.run_async("workflow_step", _dummy_workflow, iterations=50))
    return suite


def benchmark_scheduler() -> BenchmarkSuite:
    """Create a benchmark suite for the scheduler."""
    suite = BenchmarkSuite("scheduler")

    async def _dummy_schedule() -> None:
        await asyncio.sleep(0)

    asyncio.run(suite.run_async("job_schedule", _dummy_schedule, iterations=50))
    return suite


def benchmark_plugins() -> BenchmarkSuite:
    """Create a benchmark suite for plugins."""
    suite = BenchmarkSuite("plugins")

    async def _dummy_plugin() -> None:
        await asyncio.sleep(0)

    asyncio.run(suite.run_async("plugin_hook", _dummy_plugin, iterations=50))
    return suite


def benchmark_api() -> BenchmarkSuite:
    """Create a benchmark suite for API operations."""
    suite = BenchmarkSuite("api")

    async def _dummy_api() -> None:
        await asyncio.sleep(0)

    asyncio.run(suite.run_async("api_request", _dummy_api, iterations=50))
    return suite
