"""Strategy manager — manages available strategies per category."""

from __future__ import annotations

import threading
from typing import Any

from app.autonomy.enums import StrategyType


class StrategyEntry:
    """A registered strategy."""

    __slots__ = ("name", "strategy_type", "description", "parameters", "effectiveness")

    def __init__(
        self,
        name: str,
        strategy_type: StrategyType,
        description: str = "",
        parameters: dict[str, Any] | None = None,
        effectiveness: float = 0.5,
    ) -> None:
        self.name = name
        self.strategy_type = strategy_type
        self.description = description
        self.parameters = parameters or {}
        self.effectiveness = effectiveness

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "strategy_type": self.strategy_type.value,
            "description": self.description,
            "parameters": self.parameters,
            "effectiveness": self.effectiveness,
        }


class StrategyManager:
    """Manages available strategies and selects based on context."""

    def __init__(self) -> None:
        self._strategies: dict[str, list[StrategyEntry]] = {}
        self._lock = threading.RLock()
        self._setup_defaults()

    def _setup_defaults(self) -> None:
        for st in StrategyType:
            self._strategies[st.value] = [
                StrategyEntry(name="default", strategy_type=st, description="Default strategy"),
                StrategyEntry(name="conservative", strategy_type=st, description="Conservative approach", effectiveness=0.6),
                StrategyEntry(name="balanced", strategy_type=st, description="Balanced approach", effectiveness=0.7),
                StrategyEntry(name="aggressive", strategy_type=st, description="Aggressive optimization", effectiveness=0.8),
            ]

    def register(self, strategy: StrategyEntry) -> None:
        with self._lock:
            self._strategies.setdefault(strategy.strategy_type.value, []).append(strategy)

    def get_strategies(self, strategy_type: str) -> list[StrategyEntry]:
        with self._lock:
            return list(self._strategies.get(strategy_type, []))

    def select(self, strategy_type: str, context: dict[str, Any]) -> StrategyEntry:
        candidates = self.get_strategies(strategy_type)
        if not candidates:
            return StrategyEntry(name="default", strategy_type=StrategyType(strategy_type))
        risk_tolerance = context.get("risk_tolerance", 0.5)
        if risk_tolerance < 0.3:
            scored = sorted(candidates, key=lambda s: s.effectiveness if "conservative" in s.name else 0, reverse=True)
        elif risk_tolerance > 0.7:
            scored = sorted(candidates, key=lambda s: s.effectiveness if "aggressive" in s.name else 0, reverse=True)
        else:
            scored = sorted(candidates, key=lambda s: s.effectiveness, reverse=True)
        return scored[0]

    def get_all_types(self) -> list[str]:
        return [st.value for st in StrategyType]

    def count(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._strategies.values())
