"""Observability alerts — threshold and condition-based alerting."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from app.observability.models import Alert, AlertRule, AlertSeverity, AlertState


class AlertManager:
    """Alert manager — create rules, evaluate conditions, fire/resolve alerts."""

    def __init__(self) -> None:
        self._rules: dict[str, AlertRule] = {}
        self._alerts: dict[str, Alert] = {}
        self._last_fired: dict[str, float] = {}

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    @property
    def alert_count(self) -> int:
        return len(self._alerts)

    def create_rule(
        self,
        rule_id: str | None = None,
        name: str = "",
        metric_name: str = "",
        condition: str = "gt",
        threshold: float = 0.0,
        severity: str = "warning",
        cooldown_seconds: float = 60.0,
        enabled: bool = True,
        labels: dict[str, str] | None = None,
    ) -> AlertRule:
        rule = AlertRule(
            rule_id=rule_id or str(uuid4()),
            name=name,
            metric_name=metric_name,
            condition=condition,
            threshold=threshold,
            severity=AlertSeverity(severity) if severity in [s.value for s in AlertSeverity] else AlertSeverity.WARNING,
            cooldown_seconds=cooldown_seconds,
            enabled=enabled,
            labels=labels or {},
        )
        self._rules[rule.rule_id] = rule
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        return self._rules.pop(rule_id, None) is not None

    def get_rule(self, rule_id: str) -> AlertRule | None:
        return self._rules.get(rule_id)

    def list_rules(self) -> list[AlertRule]:
        return list(self._rules.values())

    def evaluate(self, metric_name: str, value: float) -> Alert | None:
        now = time.time()
        for rule in self._rules.values():
            if not rule.enabled or rule.metric_name != metric_name:
                continue
            last_fired = self._last_fired.get(rule.rule_id, 0.0)
            if now - last_fired < rule.cooldown_seconds:
                continue
            triggered = False
            if rule.condition == "gt" and value > rule.threshold:
                triggered = True
            elif rule.condition == "gte" and value >= rule.threshold:
                triggered = True
            elif rule.condition == "lt" and value < rule.threshold:
                triggered = True
            elif rule.condition == "lte" and value <= rule.threshold:
                triggered = True
            elif rule.condition == "eq" and value == rule.threshold:
                triggered = True
            elif rule.condition == "neq" and value != rule.threshold:
                triggered = True
            if triggered:
                alert = Alert(
                    alert_id=str(uuid4()),
                    rule_id=rule.rule_id,
                    name=rule.name,
                    severity=rule.severity,
                    state=AlertState.FIRING,
                    message=f"Alert '{rule.name}' triggered: {metric_name}={value} ({rule.condition} {rule.threshold})",
                    value=value,
                    timestamp=now,
                    labels=dict(rule.labels),
                )
                self._alerts[alert.alert_id] = alert
                self._last_fired[rule.rule_id] = now
                return alert
        return None

    def resolve_alert(self, alert_id: str) -> bool:
        alert = self._alerts.get(alert_id)
        if alert is None:
            return False
        alert.state = AlertState.RESOLVED
        alert.resolved_at = time.time()
        return True

    def get_alerts(self, state: str | None = None) -> list[Alert]:
        alerts = list(self._alerts.values())
        if state:
            alerts = [a for a in alerts if a.state.value == state]
        return alerts

    def get_firing_alerts(self) -> list[Alert]:
        return self.get_alerts("firing")

    def clear(self) -> int:
        count = len(self._alerts)
        self._alerts.clear()
        self._last_fired.clear()
        return count

    def to_dict(self) -> dict[str, Any]:
        return {
            "rules": [r.to_dict() for r in self._rules.values()],
            "alerts": [a.to_dict() for a in self._alerts.values()],
            "rule_count": len(self._rules),
            "alert_count": len(self._alerts),
        }
