"""Generic filtering utilities for the API Platform."""

from __future__ import annotations

from typing import Any

from app.api.enums import FilterOperator
from app.api.models import FilterParams


class FilteringHandler:
    """Handles generic filtering across repositories."""

    def __init__(self) -> None:
        self._operators: dict[str, Any] = {
            FilterOperator.EQ.value: lambda v, t: v == t,
            FilterOperator.NEQ.value: lambda v, t: v != t,
            FilterOperator.GT.value: lambda v, t: v > t,
            FilterOperator.GTE.value: lambda v, t: v >= t,
            FilterOperator.LT.value: lambda v, t: v < t,
            FilterOperator.LTE.value: lambda v, t: v <= t,
            FilterOperator.CONTAINS.value: lambda v, t: t in v if isinstance(v, str) else False,
            FilterOperator.STARTS_WITH.value: lambda v, t: v.startswith(t) if isinstance(v, str) else False,
            FilterOperator.ENDS_WITH.value: lambda v, t: v.endswith(t) if isinstance(v, str) else False,
        }

    def parse_filters(self, raw: dict[str, Any]) -> list[FilterParams]:
        filters: list[FilterParams] = []
        for field_name, value in raw.items():
            if isinstance(value, dict):
                op = value.get("operator", FilterOperator.EQ.value)
                val = value.get("value", value)
            else:
                op = FilterOperator.EQ.value
                val = value
            filters.append(FilterParams(field=field_name, operator=op, value=val))
        return filters

    def apply(self, items: list[Any], filters: list[FilterParams]) -> list[Any]:
        result = list(items)
        for f in filters:
            op_fn = self._operators.get(f.operator)
            if op_fn is None:
                continue
            result = [
                item for item in result
                if self._match_field(item, f.field, op_fn, f.value)
            ]
        return result

    def _match_field(
        self,
        item: Any,
        field: str,
        op_fn: Any,
        target: Any,
    ) -> bool:
        if isinstance(item, dict):
            value = item.get(field)
        elif hasattr(item, field):
            value = getattr(item, field)
        else:
            return False
        try:
            return bool(op_fn(value, target))
        except (TypeError, ValueError, AttributeError):
            return False
