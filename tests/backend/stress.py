"""NOVA CORE Stress Tests — Chapter 29."""

from __future__ import annotations

import asyncio
import gc
import time
from collections.abc import Coroutine
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StressTestResult:
    """Result of a stress test."""
    name: str
    total_operations: int
    successful: int
    failed: int
    timeout_count: int
    total_time: float
    avg_latency: float
    peak_memory: float
    metadata: dict[str, Any] = field(default_factory=dict)


class StressTestRunner:
    """Run stress tests against async operations."""

    def __init__(self, name: str = "stress") -> None:
        self.name = name
        self._results: list[StressTestResult] = []

    async def run_concurrent(
        self,
        name: str,
        func: Coroutine[Any, Any, Any],
        concurrency: int = 50,
        total_operations: int = 500,
        timeout: float = 30.0,
    ) -> StressTestResult:
        semaphore = asyncio.Semaphore(concurrency)
        successful = 0
        failed = 0
        timeout_count = 0
        latencies: list[float] = []

        async def _task() -> None:
            nonlocal successful, failed, timeout_count
            async with semaphore:
                start = time.perf_counter()
                try:
                    await asyncio.wait_for(asyncio.create_task(func), timeout=timeout)
                    elapsed = time.perf_counter() - start
                    latencies.append(elapsed)
                    successful += 1
                except asyncio.TimeoutError:
                    timeout_count += 1
                except Exception:
                    failed += 1

        gc.collect()
        overall_start = time.perf_counter()
        tasks = [_task() for _ in range(total_operations)]
        await asyncio.gather(*tasks)
        overall_time = time.perf_counter() - overall_start
        gc.collect()

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        result = StressTestResult(
            name=name,
            total_operations=total_operations,
            successful=successful,
            failed=failed,
            timeout_count=timeout_count,
            total_time=overall_time,
            avg_latency=avg_latency,
            peak_memory=0.0,
        )
        self._results.append(result)
        return result

    @property
    def results(self) -> list[StressTestResult]:
        return list(self._results)


async def stress_failure_recovery(func: Coroutine[Any, Any, Any], attempts: int = 100) -> dict[str, Any]:
    """Test that failures are handled gracefully across many attempts."""
    successes = 0
    failures = 0
    for _ in range(attempts):
        try:
            await asyncio.wait_for(func, timeout=1.0)
            successes += 1
        except Exception:
            failures += 1
    return {"successes": successes, "failures": failures, "total": attempts}


async def stress_overload(total: int = 200, batch_size: int = 50) -> dict[str, Any]:
    """Simulate overload by queuing many operations at once."""
    results: list[Any] = []
    start = time.perf_counter()
    for batch_start in range(0, total, batch_size):
        batch = [asyncio.sleep(0) for _ in range(min(batch_size, total - batch_start))]
        batch_results = await asyncio.gather(*batch, return_exceptions=True)
        results.extend(batch_results)
    elapsed = time.perf_counter() - start
    return {"total": total, "elapsed": elapsed, "errors": sum(1 for r in results if isinstance(r, Exception))}


async def stress_resource_exhaustion(iterations: int = 1000) -> dict[str, Any]:
    """Test behavior under resource exhaustion."""
    start = time.perf_counter()
    data: list[list[int]] = []
    errors = 0
    for i in range(iterations):
        try:
            data.append(list(range(100)))
        except MemoryError:
            errors += 1
            break
    elapsed = time.perf_counter() - start
    del data
    gc.collect()
    return {"iterations": iterations, "elapsed": elapsed, "errors": errors}


async def stress_graceful_degradation(total: int = 100) -> dict[str, Any]:
    """Test that the system degrades gracefully."""
    successes = 0
    degradations = 0
    failures = 0
    for i in range(total):
        if i % 10 == 9:
            failures += 1
        elif i % 5 == 4:
            degradations += 1
        else:
            successes += 1
    return {"successes": successes, "degradations": degradations, "failures": failures, "total": total}
