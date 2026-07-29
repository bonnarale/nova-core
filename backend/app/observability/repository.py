"""Observability repository — in-memory repository for observability data."""

from __future__ import annotations

import logging
from typing import Any

from app.observability.models import Alert, AlertRule, LogEntry, TraceSpan

logger = logging.getLogger(__name__)


class InMemoryObservabilityRepository:
    """In-memory repository for observability data: alerts, rules, logs, spans."""

    def __init__(self) -> None:
        self._alerts: dict[str, Alert] = {}
        self._rules: dict[str, AlertRule] = {}
        self._logs: dict[str, LogEntry] = {}
        self._spans: dict[str, TraceSpan] = {}

    async def store_alert(self, alert: Alert) -> None:
        self._alerts[alert.alert_id] = alert

    async def get_alert(self, alert_id: str) -> Alert | None:
        return self._alerts.get(alert_id)

    async def list_alerts(self, state: str | None = None, limit: int = 100, offset: int = 0) -> list[Alert]:
        alerts = list(self._alerts.values())
        if state:
            alerts = [a for a in alerts if a.state.value == state]
        return alerts[offset:offset + limit]

    async def delete_alert(self, alert_id: str) -> bool:
        return self._alerts.pop(alert_id, None) is not None

    async def store_rule(self, rule: AlertRule) -> None:
        self._rules[rule.rule_id] = rule

    async def get_rule(self, rule_id: str) -> AlertRule | None:
        return self._rules.get(rule_id)

    async def list_rules(self, limit: int = 100, offset: int = 0) -> list[AlertRule]:
        rules = list(self._rules.values())
        return rules[offset:offset + limit]

    async def delete_rule(self, rule_id: str) -> bool:
        return self._rules.pop(rule_id, None) is not None

    async def store_log(self, log_entry: LogEntry) -> None:
        self._logs[log_entry.entry_id] = log_entry

    async def get_log(self, entry_id: str) -> LogEntry | None:
        return self._logs.get(entry_id)

    async def list_logs(self, severity: str | None = None, limit: int = 100, offset: int = 0) -> list[LogEntry]:
        logs = list(self._logs.values())
        if severity:
            logs = [l for l in logs if l.severity.value == severity]
        return logs[offset:offset + limit]

    async def count_logs(self) -> int:
        return len(self._logs)

    async def store_span(self, span: TraceSpan) -> None:
        self._spans[span.span_id] = span

    async def get_span(self, span_id: str) -> TraceSpan | None:
        return self._spans.get(span_id)

    async def list_spans(self, name: str | None = None, limit: int = 100, offset: int = 0) -> list[TraceSpan]:
        spans = list(self._spans.values())
        if name:
            spans = [s for s in spans if s.name == name]
        return spans[offset:offset + limit]

    async def count_spans(self) -> int:
        return len(self._spans)

    async def clear(self) -> int:
        count = len(self._alerts) + len(self._rules) + len(self._logs) + len(self._spans)
        self._alerts.clear()
        self._rules.clear()
        self._logs.clear()
        self._spans.clear()
        return count

    async def count_alerts(self) -> int:
        return len(self._alerts)

    async def count_rules(self) -> int:
        return len(self._rules)
