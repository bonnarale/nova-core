"""Experiment system for A/B testing, canary releases, and experimental modules."""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.future.enums import ExperimentState, ExperimentType


@dataclass
class ExperimentVariant:
    name: str
    weight: float = 1.0
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "weight": self.weight, "config": self.config}


@dataclass
class ExperimentMetrics:
    impressions: int = 0
    conversions: int = 0
    conversion_rate: float = 0.0
    custom: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"impressions": self.impressions, "conversions": self.conversions,
                "conversion_rate": self.conversion_rate, "custom": self.custom}


@dataclass
class Experiment:
    id: str
    name: str
    experiment_type: ExperimentType
    state: ExperimentState = ExperimentState.DRAFT
    variants: list[ExperimentVariant] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metrics: dict[str, ExperimentMetrics] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "experiment_type": self.experiment_type.value,
            "state": self.state.value, "variants": [v.to_dict() for v in self.variants],
            "config": self.config, "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "metadata": self.metadata,
        }


class ExperimentManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._experiments: dict[str, Experiment] = {}

    def create_experiment(self, name: str, experiment_type: str, config: dict[str, Any] | None = None) -> Experiment:
        import uuid
        exp_id = str(uuid.uuid4())
        exp = Experiment(
            id=exp_id, name=name,
            experiment_type=ExperimentType(experiment_type),
            config=config or {},
        )
        with self._lock:
            self._experiments[exp_id] = exp
        return exp

    def start_experiment(self, experiment_id: str) -> bool:
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if not exp or exp.state != ExperimentState.DRAFT:
                return False
            exp.state = ExperimentState.RUNNING
            exp.started_at = datetime.now(timezone.utc)
            return True

    def stop_experiment(self, experiment_id: str) -> bool:
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if not exp or exp.state != ExperimentState.RUNNING:
                return False
            exp.state = ExperimentState.COMPLETED
            exp.ended_at = datetime.now(timezone.utc)
            return True

    def pause_experiment(self, experiment_id: str) -> bool:
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if not exp or exp.state != ExperimentState.RUNNING:
                return False
            exp.state = ExperimentState.PAUSED
            return True

    def add_variant(self, experiment_id: str, variant: ExperimentVariant) -> bool:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        with self._lock:
            exp.variants.append(variant)
            exp.metrics[variant.name] = ExperimentMetrics()
        return True

    def get_variant(self, experiment_id: str, user_id: str | None = None) -> str | None:
        exp = self._experiments.get(experiment_id)
        if not exp or not exp.variants or exp.state != ExperimentState.RUNNING:
            return None
        total_weight = sum(v.weight for v in exp.variants)
        if total_weight <= 0:
            return exp.variants[0].name
        hash_input = f"{experiment_id}:{user_id or 'anonymous'}"
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = (hash_val % 10000) / 100.0
        cumulative = 0.0
        for v in exp.variants:
            cumulative += (v.weight / total_weight) * 100
            if bucket < cumulative:
                return v.name
        return exp.variants[-1].name

    def record_impression(self, experiment_id: str, variant_name: str) -> bool:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        metrics = exp.metrics.get(variant_name)
        if not metrics:
            return False
        with self._lock:
            metrics.impressions += 1
            if metrics.impressions > 0:
                metrics.conversion_rate = metrics.conversions / metrics.impressions
        return True

    def record_conversion(self, experiment_id: str, variant_name: str) -> bool:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        metrics = exp.metrics.get(variant_name)
        if not metrics:
            return False
        with self._lock:
            metrics.conversions += 1
            if metrics.impressions > 0:
                metrics.conversion_rate = metrics.conversions / metrics.impressions
        return True

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        return self._experiments.get(experiment_id)

    def get_experiments(self) -> list[Experiment]:
        return list(self._experiments.values())

    def get_metrics(self, experiment_id: str) -> dict[str, Any]:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {}
        return {k: v.to_dict() for k, v in exp.metrics.items()}

    def delete_experiment(self, experiment_id: str) -> bool:
        with self._lock:
            return self._experiments.pop(experiment_id, None) is not None

    def summary(self) -> dict[str, Any]:
        states: dict[str, int] = {}
        for exp in self._experiments.values():
            states[exp.state.value] = states.get(exp.state.value, 0) + 1
        return {"total": len(self._experiments), "by_state": states}
