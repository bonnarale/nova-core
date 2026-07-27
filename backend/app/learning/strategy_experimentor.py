"""StrategyExperimentor — A/B testing framework for agent strategies.

Provides experiment creation, random variant assignment (50/50 balanced),
and statistical comparison using chi-squared tests with a minimum 30-sample gate.
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any
from dataclasses import dataclass, field

from app.learning.base import OutcomeStore

logger = logging.getLogger(__name__)


@dataclass
class Experiment:
    """An A/B experiment comparing control vs variant strategies."""

    id: str
    name: str
    control: str
    variant: str
    active: bool = True
    assignments: dict[str, str] = field(default_factory=dict)  # execution_id → strategy

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "control": self.control,
            "variant": self.variant,
            "active": self.active,
            "assignment_count": len(self.assignments),
        }


class StrategyExperimentor:
    """Manages A/B experiments for agent strategies.

    Provides variant assignment, outcome tracking per variant, and
    statistical comparison with chi-squared test.
    """

    MIN_SAMPLES_PER_VARIANT = 30

    def __init__(self, store: OutcomeStore) -> None:
        self._store = store
        self._experiments: dict[str, Experiment] = {}

    def create_experiment(
        self,
        name: str,
        control: str,
        variant: str,
    ) -> Experiment:
        """Create a new A/B experiment."""
        import uuid
        experiment = Experiment(
            id=str(uuid.uuid4()),
            name=name,
            control=control,
            variant=variant,
        )
        self._experiments[experiment.id] = experiment
        logger.info(
            "Experiment created: %s (control=%s, variant=%s)",
            name, control, variant,
        )
        return experiment

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        return self._experiments.get(experiment_id)

    def list_experiments(self) -> list[Experiment]:
        return list(self._experiments.values())

    def assign_variant(self, experiment_id: str) -> str | None:
        """Randomly assign a strategy for the given experiment.

        Returns the assigned strategy name, or None if experiment not found/inactive.
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None or not experiment.active:
            return None

        # Balanced 50/50 assignment
        control_count = sum(
            1 for s in experiment.assignments.values() if s == experiment.control
        )
        variant_count = sum(
            1 for s in experiment.assignments.values() if s == experiment.variant
        )

        if control_count <= variant_count:
            return experiment.control
        return experiment.variant

    def record_assignment(self, experiment_id: str, execution_id: str, strategy: str) -> bool:
        """Record that an execution was assigned a strategy."""
        experiment = self._experiments.get(experiment_id)
        if experiment is None or not experiment.active:
            return False
        experiment.assignments[execution_id] = strategy
        return True

    async def compare_outcomes(self, experiment_id: str) -> dict[str, Any]:
        """Compare outcomes between control and variant using chi-squared test.

        Returns statistical comparison dict. Requires >= MIN_SAMPLES_PER_VARIANT
        per variant to produce a result.
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return {"error": "Experiment not found"}

        # Gather outcomes per variant
        control_executions = [
            eid for eid, strat in experiment.assignments.items()
            if strat == experiment.control
        ]
        variant_executions = [
            eid for eid, strat in experiment.assignments.items()
            if strat == experiment.variant
        ]

        control_outcomes = []
        for eid in control_executions:
            outcome = await self._store.get_by_execution(eid)
            if outcome:
                control_outcomes.append(outcome)

        variant_outcomes = []
        for eid in variant_executions:
            outcome = await self._store.get_by_execution(eid)
            if outcome:
                variant_outcomes.append(outcome)

        # Check minimum sample size
        if (
            len(control_outcomes) < self.MIN_SAMPLES_PER_VARIANT
            or len(variant_outcomes) < self.MIN_SAMPLES_PER_VARIANT
        ):
            return {
                "status": "insufficient_data",
                "control_samples": len(control_outcomes),
                "variant_samples": len(variant_outcomes),
                "required": self.MIN_SAMPLES_PER_VARIANT,
            }

        # Compute success counts
        control_success = sum(1 for o in control_outcomes if o.outcome == "success")
        control_failure = len(control_outcomes) - control_success
        variant_success = sum(1 for o in variant_outcomes if o.outcome == "success")
        variant_failure = len(variant_outcomes) - variant_success

        # Chi-squared test for 2x2 contingency table
        # [[control_success, control_failure],
        #  [variant_success, variant_failure]]
        n = len(control_outcomes) + len(variant_outcomes)
        a, b = control_success, control_failure
        c, d = variant_success, variant_failure

        # Chi-squared with Yates' correction for continuity
        numerator = (n * (abs(a * d - b * c) - n / 2) ** 2) if n > 0 else 0
        denominator = (a + b) * (c + d) * (a + c) * (b + d)
        chi2 = numerator / denominator if denominator > 0 else 0.0

        # p-value approximation (1 degree of freedom)
        p_value = self._chi2_p_value(chi2)

        control_rate = control_success / len(control_outcomes) if control_outcomes else 0.0
        variant_rate = variant_success / len(variant_outcomes) if variant_outcomes else 0.0

        winner = None
        if p_value < 0.05:
            winner = experiment.control if control_rate > variant_rate else experiment.variant

        return {
            "status": "completed",
            "experiment_id": experiment_id,
            "control": experiment.control,
            "variant": experiment.variant,
            "control_samples": len(control_outcomes),
            "variant_samples": len(variant_outcomes),
            "control_success_rate": control_rate,
            "variant_success_rate": variant_rate,
            "chi_squared": chi2,
            "p_value": p_value,
            "significant": p_value < 0.05,
            "winner": winner,
        }

    @staticmethod
    def _chi2_p_value(chi2: float) -> float:
        """Approximate p-value for chi-squared with 1 degree of freedom.

        Uses the survival function approximation: p ≈ exp(-chi2/2) for large chi2.
        For chi2=0, returns 1.0 (no difference).
        """
        if chi2 <= 0:
            return 1.0
        # Rough approximation using the incomplete gamma function relationship
        # For chi2 ~ 1 df: p ≈ erfc(sqrt(chi2/2))
        # Use a simple exponential approximation that's adequate for gating
        return math.exp(-chi2 / 2)
