from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .schemas import Recommendation


class RecommendationEngine:
    def __init__(self) -> None:
        self._recommendations: dict[str, Recommendation] = {}

    def generate_recommendation(
        self,
        category: str,
        title: str,
        description: str,
        priority: str = "medium",
        impact: str = "",
        effort: str = "",
    ) -> dict:
        rec = Recommendation(
            category=category,
            title=title,
            description=description,
            priority=priority,
            impact=impact,
            effort=effort,
        )
        self._recommendations[rec.id] = rec
        return {
            "id": rec.id,
            "category": rec.category,
            "title": rec.title,
            "description": rec.description,
            "priority": rec.priority,
            "status": rec.status,
            "impact": rec.impact,
            "effort": rec.effort,
            "created_at": rec.created_at,
        }

    def get_recommendation(self, rec_id: str) -> dict | None:
        rec = self._recommendations.get(rec_id)
        if rec is None:
            return None
        return {
            "id": rec.id,
            "category": rec.category,
            "title": rec.title,
            "description": rec.description,
            "priority": rec.priority,
            "status": rec.status,
            "impact": rec.impact,
            "effort": rec.effort,
            "created_at": rec.created_at,
        }

    def list_recommendations(
        self, status: str | None = None, category: str | None = None
    ) -> list[dict]:
        recs = list(self._recommendations.values())
        if status is not None:
            recs = [r for r in recs if r.status == status]
        if category is not None:
            recs = [r for r in recs if r.category == category]
        return [
            {
                "id": r.id,
                "category": r.category,
                "title": r.title,
                "description": r.description,
                "priority": r.priority,
                "status": r.status,
                "impact": r.impact,
                "effort": r.effort,
                "created_at": r.created_at,
            }
            for r in recs
        ]

    def accept_recommendation(self, rec_id: str) -> dict | None:
        rec = self._recommendations.get(rec_id)
        if rec is None or rec.status != "pending":
            return None
        rec.status = "accepted"
        return self.get_recommendation(rec_id)

    def reject_recommendation(self, rec_id: str) -> dict | None:
        rec = self._recommendations.get(rec_id)
        if rec is None or rec.status != "pending":
            return None
        rec.status = "rejected"
        return self.get_recommendation(rec_id)

    def implement_recommendation(self, rec_id: str) -> dict | None:
        rec = self._recommendations.get(rec_id)
        if rec is None or rec.status not in ("pending", "accepted"):
            return None
        rec.status = "implemented"
        return self.get_recommendation(rec_id)

    def get_pending(self) -> list[dict]:
        return self.list_recommendations(status="pending")

    def to_dict(self) -> dict:
        return {
            "recommendations": {
                k: {
                    "id": v.id,
                    "category": v.category,
                    "title": v.title,
                    "priority": v.priority,
                    "status": v.status,
                }
                for k, v in self._recommendations.items()
            }
        }
