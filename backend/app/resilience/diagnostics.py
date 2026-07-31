"""Resilience diagnostics."""

from __future__ import annotations

import threading
from typing import Any

from app.resilience.enums import CircuitState


class ResilienceDiagnostics:
    """Generates resilience diagnostic reports."""

    def __init__(self) -> None:
        self._reports: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def generate(
        self,
        circuit_breakers: dict[str, Any] | None = None,
        retry_stats: dict[str, Any] | None = None,
        timeout_events: list[dict[str, Any]] | None = None,
        failover_events: list[dict[str, Any]] | None = None,
        degraded_services: list[str] | None = None,
        recovery_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        report = {
            "circuit_breakers": circuit_breakers or {},
            "retry_stats": retry_stats or {},
            "timeout_events": (timeout_events or [])[-20:],
            "failover_events": (failover_events or [])[-20:],
            "degraded_services": degraded_services or [],
            "recovery_history": (recovery_history or [])[-20:],
        }
        with self._lock:
            self._reports.append(report)
        return report

    def get_reports(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._reports[-limit:])

    def get_recommendations(self, report: dict[str, Any]) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        cb_summary = report.get("circuit_breakers", {})
        open_count = cb_summary.get("open", 0)
        if open_count > 0:
            recs.append({
                "severity": "critical",
                "title": f"{open_count} circuit breaker(s) open",
                "description": "Investigate root cause of failing subsystems.",
            })
        retry_stats = report.get("retry_stats", {})
        if retry_stats.get("failure", 0) > retry_stats.get("total", 0) * 0.5:
            recs.append({
                "severity": "high",
                "title": "High retry failure rate",
                "description": "Consider increasing timeouts or adjusting retry policies.",
            })
        degraded = report.get("degraded_services", [])
        if len(degraded) > 3:
            recs.append({
                "severity": "high",
                "title": f"{len(degraded)} services degraded",
                "description": "Multiple services operating in degraded mode. Check system resources.",
            })
        return recs
