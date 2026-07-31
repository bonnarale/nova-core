from __future__ import annotations

import statistics


class MetricsCollector:
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.gauges: dict[str, float] = {}
        self.histograms: dict[str, list[float]] = {}

    def increment(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value

    def decrement(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) - value

    def set_gauge(self, name: str, value: float) -> None:
        self.gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        self.histograms.setdefault(name, []).append(value)

    def get_counter(self, name: str) -> int:
        return self.counters.get(name, 0)

    def get_gauge(self, name: str) -> float | None:
        return self.gauges.get(name)

    def get_histogram(self, name: str) -> dict:
        values = self.histograms.get(name, [])
        if not values:
            return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": statistics.mean(values),
            "min": min(values),
            "max": max(values),
        }

    def snapshot(self) -> dict:
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {
                name: self.get_histogram(name) for name in self.histograms
            },
        }

    def reset(self) -> None:
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()

    def to_dict(self) -> dict:
        return self.snapshot()
