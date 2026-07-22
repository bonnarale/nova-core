"""RAG filters — metadata filtering for retrieved chunks."""

from __future__ import annotations

from typing import Any, Optional

from app.rag.schemas import FilterCondition, FilterOperator


def apply_filters(
    chunks_metadata: list[dict[str, Any]],
    filters: list[FilterCondition],
) -> list[int]:
    """Return indices of metadata dicts that match ALL filters."""
    matching: list[int] = []
    for i, meta in enumerate(chunks_metadata):
        if all(_evaluate(meta, fc) for fc in filters):
            matching.append(i)
    return matching


def _evaluate(meta: dict[str, Any], fc: FilterCondition) -> bool:
    val = meta.get(fc.field)
    if val is None and fc.operator not in (FilterOperator.NEQ, FilterOperator.NIN):
        return False
    op = fc.operator
    if op == FilterOperator.EQ:
        return val == fc.value
    if op == FilterOperator.NEQ:
        return val != fc.value
    if op == FilterOperator.IN:
        return val in fc.value if isinstance(fc.value, (list, set)) else False
    if op == FilterOperator.NIN:
        return val not in fc.value if isinstance(fc.value, (list, set)) else True
    if op == FilterOperator.GT:
        return val is not None and val > fc.value
    if op == FilterOperator.GTE:
        return val is not None and val >= fc.value
    if op == FilterOperator.LT:
        return val is not None and val < fc.value
    if op == FilterOperator.LTE:
        return val is not None and val <= fc.value
    if op == FilterOperator.CONTAINS:
        return fc.value in str(val) if val is not None else False
    if op == FilterOperator.STARTS_WITH:
        return str(val).startswith(str(fc.value)) if val is not None else False
    return True


def build_tag_filter(tags: list[str]) -> Optional[FilterCondition]:
    if not tags:
        return None
    return FilterCondition(field="tags", operator=FilterOperator.CONTAINS, value=tags[0])


def build_source_filter(sources: list[str]) -> Optional[FilterCondition]:
    if not sources:
        return None
    if len(sources) == 1:
        return FilterCondition(field="source", operator=FilterOperator.EQ, value=sources[0])
    return FilterCondition(field="source", operator=FilterOperator.IN, value=sources)


def build_category_filter(categories: list[str]) -> Optional[FilterCondition]:
    if not categories:
        return None
    if len(categories) == 1:
        return FilterCondition(field="category", operator=FilterOperator.EQ, value=categories[0])
    return FilterCondition(field="category", operator=FilterOperator.IN, value=categories)


def merge_filters(
    existing: list[FilterCondition],
    *extras: Optional[FilterCondition],
) -> list[FilterCondition]:
    result = list(existing)
    for f in extras:
        if f is not None:
            result.append(f)
    return result
