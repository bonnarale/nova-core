"""NOVA CORE Test Reporting — Chapter 29.

Provides test reporting infrastructure for coverage, timing, failures,
benchmark summaries, and regression summaries.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class CoverageReport:
    """Test coverage report."""
    total_lines: int = 0
    covered_lines: int = 0
    total_functions: int = 0
    covered_functions: int = 0
    total_classes: int = 0
    covered_classes: int = 0
    modules: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def line_coverage(self) -> float:
        return (self.covered_lines / self.total_lines * 100) if self.total_lines > 0 else 0.0

    @property
    def function_coverage(self) -> float:
        return (self.covered_functions / self.total_functions * 100) if self.total_functions > 0 else 0.0

    @property
    def class_coverage(self) -> float:
        return (self.covered_classes / self.total_classes * 100) if self.total_classes > 0 else 0.0

    def summary(self) -> str:
        return (
            f"Coverage: {self.line_coverage:.1f}% lines, "
            f"{self.function_coverage:.1f}% functions, "
            f"{self.class_coverage:.1f}% classes"
        )


@dataclass
class TimingReport:
    """Test timing report."""
    total_duration: float = 0.0
    test_durations: dict[str, float] = field(default_factory=dict)
    slowest_tests: list[tuple[str, float]] = field(default_factory=list)
    fastest_tests: list[tuple[str, float]] = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"Total Duration: {self.total_duration:.2f}s"]
        if self.slowest_tests:
            lines.append("Slowest tests:")
            for name, dur in self.slowest_tests[:5]:
                lines.append(f"  {name}: {dur:.3f}s")
        return "\n".join(lines)


@dataclass
class FailureReport:
    """Test failure report."""
    total_failures: int = 0
    failures: list[dict[str, str]] = field(default_factory=list)

    def summary(self) -> str:
        if self.total_failures == 0:
            return "No failures"
        lines = [f"Failures: {self.total_failures}"]
        for f in self.failures[:10]:
            lines.append(f"  FAIL: {f.get('name', 'unknown')}")
            if "message" in f:
                lines.append(f"    {f['message']}")
        return "\n".join(lines)


@dataclass
class BenchmarkSummaryReport:
    """Benchmark summary report."""
    suite_name: str = ""
    benchmarks: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"Benchmark Suite: {self.suite_name}"]
        for b in self.benchmarks:
            lines.append(
                f"  {b.get('name', '?')}: avg={b.get('avg_time', 0)*1000:.2f}ms, "
                f"p95={b.get('p95_time', 0)*1000:.2f}ms, "
                f"throughput={b.get('throughput', 0):.1f} ops/s"
            )
        return "\n".join(lines)


@dataclass
class RegressionSummaryReport:
    """Regression summary report."""
    timestamp: str = ""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    regressions: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Regression Report ({self.timestamp})",
            f"Total: {self.total_tests}, Passed: {self.passed}, Failed: {self.failed}",
        ]
        if self.regressions:
            lines.append(f"Regressions ({len(self.regressions)}):")
            for r in self.regressions[:10]:
                lines.append(f"  - {r}")
        else:
            lines.append("No regressions detected")
        return "\n".join(lines)


class TestReporter:
    """Collect and generate test reports."""

    def __init__(self) -> None:
        self._coverage = CoverageReport()
        self._timing = TimingReport()
        self._failures = FailureReport()
        self._benchmarks: list[BenchmarkSummaryReport] = []
        self._regressions = RegressionSummaryReport(timestamp=datetime.now(timezone.utc).isoformat())
        self._test_start: float | None = None

    def start(self) -> None:
        self._test_start = time.perf_counter()

    def record_test(self, name: str, passed: bool, duration: float, message: str = "") -> None:
        self._timing.test_durations[name] = duration
        if not passed:
            self._failures.total_failures += 1
            self._failures.failures.append({"name": name, "message": message})
        if passed:
            self._regressions.passed += 1
        else:
            self._regressions.failed += 1
        self._regressions.total_tests += 1

    def set_coverage(self, coverage: CoverageReport) -> None:
        self._coverage = coverage

    def add_benchmark(self, report: BenchmarkSummaryReport) -> None:
        self._benchmarks.append(report)

    def generate(self) -> dict[str, Any]:
        if self._test_start:
            self._timing.total_duration = time.perf_counter() - self._test_start
        sorted_durs = sorted(self._timing.test_durations.items(), key=lambda x: x[1], reverse=True)
        self._timing.slowest_tests = sorted_durs[:10]
        self._timing.fastest_tests = sorted_durs[-10:] if len(sorted_durs) > 10 else []
        return {
            "coverage": self._coverage.summary(),
            "timing": self._timing.summary(),
            "failures": self._failures.summary(),
            "regressions": self._regressions.summary(),
            "benchmarks": [b.summary() for b in self._benchmarks],
        }

    def to_json(self, path: str | None = None) -> str:
        data = self.generate()
        result = json.dumps(data, indent=2)
        if path:
            with open(path, "w") as f:
                f.write(result)
        return result
