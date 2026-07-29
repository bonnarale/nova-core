from __future__ import annotations


class AutonomyEngine:
    def __init__(self) -> None:
        self._level: float = 0.5
        self._action_risks: dict[str, str] = {
            "read": "low",
            "analyze": "low",
            "recommend": "low",
            "execute_task": "medium",
            "modify_code": "high",
            "system_modification": "critical",
            "self_improve": "high",
            "delegate": "medium",
            "research": "low",
            "create_project": "medium",
        }

    def set_level(self, level: float) -> None:
        self._level = max(0.0, min(1.0, level))

    def get_level(self) -> float:
        return self._level

    def can_autonomously(self, action_type: str) -> bool:
        risk = self._action_risks.get(action_type, "medium")
        thresholds: dict[str, float] = {
            "low": 0.2,
            "medium": 0.5,
            "high": 0.8,
            "critical": 1.0,
        }
        return self._level >= thresholds.get(risk, 0.5)

    def requires_approval(self, action_type: str) -> bool:
        return not self.can_autonomously(action_type)

    def get_capabilities(self) -> list[str]:
        caps: list[str] = []
        if self._level >= 0.1:
            caps.extend(["read", "analyze", "research"])
        if self._level >= 0.3:
            caps.extend(["recommend"])
        if self._level >= 0.5:
            caps.extend(["execute_task", "delegate", "create_project"])
        if self._level >= 0.8:
            caps.extend(["modify_code", "self_improve"])
        if self._level >= 1.0:
            caps.extend(["system_modification"])
        return caps

    def evaluate_action(self, action_type: str, risk_level: str) -> dict:
        allowed = self.can_autonomously(action_type)
        approval_needed = self.requires_approval(action_type)
        return {
            "allowed": allowed,
            "requires_approval": approval_needed,
            "reason": f"Action '{action_type}' with risk '{risk_level}' "
            + ("is within autonomy bounds" if allowed else "exceeds autonomy bounds"),
        }

    def to_dict(self) -> dict:
        return {
            "level": self._level,
            "capabilities": self.get_capabilities(),
            "action_risks": dict(self._action_risks),
        }
