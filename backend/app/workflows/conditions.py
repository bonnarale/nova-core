"""Condition evaluation for workflow branching logic."""

from __future__ import annotations

import operator
from typing import Any

from app.workflows.base import ConditionEvaluator


class DefaultConditionEvaluator(ConditionEvaluator):
    """Evaluates conditions using operator-based comparisons."""

    _OPERATORS = {
        "eq": operator.eq,
        "ne": operator.ne,
        "gt": operator.gt,
        "gte": operator.ge,
        "lt": operator.lt,
        "lte": operator.le,
        "in": lambda a, b: a in b,
        "not_in": lambda a, b: a not in b,
        "contains": lambda a, b: b in a if isinstance(a, (str, list)) else False,
        "regex": lambda a, b: __import__("re").search(str(b), str(a)) is not None,
        "exists": lambda a, _: a is not None,
        "not_exists": lambda a, _: a is None,
        "truthy": lambda a, _: bool(a),
        "falsy": lambda a, _: not bool(a),
    }

    async def evaluate(self, condition: dict, context: dict) -> bool:
        field = condition.get("field", "")
        op_name = condition.get("operator", "eq")
        value = condition.get("value")

        actual = self._resolve_field(field, context)
        op_func = self._OPERATORS.get(op_name)

        if op_func is None:
            raise ValueError(f"Unknown operator: {op_name}")

        try:
            return bool(op_func(actual, value))
        except Exception:
            return False

    def _resolve_field(self, field: str, context: dict) -> Any:
        parts = field.split(".")
        current = context
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, (list, tuple)):
                try:
                    idx = int(part)
                    current = current[idx] if 0 <= idx < len(current) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current
