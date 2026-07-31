"""Continuous self-improvement engine for NOVA Command Center."""

from __future__ import annotations

from typing import Any

from .schemas import _uuid, _utcnow


_IMPROVEMENT_CATEGORIES: dict[str, dict[str, Any]] = {
    "performance": {
        "description": "System performance optimizations",
        "keywords": ["slow", "latency", "bottleneck", "optimize", "cache"],
    },
    "accuracy": {
        "description": "Analysis and decision accuracy improvements",
        "keywords": ["accuracy", "correct", "precise", "error", "wrong"],
    },
    "automation": {
        "description": "Increased automation and reduced manual intervention",
        "keywords": ["automate", "manual", "repetitive", "streamline"],
    },
    "coverage": {
        "description": "Improved task and objective coverage",
        "keywords": ["coverage", "gap", "missing", "incomplete", "coverage"],
    },
    "robustness": {
        "description": "System reliability and error handling improvements",
        "keywords": ["error", "failure", "crash", "resilient", "robust"],
    },
    "knowledge": {
        "description": "Knowledge base and learning improvements",
        "keywords": ["learn", "knowledge", "pattern", "insight", "history"],
    },
}


class SelfImprovementEngine:
    def __init__(self) -> None:
        self._improvements: dict[str, dict] = {}
        self._patterns: list[dict] = []
        self._metrics_history: list[dict] = []
        self._enabled: bool = True

    def record_metric(self, name: str, value: float, context: dict | None = None) -> dict:
        entry = {
            "id": _uuid(),
            "name": name,
            "value": value,
            "context": context or {},
            "timestamp": _utcnow(),
        }
        self._metrics_history.append(entry)
        if len(self._metrics_history) > 1000:
            self._metrics_history = self._metrics_history[-500:]
        return entry

    def detect_patterns(self) -> list[dict]:
        if len(self._metrics_history) < 5:
            return []
        new_patterns: list[dict] = []
        by_name: dict[str, list[float]] = {}
        for entry in self._metrics_history:
            by_name.setdefault(entry["name"], []).append(entry["value"])
        for name, values in by_name.items():
            if len(values) >= 3:
                avg = sum(values) / len(values)
                recent = values[-3:]
                recent_avg = sum(recent) / len(recent)
                trend = "improving" if recent_avg > avg * 1.1 else (
                    "degrading" if recent_avg < avg * 0.9 else "stable"
                )
                pattern = {
                    "id": _uuid(),
                    "metric_name": name,
                    "trend": trend,
                    "overall_avg": round(avg, 4),
                    "recent_avg": round(recent_avg, 4),
                    "sample_count": len(values),
                    "detected_at": _utcnow(),
                }
                new_patterns.append(pattern)
                self._patterns.append(pattern)
        return new_patterns

    def suggest_improvements(self) -> list[dict]:
        suggestions: list[dict] = []
        for pattern in self._patterns[-10:]:
            if pattern["trend"] == "degrading":
                cat = self._categorize_improvement(pattern["metric_name"])
                suggestions.append({
                    "id": _uuid(),
                    "category": cat,
                    "title": f"Address degrading {pattern['metric_name']}",
                    "description": (
                        f"Metric '{pattern['metric_name']}' trending downward "
                        f"(recent avg: {pattern['recent_avg']:.4f} vs overall: {pattern['overall_avg']:.4f})"
                    ),
                    "priority": "high",
                    "status": "pending",
                    "pattern_id": pattern["id"],
                    "created_at": _utcnow(),
                })
        return suggestions

    def record_improvement(
        self,
        category: str,
        title: str,
        description: str,
        result: dict | None = None,
    ) -> dict:
        improvement = {
            "id": _uuid(),
            "category": category,
            "title": title,
            "description": description,
            "result": result or {},
            "status": "implemented",
            "timestamp": _utcnow(),
        }
        self._improvements[improvement["id"]] = improvement
        return improvement

    def get_metrics_summary(self) -> dict:
        if not self._metrics_history:
            return {"total_entries": 0, "metrics": {}}
        by_name: dict[str, list[float]] = {}
        for entry in self._metrics_history:
            by_name.setdefault(entry["name"], []).append(entry["value"])
        metrics: dict[str, dict] = {}
        for name, values in by_name.items():
            metrics[name] = {
                "count": len(values),
                "avg": round(sum(values) / len(values), 4),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "latest": values[-1],
            }
        return {"total_entries": len(self._metrics_history), "metrics": metrics}

    def get_improvements(self, category: str | None = None) -> list[dict]:
        items = list(self._improvements.values())
        if category:
            items = [i for i in items if i["category"] == category]
        return items

    def get_patterns(self, trend: str | None = None) -> list[dict]:
        patterns = list(self._patterns)
        if trend:
            patterns = [p for p in patterns if p["trend"] == trend]
        return patterns

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def is_enabled(self) -> bool:
        return self._enabled

    def _categorize_improvement(self, metric_name: str) -> str:
        name_lower = metric_name.lower()
        for cat, info in _IMPROVEMENT_CATEGORIES.items():
            if any(kw in name_lower for kw in info["keywords"]):
                return cat
        return "general"

    def to_dict(self) -> dict:
        return {
            "enabled": self._enabled,
            "total_improvements": len(self._improvements),
            "total_patterns": len(self._patterns),
            "total_metrics": len(self._metrics_history),
            "categories": list(_IMPROVEMENT_CATEGORIES.keys()),
        }
