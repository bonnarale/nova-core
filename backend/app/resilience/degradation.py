"""Graceful degradation management."""

from __future__ import annotations

import threading
from typing import Any

from app.resilience.enums import DegradationLevel


class DegradationManager:
    """Graceful degradation when dependencies become unavailable."""

    def __init__(self) -> None:
        self._levels: dict[str, DegradationLevel] = {}
        self._features: dict[str, dict[str, bool]] = {}
        self._lock = threading.RLock()

    def set_level(self, subsystem: str, level: DegradationLevel) -> None:
        with self._lock:
            self._levels[subsystem] = level

    def get_level(self, subsystem: str) -> DegradationLevel:
        with self._lock:
            return self._levels.get(subsystem, DegradationLevel.NONE)

    def disable_feature(self, subsystem: str, feature: str) -> None:
        with self._lock:
            self._features.setdefault(subsystem, {})[feature] = False

    def enable_feature(self, subsystem: str, feature: str) -> None:
        with self._lock:
            self._features.setdefault(subsystem, {})[feature] = True

    def is_feature_enabled(self, subsystem: str, feature: str) -> bool:
        with self._lock:
            features = self._features.get(subsystem, {})
            return features.get(feature, True)

    def get_degraded_subsystems(self) -> list[str]:
        with self._lock:
            return [k for k, v in self._levels.items() if v != DegradationLevel.NONE]

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "levels": {k: v.value for k, v in self._levels.items()},
                "degraded_count": len([v for v in self._levels.values() if v != DegradationLevel.NONE]),
                "features": {k: dict(v) for k, v in self._features.items()},
            }
