"""Permission system for Tool Runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class PermissionLevel(IntEnum):
    """Granularity of tool access. Higher values = more access."""

    NONE = 0
    READ = 1
    WRITE = 2
    ADMIN = 3


@dataclass
class ToolPermission:
    """Permission rule for a specific tool."""

    tool_name: str
    level: PermissionLevel = PermissionLevel.READ
    allowed_agents: list[str] = field(default_factory=lambda: ["*"])
    allowed_users: list[str] = field(default_factory=lambda: ["*"])
    allowed_roles: list[str] = field(default_factory=list)
    denied_agents: list[str] = field(default_factory=list)
    denied_users: list[str] = field(default_factory=list)

    def allows(
        self,
        agent_id: str = "",
        user_id: str = "",
        roles: list[str] | None = None,
        required_level: PermissionLevel = PermissionLevel.READ,
    ) -> bool:
        if self.level == PermissionLevel.NONE:
            return False
        if self.level.value < required_level.value:
            return False

        if agent_id and agent_id in self.denied_agents:
            return False
        if user_id and user_id in self.denied_users:
            return False

        if self.allowed_roles:
            if not roles or not any(r in self.allowed_roles for r in roles):
                return False

        if "*" in self.allowed_agents and "*" in self.allowed_users:
            return True
        if user_id and user_id in self.allowed_users:
            return True
        if agent_id and agent_id in self.allowed_agents:
            return True

        if "*" in self.allowed_agents and not user_id:
            return True

        return False


class PermissionChecker:
    """Checks whether an agent is allowed to invoke a tool."""

    def __init__(self, rules: dict[str, ToolPermission] | None = None) -> None:
        self._rules: dict[str, ToolPermission] = {}
        if rules:
            for name, rule in rules.items():
                self._rules[name] = rule

    def register(self, permission: ToolPermission) -> None:
        self._rules[permission.tool_name] = permission

    def unregister(self, tool_name: str) -> None:
        self._rules.pop(tool_name, None)

    def get_permission(self, tool_name: str) -> ToolPermission | None:
        return self._rules.get(tool_name)

    def check(
        self,
        tool_name: str,
        agent_id: str = "",
        user_id: str = "",
        roles: list[str] | None = None,
        required_level: PermissionLevel = PermissionLevel.READ,
    ) -> bool:
        rule = self._rules.get(tool_name)
        if rule is None:
            return True
        return rule.allows(
            agent_id=agent_id,
            user_id=user_id,
            roles=roles,
            required_level=required_level,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            name: {
                "tool_name": rule.tool_name,
                "level": rule.level.value,
                "allowed_agents": list(rule.allowed_agents),
                "allowed_users": list(rule.allowed_users),
                "allowed_roles": list(rule.allowed_roles),
                "denied_agents": list(rule.denied_agents),
                "denied_users": list(rule.denied_users),
            }
            for name, rule in self._rules.items()
        }
