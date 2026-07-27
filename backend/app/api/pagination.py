"""Pagination utilities for the API Platform."""

from __future__ import annotations

from typing import Any

from app.api.enums import PaginationStyle
from app.api.models import PaginationParams


class PaginationHandler:
    """Handles page-based, cursor-based, and offset-based pagination."""

    def __init__(
        self,
        default_page_size: int = 20,
        max_page_size: int = 100,
    ) -> None:
        self.default_page_size = default_page_size
        self.max_page_size = max_page_size

    def normalize(
        self,
        page: int = 1,
        page_size: int = 0,
        offset: int = 0,
        limit: int = 0,
        cursor: str = "",
    ) -> PaginationParams:
        if page < 1:
            page = 1
        ps = page_size if page_size > 0 else self.default_page_size
        if ps > self.max_page_size:
            ps = self.max_page_size
        off = max(0, offset)
        lim = limit if limit > 0 else self.default_page_size
        if lim > self.max_page_size:
            lim = self.max_page_size
        return PaginationParams(
            page=page, page_size=ps, cursor=cursor, offset=off, limit=lim,
        )

    def paginate_page(
        self,
        items: list[Any],
        total: int,
        page: int = 1,
        page_size: int = 0,
    ) -> dict[str, Any]:
        ps = page_size if page_size > 0 else self.default_page_size
        if ps > self.max_page_size:
            ps = self.max_page_size
        if page < 1:
            page = 1
        total_pages = max(1, (total + ps - 1) // ps)
        start = (page - 1) * ps
        end = start + ps
        page_items = items[start:end]
        return {
            "items": page_items,
            "pagination": {
                "page": page,
                "page_size": ps,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
        }

    def paginate_cursor(
        self,
        items: list[Any],
        cursor: str = "",
        limit: int = 0,
    ) -> dict[str, Any]:
        lim = limit if limit > 0 else self.default_page_size
        if lim > self.max_page_size:
            lim = self.max_page_size
        if cursor:
            start_idx = 0
            for i, item in enumerate(items):
                item_id = str(getattr(item, "id", i))
                if item_id == cursor:
                    start_idx = i + 1
                    break
        else:
            start_idx = 0
        page_items = items[start_idx : start_idx + lim]
        next_cursor = ""
        if start_idx + lim < len(items):
            next_item = items[start_idx + lim]
            next_cursor = str(getattr(next_item, "id", ""))
        return {
            "items": page_items,
            "pagination": {
                "next_cursor": next_cursor,
                "has_more": start_idx + lim < len(items),
            },
        }

    def paginate_offset(
        self,
        items: list[Any],
        total: int,
        offset: int = 0,
        limit: int = 0,
    ) -> dict[str, Any]:
        lim = limit if limit > 0 else self.default_page_size
        if lim > self.max_page_size:
            lim = self.max_page_size
        off = max(0, offset)
        page_items = items[off : off + lim]
        return {
            "items": page_items,
            "pagination": {
                "offset": off,
                "limit": lim,
                "total_items": total,
                "has_next": off + lim < total,
                "has_previous": off > 0,
            },
        }
