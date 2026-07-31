"""NOVA CORE Regression Testing — Chapter 29.

Provides infrastructure to automatically run all existing tests and
detect regressions.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    status: str  # "passed", "failed", "error", "skipped"
    duration: float = 0.0
    message: str = ""
    traceback: str = ""


@dataclass
class RegressionSuiteResult:
    """Result of a regression test suite run."""
    suite_name: str
    timestamp: str
    total: int
    passed: int
    failed: int
    errors: int
    skipped: int
    duration: float
    test_results: list[TestResult] = field(default_factory=list)
    regressions: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total * 100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class RegressionDetector:
    """Detect regressions by comparing test results across runs."""

    def __init__(self) -> None:
        self._baseline: dict[str, str] = {}
        self._current: dict[str, str] = {}

    def set_baseline(self, results: dict[str, str]) -> None:
        """Set baseline test results (name -> status)."""
        self._baseline = dict(results)

    def set_current(self, results: dict[str, str]) -> None:
        """Set current test results (name -> status)."""
        self._current = dict(results)

    def detect(self) -> dict[str, Any]:
        """Detect regressions between baseline and current."""
        regressions: list[str] = []
        new_passes: list[str] = []
        for test_name, baseline_status in self._baseline.items():
            current_status = self._current.get(test_name, "missing")
            if baseline_status == "passed" and current_status != "passed":
                regressions.append(test_name)
        for test_name, current_status in self._current.items():
            baseline_status = self._baseline.get(test_name, "missing")
            if current_status == "passed" and baseline_status != "passed":
                new_passes.append(test_name)
        return {"regressions": regressions, "new_passes": new_passes, "total_regressions": len(regressions)}


class RegressionSuite:
    """A named collection of regression test expectations."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._results: list[TestResult] = []

    def add_result(self, result: TestResult) -> None:
        self._results.append(result)

    def summary(self) -> RegressionSuiteResult:
        passed = sum(1 for r in self._results if r.status == "passed")
        failed = sum(1 for r in self._results if r.status == "failed")
        errors = sum(1 for r in self._results if r.status == "error")
        skipped = sum(1 for r in self._results if r.status == "skipped")
        duration = sum(r.duration for r in self._results)
        regressions = [r.name for r in self._results if r.status in ("failed", "error")]
        return RegressionSuiteResult(
            suite_name=self.name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total=len(self._results),
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            duration=duration,
            test_results=list(self._results),
            regressions=regressions,
        )


def create_regression_result(
    name: str, status: str, duration: float = 0.0, message: str = ""
) -> TestResult:
    """Create a TestResult with given parameters."""
    return TestResult(name=name, status=status, duration=duration, message=message)


def compare_results(
    baseline: dict[str, str], current: dict[str, str]
) -> dict[str, Any]:
    """Quick comparison of two result dicts."""
    detector = RegressionDetector()
    detector.set_baseline(baseline)
    detector.set_current(current)
    return detector.detect()
