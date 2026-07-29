"""Workflow variables — global, local, context, and environment variable management."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VariableScope(str, Enum):
    GLOBAL = "global"
    LOCAL = "local"
    WORKFLOW = "workflow"
    EXECUTION = "execution"
    ENVIRONMENT = "environment"


@dataclass
class Variable:
    name: str = ""
    scope: VariableScope = VariableScope.LOCAL
    value: Any = None
    var_type: str = "any"
    description: str = ""
    required: bool = False
    default: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


class VariableStore:
    """Multi-scope variable store for workflow execution."""

    def __init__(self) -> None:
        self._global: dict[str, Any] = {}
        self._workflow: dict[str, Any] = {}
        self._execution: dict[str, Any] = {}
        self._local: dict[str, dict[str, Any]] = {}

    def set_global(self, name: str, value: Any) -> None:
        self._global[name] = value

    def get_global(self, name: str, default: Any = None) -> Any:
        return self._global.get(name, default)

    def set_workflow(self, name: str, value: Any) -> None:
        self._workflow[name] = value

    def get_workflow(self, name: str, default: Any = None) -> Any:
        return self._workflow.get(name, default)

    def set_execution(self, name: str, value: Any) -> None:
        self._execution[name] = value

    def get_execution(self, name: str, default: Any = None) -> Any:
        return self._execution.get(name, default)

    def set_local(self, scope_id: str, name: str, value: Any) -> None:
        self._local.setdefault(scope_id, {})[name] = value

    def get_local(self, scope_id: str, name: str, default: Any = None) -> Any:
        return self._local.get(scope_id, {}).get(name, default)

    def get(self, name: str, default: Any = None) -> Any:
        if name in self._execution:
            return self._execution[name]
        if name in self._workflow:
            return self._workflow[name]
        if name in self._global:
            return self._global[name]
        env_val = os.environ.get(name)
        if env_val is not None:
            return env_val
        return default

    def set(self, name: str, value: Any, scope: VariableScope = VariableScope.EXECUTION) -> None:
        if scope == VariableScope.GLOBAL:
            self._global[name] = value
        elif scope == VariableScope.WORKFLOW:
            self._workflow[name] = value
        elif scope == VariableScope.EXECUTION:
            self._execution[name] = value

    def resolve(self, mapping: dict[str, str], source: dict[str, Any] | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {}
        source = source or {}
        for target_key, source_key in mapping.items():
            if source_key in source:
                result[target_key] = source[source_key]
            else:
                result[target_key] = self.get(source_key)
        return result

    def get_all_global(self) -> dict[str, Any]:
        return dict(self._global)

    def get_all_workflow(self) -> dict[str, Any]:
        return dict(self._workflow)

    def get_all_execution(self) -> dict[str, Any]:
        return dict(self._execution)

    def clear_local(self, scope_id: str) -> None:
        self._local.pop(scope_id, None)

    def clear_all(self) -> None:
        self._global.clear()
        self._workflow.clear()
        self._execution.clear()
        self._local.clear()
