"""Health checks for the Scaling subsystem."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.scaling.enums import ScalingState
from app.scaling.models import ScalingHealth

logger = logging.getLogger(__name__)


class ScalingHealthChecker:
    """Health checker for the scaling subsystem."""

    def __init__(self) -> None:
        self._last_check: float = 0.0
        self._checks: dict[str, bool] = {}

    async def check(
        self,
        workers_healthy: int = 0,
        workers_total: int = 0,
        queues_healthy: int = 0,
        queues_total: int = 0,
        cache_hit_ratio: float = 0.0,
        state: ScalingState = ScalingState.RUNNING,
    ) -> ScalingHealth:
        status = "healthy"
        if state == ScalingState.DEGRADED:
            status = "degraded"
        elif state in (ScalingState.FAILED, ScalingState.SHUTDOWN):
            status = "unhealthy"
        elif workers_total > 0 and workers_healthy / workers_total < 0.5:
            status = "degraded"

        self._last_check = time.time()
        return ScalingHealth(
            status=status,
            workers_healthy=workers_healthy,
            workers_total=workers_total,
            queues_healthy=queues_healthy,
            queues_total=queues_total,
            cache_hit_ratio=cache_hit_ratio,
            last_check=self._last_check,
        )

    def register_check(self, name: str, healthy: bool) -> None:
        self._checks[name] = healthy

    def remove_check(self, name: str) -> bool:
        if name in self._checks:
            del self._checks[name]
            return True
        return False

    def get_checks(self) -> dict[str, bool]:
        return dict(self._checks)
