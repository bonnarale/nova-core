from __future__ import annotations

from .schemas import GovernorDecision


class DecisionEngine:
    def __init__(self) -> None:
        self.decisions: dict[str, GovernorDecision] = {}

    def make_decision(
        self,
        decision_type: str,
        description: str,
        context: dict | None = None,
        confidence: float = 0.8,
    ) -> GovernorDecision:
        reasoning = f"Decision on '{decision_type}' based on context: {context or {}}"
        decision = GovernorDecision(
            decision_type=decision_type,
            description=description,
            reasoning=reasoning,
            confidence=confidence,
            action_taken="pending",
            requires_approval=confidence < 0.7,
        )
        self.decisions[decision.id] = decision
        return decision

    def get_decision(self, decision_id: str) -> GovernorDecision | None:
        return self.decisions.get(decision_id)

    def list_decisions(
        self, decision_type: str | None = None, limit: int = 50
    ) -> list[GovernorDecision]:
        items = list(self.decisions.values())
        if decision_type is not None:
            items = [d for d in items if d.decision_type == decision_type]
        return items[:limit]

    def approve_decision(self, decision_id: str) -> GovernorDecision | None:
        decision = self.decisions.get(decision_id)
        if decision is None:
            return None
        decision.approved = True
        decision.action_taken = "approved"
        return decision

    def reject_decision(self, decision_id: str) -> GovernorDecision | None:
        decision = self.decisions.get(decision_id)
        if decision is None:
            return None
        decision.approved = False
        decision.action_taken = "rejected"
        return decision

    def to_dict(self) -> dict:
        return {k: v.__dict__ for k, v in self.decisions.items()}
