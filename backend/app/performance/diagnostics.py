"""Performance diagnostics engine."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.performance.enums import OptimizationSeverity


class Hotspot:
    """A performance hotspot."""

    __slots__ = ("area", "severity", "metric", "value", "threshold", "message")

    def __init__(self, area: str, severity: str, metric: str, value: float, threshold: float, message: str) -> None:
        self.area = area
        self.severity = severity
        self.metric = metric
        self.value = value
        self.threshold = threshold
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {
            "area": self.area,
            "severity": self.severity,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
        }


class DiagnosticReport:
    """Complete diagnostic report."""

    __slots__ = ("hotspots", "bottlenecks", "slow_queries", "allocations", "blocking_calls", "timestamp")

    def __init__(self) -> None:
        self.hotspots: list[Hotspot] = []
        self.bottlenecks: list[dict[str, Any]] = []
        self.slow_queries: list[dict[str, Any]] = []
        self.allocations: list[dict[str, Any]] = []
        self.blocking_calls: list[dict[str, Any]] = []
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "hotspots": [h.to_dict() for h in self.hotspots],
            "bottlenecks": self.bottlenecks,
            "slow_queries": self.slow_queries,
            "allocations": self.allocations,
            "blocking_calls": self.blocking_calls,
            "timestamp": self.timestamp,
        }

    def summary(self) -> dict[str, Any]:
        severity_counts: dict[str, int] = {}
        for h in self.hotspots:
            severity_counts[h.severity] = severity_counts.get(h.severity, 0) + 1
        return {
            "total_hotspots": len(self.hotspots),
            "total_bottlenecks": len(self.bottlenecks),
            "total_slow_queries": len(self.slow_queries),
            "total_allocations": len(self.allocations),
            "total_blocking_calls": len(self.blocking_calls),
            "severity_counts": severity_counts,
        }


class DiagnosticsEngine:
    """Generates optimization diagnostics reports."""

    def __init__(self) -> None:
        self._reports: list[DiagnosticReport] = []
        self._lock = threading.RLock()

    def analyze(
        self,
        latency_stats: dict[str, Any] | None = None,
        cache_stats: list[dict[str, Any]] | None = None,
        query_stats: dict[str, Any] | None = None,
        execution_stats: dict[str, Any] | None = None,
        resource_stats: dict[str, Any] | None = None,
    ) -> DiagnosticReport:
        report = DiagnosticReport()
        latency_stats = latency_stats or {}
        cache_stats = cache_stats or []
        query_stats = query_stats or {}
        execution_stats = execution_stats or {}
        resource_stats = resource_stats or {}

        for op, stats in latency_stats.items():
            if isinstance(stats, dict):
                avg = stats.get("avg", 0)
                if avg > 100:
                    report.hotspots.append(Hotspot(
                        area="latency",
                        severity="high" if avg > 500 else "medium",
                        metric=op,
                        value=avg,
                        threshold=100.0,
                        message=f"Operation '{op}' avg latency is {avg:.1f}ms",
                    ))

        for cs in cache_stats:
            if isinstance(cs, dict):
                ratio = cs.get("hit_ratio", 1.0)
                if ratio < 0.5 and cs.get("hits", 0) + cs.get("misses", 0) > 10:
                    report.bottlenecks.append({
                        "area": "cache",
                        "name": cs.get("name", "unknown"),
                        "hit_ratio": ratio,
                        "message": f"Cache '{cs.get('name')}' has low hit ratio ({ratio:.2%})",
                    })

        if query_stats.get("slow", 0) > 0:
            report.slow_queries.append({
                "count": query_stats["slow"],
                "threshold_ms": 100.0,
                "message": f"{query_stats['slow']} queries exceed 100ms threshold",
            })

        if execution_stats.get("parallel", 0) < execution_stats.get("total", 0) * 0.3:
            if execution_stats.get("total", 0) > 10:
                report.blocking_calls.append({
                    "area": "execution",
                    "message": "Low parallelization ratio detected",
                    "serial_ratio": 1 - execution_stats.get("parallel", 0) / max(execution_stats.get("total", 1), 1),
                })

        with self._lock:
            self._reports.append(report)
        return report

    def get_reports(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._reports[-limit:]]

    def get_recommendations(self, report: DiagnosticReport) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        for hotspot in report.hotspots:
            recs.append({
                "area": hotspot.area,
                "severity": hotspot.severity,
                "title": f"Hotspot: {hotspot.metric}",
                "description": hotspot.message,
                "expected_improvement": "Varies based on optimization",
            })
        for bottleneck in report.bottlenecks:
            recs.append({
                "area": bottleneck.get("area", "unknown"),
                "severity": "high",
                "title": f"Bottleneck: {bottleneck.get('name', 'unknown')}",
                "description": bottleneck.get("message", ""),
                "expected_improvement": "10-30% improvement",
            })
        return recs
