"""Observability structured logging — JSON structured logging with correlation IDs."""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import uuid4

from app.observability.models import LogEntry, LogSeverity


class ObservabilityLogger:
    """Structured JSON logger with correlation support."""

    def __init__(self, max_entries: int = 1000) -> None:
        self._max_entries = max_entries
        self._entries: list[LogEntry] = []

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def log(
        self,
        severity: str,
        message: str,
        source: str = "",
        correlation_id: str | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        request_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        agent_id: str | None = None,
        workflow_id: str | None = None,
        task_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> LogEntry:
        entry = LogEntry(
            entry_id=str(uuid4()),
            severity=LogSeverity(severity) if severity in [s.value for s in LogSeverity] else LogSeverity.INFO,
            message=message,
            source=source,
            timestamp=time.time(),
            correlation_id=correlation_id,
            trace_id=trace_id,
            span_id=span_id,
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
            agent_id=agent_id,
            workflow_id=workflow_id,
            task_id=task_id,
            extra=extra or {},
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        return entry

    def debug(self, message: str, **kwargs: Any) -> LogEntry:
        return self.log("debug", message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> LogEntry:
        return self.log("info", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> LogEntry:
        return self.log("warning", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> LogEntry:
        return self.log("error", message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> LogEntry:
        return self.log("critical", message, **kwargs)

    def get_logs(self, severity: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        entries = self._entries
        if severity:
            entries = [e for e in entries if e.severity.value == severity]
        return [e.to_dict() for e in entries[-limit:]]

    def get_log(self, entry_id: str) -> LogEntry | None:
        for entry in self._entries:
            if entry.entry_id == entry_id:
                return entry
        return None

    def clear(self) -> int:
        count = len(self._entries)
        self._entries.clear()
        return count

    def to_dict(self, limit: int = 100) -> dict[str, Any]:
        logs = self.get_logs(limit=limit)
        return {"logs": logs, "total": len(self._entries)}
