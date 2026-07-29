"""NOVA CORE Load Testing — Chapter 29."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Coroutine
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LoadTestResult:
    """Result of a load test."""
    name: str
    total_requests: int
    successful: int
    failed: int
    total_time: float
    throughput: float
    avg_latency: float
    min_latency: float
    max_latency: float
    p50_latency: float
    p95_latency: float
    p99_latency: float
    concurrency: int
    memory_usage_mb: float
    metadata: dict[str, Any] = field(default_factory=dict)


class LoadTestRunner:
    """Run load tests against async operations."""

    def __init__(self, name: str = "load") -> None:
        self.name = name
        self._results: list[LoadTestResult] = []

    async def run(
        self,
        name: str,
        func: Coroutine[Any, Any, Any],
        total_requests: int = 1000,
        concurrency: int = 50,
        timeout: float = 60.0,
    ) -> LoadTestResult:
        semaphore = asyncio.Semaphore(concurrency)
        latencies: list[float] = []
        successful = 0
        failed = 0

        async def _request() -> None:
            nonlocal successful, failed
            start = time.perf_counter()
            try:
                async with semaphore:
                    await asyncio.wait_for(func, timeout=timeout / concurrency)
                elapsed = time.perf_counter() - start
                latencies.append(elapsed)
                successful += 1
            except Exception:
                elapsed = time.perf_counter() - start
                latencies.append(elapsed)
                failed += 1

        overall_start = time.perf_counter()
        tasks = [_request() for _ in range(total_requests)]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - overall_start

        sorted_lat = sorted(latencies) if latencies else [0.0]
        n = len(sorted_lat)
        result = LoadTestResult(
            name=name,
            total_requests=total_requests,
            successful=successful,
            failed=failed,
            total_time=total_time,
            throughput=total_requests / total_time if total_time > 0 else 0,
            avg_latency=sum(sorted_lat) / n,
            min_latency=sorted_lat[0],
            max_latency=sorted_lat[-1],
            p50_latency=sorted_lat[int(n * 0.5)],
            p95_latency=sorted_lat[int(n * 0.95)],
            p99_latency=sorted_lat[int(n * 0.99)],
            concurrency=concurrency,
            memory_usage_mb=0.0,
        )
        self._results.append(result)
        return result

    @property
    def results(self) -> list[LoadTestResult]:
        return list(self._results)

    def summary(self) -> str:
        lines = [f"Load Test Suite: {self.name}", "=" * 60]
        for r in self._results:
            lines.append(f"  {r.name}: {r.total_requests} reqs, {r.concurrency} conc, throughput={r.throughput:.1f} r/s, p95={r.p95_latency*1000:.1f}ms, success={r.successful}, fail={r.failed}")
        return "\n".join(lines)


@dataclass
class ThroughputMeasurement:
    """Throughput measurement over a time window."""
    name: str
    operations: int
    duration: float
    ops_per_second: float


@dataclass
class LatencyMeasurement:
    """Latency measurement distribution."""
    name: str
    samples: int
    mean_ms: float
    median_ms: float
    std_dev_ms: float
    min_ms: float
    max_ms: float


@dataclass
class ConcurrencyMeasurement:
    """Concurrency measurement."""
    name: str
    concurrent_tasks: int
    completed: int
    failed: int
    avg_time: float


@dataclass
class MemoryMeasurement:
    """Memory usage measurement."""
    name: str
    before_mb: float
    after_mb: float
    delta_mb: float


@dataclass
class CPUMeasurement:
    """CPU usage measurement."""
    name: str
    avg_percent: float
    peak_percent: float
    samples: int
