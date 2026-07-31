from __future__ import annotations


_CAPABILITY_TIERS: list[tuple[float, list[str]]] = [
    (0.2, ["read", "analyze"]),
    (0.4, ["research", "recommend"]),
    (0.6, ["create_project", "delegate"]),
    (0.8, ["execute_task", "modify_workflow"]),
    (1.0, ["self_improve", "modify_code"]),
]

_HIGH_RISK_ACTIONS: frozenset[str] = frozenset({
    "self_improve",
    "modify_code",
    "modify_workflow",
    "execute_task",
})

_APPROVAL_REQUIRED_ACTIONS: frozenset[str] = frozenset({
    "create_project",
    "delegate",
    "execute_task",
    "modify_workflow",
    "self_improve",
    "modify_code",
})


class AutonomyManager:
    def __init__(self) -> None:
        self.level: float = 0.5
        self.policies: dict[str, dict] = {}

    def set_level(self, level: float) -> None:
        self.level = max(0.0, min(1.0, level))

    def get_level(self) -> float:
        return self.level

    def get_capabilities(self) -> list[str]:
        caps: list[str] = []
        for threshold, tier_caps in _CAPABILITY_TIERS:
            if self.level <= threshold:
                caps.extend(tier_caps)
                break
        else:
            if self.level > 1.0:
                caps = [c for _, tier in _CAPABILITY_TIERS for c in tier]
        return caps

    def can_perform(self, action: str) -> bool:
        return action in self.get_capabilities()

    def requires_approval(self, action: str) -> bool:
        if action in _HIGH_RISK_ACTIONS and self.level >= 0.6:
            return True
        if action in _APPROVAL_REQUIRED_ACTIONS:
            if self.level < 0.4:
                return True
            if action in ("create_project", "delegate") and self.level < 0.6:
                return True
            if action in ("execute_task", "modify_workflow") and self.level < 0.8:
                return True
            return action in _HIGH_RISK_ACTIONS
        return False

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "capabilities": self.get_capabilities(),
            "policies": dict(self.policies),
        }
