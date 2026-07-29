from __future__ import annotations

from .schemas import Recommendation


class RecommendationEngine:
    def __init__(self) -> None:
        self.recommendations: dict[str, Recommendation] = {}

    def create(
        self,
        category: str,
        title: str,
        description: str,
        priority: str = "medium",
        impact: str = "",
        effort: str = "",
    ) -> Recommendation:
        rec = Recommendation(
            category=category,
            title=title,
            description=description,
            priority=priority,
            impact=impact,
            effort=effort,
        )
        self.recommendations[rec.id] = rec
        return rec

    def get(self, rec_id: str) -> Recommendation | None:
        return self.recommendations.get(rec_id)

    def list_all(
        self, status: str | None = None, category: str | None = None
    ) -> list[Recommendation]:
        items = list(self.recommendations.values())
        if status is not None:
            items = [r for r in items if r.status == status]
        if category is not None:
            items = [r for r in items if r.category == category]
        return items

    def accept(self, rec_id: str) -> Recommendation | None:
        rec = self.recommendations.get(rec_id)
        if rec is None:
            return None
        rec.status = "accepted"
        return rec

    def reject(self, rec_id: str) -> Recommendation | None:
        rec = self.recommendations.get(rec_id)
        if rec is None:
            return None
        rec.status = "rejected"
        return rec

    def implement(self, rec_id: str) -> Recommendation | None:
        rec = self.recommendations.get(rec_id)
        if rec is None:
            return None
        rec.status = "implemented"
        return rec

    def get_pending(self) -> list[Recommendation]:
        return [r for r in self.recommendations.values() if r.status == "pending"]

    def to_dict(self) -> dict:
        return {k: v.__dict__ for k, v in self.recommendations.items()}
