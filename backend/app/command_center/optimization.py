from __future__ import annotations

from .schemas import Optimization


class OptimizationEngine:
    def __init__(self) -> None:
        self.optimizations: dict[str, Optimization] = {}

    def analyze(
        self,
        category: str,
        current_state: str,
        proposed_state: str,
        improvement: str,
        priority: int = 3,
        estimated_impact: str = "",
    ) -> Optimization:
        opt = Optimization(
            category=category,
            current_state=current_state,
            proposed_state=proposed_state,
            improvement=improvement,
            priority=priority,
            estimated_impact=estimated_impact,
        )
        self.optimizations[opt.id] = opt
        return opt

    def get(self, opt_id: str) -> Optimization | None:
        return self.optimizations.get(opt_id)

    def list_all(self, category: str | None = None) -> list[Optimization]:
        items = list(self.optimizations.values())
        if category is not None:
            items = [o for o in items if o.category == category]
        return items

    def prioritize(self) -> list[Optimization]:
        return sorted(
            self.optimizations.values(), key=lambda o: o.priority, reverse=True
        )

    def approve(self, opt_id: str) -> Optimization | None:
        opt = self.optimizations.get(opt_id)
        if opt is None:
            return None
        opt.status = "approved"
        return opt

    def implement(self, opt_id: str) -> Optimization | None:
        opt = self.optimizations.get(opt_id)
        if opt is None:
            return None
        opt.status = "implemented"
        return opt

    def to_dict(self) -> dict:
        return {k: v.__dict__ for k, v in self.optimizations.items()}
