"""Benchmarking framework."""

from __future__ import annotations

import statistics
import time
from typing import Any, Callable, Awaitable

from app.performance.enums import BenchmarkCategory


class BenchmarkResult:
    """Result of a single benchmark run."""

    __slots__ = ("category", "name", "iterations", "times_ms", "stats")

    def __init__(self, category: str, name: str, iterations: int, times_ms: list[float]) -> None:
        self.category = category
        self.name = name
        self.iterations = iterations
        self.times_ms = times_ms
        self.stats = self._compute_stats()

    def _compute_stats(self) -> dict[str, float]:
        if not self.times_ms:
            return {"min": 0, "max": 0, "avg": 0, "median": 0, "stdev": 0, "p95": 0, "p99": 0, "throughput": 0}
        s = sorted(self.times_ms)
        avg = statistics.mean(s)
        total_ms = sum(s)
        return {
            "min": s[0],
            "max": s[-1],
            "avg": avg,
            "median": statistics.median(s),
            "stdev": statistics.stdev(s) if len(s) > 1 else 0.0,
            "p95": s[int(len(s) * 0.95)] if len(s) > 1 else s[0],
            "p99": s[int(len(s) * 0.99)] if len(s) > 1 else s[0],
            "throughput": (self.iterations / (total_ms / 1000)) if total_ms > 0 else 0,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "name": self.name,
            "iterations": self.iterations,
            "stats": self.stats,
        }


class BenchmarkSuite:
    """Collection of benchmark results by category."""

    def __init__(self) -> None:
        self._results: dict[str, list[BenchmarkResult]] = {}

    def add(self, result: BenchmarkResult) -> None:
        self._results.setdefault(result.category, []).append(result)

    def get(self, category: str | None = None) -> list[BenchmarkResult]:
        if category:
            return list(self._results.get(category, []))
        return [r for results in self._results.values() for r in results]

    def summary(self) -> dict[str, Any]:
        summary: dict[str, Any] = {}
        for cat, results in self._results.items():
            all_times = [t for r in results for t in r.times_ms]
            summary[cat] = {
                "benchmarks": len(results),
                "total_iterations": sum(r.iterations for r in results),
                "avg_latency_ms": statistics.mean(all_times) if all_times else 0,
            }
        return summary

    def count(self) -> int:
        return sum(len(results) for results in self._results.values())


class BenchmarkRunner:
    """Runs benchmark suites with warmup and iteration control."""

    def __init__(self) -> None:
        self._suite = BenchmarkSuite()

    @property
    def suite(self) -> BenchmarkSuite:
        return self._suite

    async def run_async(
        self,
        name: str,
        func: Callable[..., Awaitable[Any]],
        category: str = "execution",
        iterations: int = 100,
        warmup: int = 10,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
    ) -> BenchmarkResult:
        kwargs = kwargs or {}
        for _ in range(warmup):
            await func(*args, **kwargs)
        times_ms: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            await func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            times_ms.append(elapsed)
        result = BenchmarkResult(category, name, iterations, times_ms)
        self._suite.add(result)
        return result

    def run_sync(
        self,
        name: str,
        func: Callable[..., Any],
        category: str = "execution",
        iterations: int = 100,
        warmup: int = 10,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
    ) -> BenchmarkResult:
        kwargs = kwargs or {}
        for _ in range(warmup):
            func(*args, **kwargs)
        times_ms: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            times_ms.append(elapsed)
        result = BenchmarkResult(category, name, iterations, times_ms)
        self._suite.add(result)
        return result

    def get_results(self, category: str | None = None) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._suite.get(category)]

    def summary(self) -> dict[str, Any]:
        return self._suite.summary()
