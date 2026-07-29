"""Adaptation engine — manages and applies adaptive strategies."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.autonomy.enums import StrategyType


class AdaptationRecord:
    """Records a strategy adaptation."""

    __slots__ = ("strategy_type", "previous", "current", "reason", "timestamp")

    def __init__(self, strategy_type: StrategyType, previous: str, current: str, reason: str = "") -> None:
        self.strategy_type = strategy_type
        self.previous = previous
        self.current = current
        self.reason = reason
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_type": self.strategy_type.value,
            "previous": self.previous,
            "current": self.current,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


class AdaptationEngine:
    """Manages adaptive strategy transitions based on feedback."""

    def __init__(self) -> None:
        self._current_strategies: dict[str, str] = {st.value: "default" for st in StrategyType}
        self._history: list[AdaptationRecord] = []
        self._lock = threading.RLock()

    def get_strategy(self, strategy_type: str) -> str:
        with self._lock:
            return self._current_strategies.get(strategy_type, "default")

    def adapt(self, strategy_type: str, feedback: dict[str, Any]) -> str:
        with self._lock:
            previous = self._current_strategies.get(strategy_type, "default")
            performance = feedback.get("performance", 0.5)
            if performance < 0.3:
                new_strategy = "conservative"
            elif performance > 0.8:
                new_strategy = "aggressive"
            else:
                new_strategy = "balanced"
            if new_strategy == previous:
                new_strategy = previous
            self._current_strategies[strategy_type] = new_strategy
            if new_strategy != previous:
                record = AdaptationRecord(
                    strategy_type=StrategyType(strategy_type),
                    previous=previous,
                    current=new_strategy,
                    reason=f"performance={performance:.2f}",
                )
                self._history.append(record)
            return new_strategy

    def set_strategy(self, strategy_type: str, strategy: str) -> None:
        with self._lock:
            previous = self._current_strategies.get(strategy_type, "default")
            self._current_strategies[strategy_type] = strategy
            if strategy != previous:
                record = AdaptationRecord(
                    strategy_type=StrategyType(strategy_type),
                    previous=previous,
                    current=strategy,
                    reason="manual_override",
                )
                self._history.append(record)

    def get_all_strategies(self) -> dict[str, str]:
        with self._lock:
            return dict(self._current_strategies)

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._history[-limit:]]

    def reset(self) -> None:
        with self._lock:
            self._current_strategies = {st.value: "default" for st in StrategyType}
            self._history.clear()
