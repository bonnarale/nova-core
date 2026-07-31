"""Reflection engine — execution review, outcome evaluation, failure/success analysis, lesson extraction."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.autonomy.enums import ReflectionType


class ReflectionRecord:
    """A single reflection record."""

    __slots__ = ("id", "type", "execution_id", "findings", "lessons", "timestamp", "metadata")

    def __init__(
        self,
        reflection_type: ReflectionType,
        execution_id: str = "",
        findings: list[str] | None = None,
        lessons: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.type = reflection_type
        self.execution_id = execution_id
        self.findings = findings or []
        self.lessons = lessons or []
        self.timestamp = time.time()
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "execution_id": self.execution_id,
            "findings": self.findings,
            "lessons": self.lessons,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class ReflectionEngine:
    """Performs reflective analysis on autonomous operations."""

    def __init__(self) -> None:
        self._records: list[ReflectionRecord] = []
        self._lessons: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    async def review_execution(self, execution_id: str, results: dict[str, Any]) -> dict[str, Any]:
        success = results.get("success", True)
        duration = results.get("duration_ms", 0)
        findings = []
        if success:
            findings.append(f"Execution {execution_id} completed successfully in {duration}ms")
        else:
            findings.append(f"Execution {execution_id} failed")
            error = results.get("error", "unknown")
            findings.append(f"Error: {error}")
        record = ReflectionRecord(
            reflection_type=ReflectionType.EXECUTION_REVIEW,
            execution_id=execution_id,
            findings=findings,
            metadata=results,
        )
        with self._lock:
            self._records.append(record)
        return record.to_dict()

    async def analyze_failure(self, execution_id: str, error: str) -> dict[str, Any]:
        findings = [
            f"Failure in execution {execution_id}",
            f"Root cause: {error}",
            "Recommendation: investigate upstream dependencies",
        ]
        lessons = [f"Avoid pattern: {error}"]
        record = ReflectionRecord(
            reflection_type=ReflectionType.FAILURE_ANALYSIS,
            execution_id=execution_id,
            findings=findings,
            lessons=lessons,
        )
        with self._lock:
            self._records.append(record)
            self._lessons.extend([{"lesson": l, "source": "failure_analysis"} for l in lessons])
        return record.to_dict()

    async def analyze_success(self, execution_id: str, results: dict[str, Any]) -> dict[str, Any]:
        findings = [
            f"Success in execution {execution_id}",
            f"Outcome: {results.get('summary', 'positive')}",
        ]
        lessons = [f"Success pattern: {results.get('pattern', 'standard')}"]
        record = ReflectionRecord(
            reflection_type=ReflectionType.SUCCESS_ANALYSIS,
            execution_id=execution_id,
            findings=findings,
            lessons=lessons,
        )
        with self._lock:
            self._records.append(record)
            self._lessons.extend([{"lesson": l, "source": "success_analysis"} for l in lessons])
        return record.to_dict()

    async def evaluate_outcome(self, execution_id: str, expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
        matched = sum(1 for k, v in expected.items() if actual.get(k) == v)
        total = max(len(expected), 1)
        alignment = matched / total
        findings = [f"Outcome alignment: {alignment:.1%} ({matched}/{total} metrics matched)"]
        record = ReflectionRecord(
            reflection_type=ReflectionType.OUTCOME_EVALUATION,
            execution_id=execution_id,
            findings=findings,
            metadata={"expected": expected, "actual": actual, "alignment": alignment},
        )
        with self._lock:
            self._records.append(record)
        return record.to_dict()

    async def extract_lessons(self, analyses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        extracted: list[dict[str, Any]] = []
        for analysis in analyses:
            for finding in analysis.get("findings", []):
                lesson = {"lesson": finding, "source": analysis.get("type", "analysis"), "timestamp": time.time()}
                extracted.append(lesson)
        with self._lock:
            self._lessons.extend(extracted)
        return extracted

    def get_records(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._records[-limit:]]

    def get_lessons(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._lessons[-limit:])

    def get_records_by_type(self, reflection_type: ReflectionType) -> list[dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._records if r.type == reflection_type]
