"""Unified response formatting for the API Platform."""

from __future__ import annotations

import time
import uuid
from typing import Any

from app.api.base import ResponseFormatter
from app.api.enums import ErrorCode
from app.api.models import APIResponse, PaginatedResponse


class StandardResponseFormatter(ResponseFormatter):
    """Formats all API responses into a consistent structure."""

    def success(
        self,
        data: Any = None,
        metadata: dict[str, Any] | None = None,
        request_id: str = "",
    ) -> dict[str, Any]:
        resp = APIResponse(
            success=True,
            data=data,
            metadata=metadata or {},
            request_id=request_id or str(uuid.uuid4()),
        )
        return resp.to_dict()

    def error(
        self,
        code: ErrorCode,
        message: str,
        details: list[dict[str, Any]] | None = None,
        request_id: str = "",
    ) -> dict[str, Any]:
        errors: list[dict[str, Any]] = []
        if details:
            errors.extend(details)
        else:
            errors.append({"code": code.value, "message": message})
        resp = APIResponse(
            success=False,
            errors=errors,
            request_id=request_id or str(uuid.uuid4()),
        )
        return resp.to_dict()

    def paginated(
        self,
        data: list[Any],
        total: int,
        page: int = 1,
        page_size: int = 20,
        request_id: str = "",
    ) -> dict[str, Any]:
        total_pages = max(1, (total + page_size - 1) // page_size) if page_size > 0 else 1
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        }
        resp = PaginatedResponse(
            data=data,
            pagination=pagination,
            request_id=request_id or str(uuid.uuid4()),
        )
        return resp.to_dict()

    def cursor_paginated(
        self,
        data: list[Any],
        next_cursor: str = "",
        has_more: bool = False,
        request_id: str = "",
    ) -> dict[str, Any]:
        pagination: dict[str, Any] = {
            "next_cursor": next_cursor,
            "has_more": has_more,
        }
        resp = PaginatedResponse(
            data=data,
            pagination=pagination,
            request_id=request_id or str(uuid.uuid4()),
        )
        return resp.to_dict()

    def offset_paginated(
        self,
        data: list[Any],
        total: int,
        offset: int = 0,
        limit: int = 20,
        request_id: str = "",
    ) -> dict[str, Any]:
        pagination = {
            "offset": offset,
            "limit": limit,
            "total_items": total,
            "has_next": offset + limit < total,
            "has_previous": offset > 0,
        }
        resp = PaginatedResponse(
            data=data,
            pagination=pagination,
            request_id=request_id or str(uuid.uuid4()),
        )
        return resp.to_dict()

    def timestamp(self) -> float:
        return time.time()
