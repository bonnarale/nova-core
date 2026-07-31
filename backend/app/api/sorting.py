"""Multi-field sorting utilities for the API Platform."""

from __future__ import annotations

from typing import Any

from app.api.enums import SortDirection
from app.api.models import SortParams


class SortingHandler:
    """Handles multi-field sorting with configurable defaults."""

    def __init__(self, default_sort_field: str = "created_at", default_direction: str = SortDirection.DESC.value) -> None:
        self.default_sort_field = default_sort_field
        self.default_direction = default_direction

    def parse_sort(self, raw: str | list[str] | None) -> list[SortParams]:
        if not raw:
            return [SortParams(field=self.default_sort_field, direction=self.default_direction)]
        parts: list[str] = []
        if isinstance(raw, str):
            parts = [p.strip() for p in raw.split(",") if p.strip()]
        elif isinstance(raw, list):
            parts = raw
        result: list[SortParams] = []
        for p in parts:
            if p.startswith("-"):
                result.append(SortParams(field=p[1:], direction=SortDirection.DESC.value))
            elif p.startswith("+"):
                result.append(SortParams(field=p[1:], direction=SortDirection.ASC.value))
            else:
                result.append(SortParams(field=p, direction=SortDirection.ASC.value))
        return result or [SortParams(field=self.default_sort_field, direction=self.default_direction)]

    def sort(self, items: list[Any], sort_params: list[SortParams]) -> list[Any]:
        if not sort_params or not items:
            return list(items)
        result = list(items)
        for sp in reversed(sort_params):
            reverse = sp.direction == SortDirection.DESC.value
            result.sort(key=lambda x: self._get_sort_key(x, sp.field), reverse=reverse)
        return result

    def _get_sort_key(self, item: Any, field: str) -> Any:
        if isinstance(item, dict):
            val = item.get(field, "")
        elif hasattr(item, field):
            val = getattr(item, field, "")
        else:
            val = ""
        if val is None:
            return ""
        return val
