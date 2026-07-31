"""Standardized error handling for the API Platform."""

from __future__ import annotations

import uuid
from typing import Any

from app.api.base import ErrorHandler
from app.api.enums import ErrorCode
from app.api.models import ErrorDetail


class StandardErrorHandler(ErrorHandler):
    """Standardized API error responses."""

    def _make_error(
        self,
        code: ErrorCode,
        message: str,
        details: list[ErrorDetail] | None = None,
        request_id: str = "",
    ) -> dict[str, Any]:
        error_list: list[dict[str, Any]] = []
        if details:
            error_list = [d.to_dict() for d in details]
        else:
            error_list = [{"code": code.value, "message": message}]
        return {
            "success": False,
            "data": None,
            "metadata": {},
            "errors": error_list,
            "request_id": request_id or str(uuid.uuid4()),
        }

    def handle_validation(
        self,
        errors: list[dict[str, Any]],
        request_id: str = "",
    ) -> dict[str, Any]:
        details = [
            ErrorDetail(
                code=e.get("code", ErrorCode.VALIDATION_ERROR.value),
                message=e.get("message", "Validation error"),
                field=e.get("field", ""),
                location=e.get("location", "body"),
            )
            for e in errors
        ]
        return self._make_error(
            ErrorCode.VALIDATION_ERROR,
            "Validation failed",
            details=details,
            request_id=request_id,
        )

    def handle_not_found(
        self, resource: str, request_id: str = ""
    ) -> dict[str, Any]:
        return self._make_error(
            ErrorCode.RESOURCE_NOT_FOUND,
            f"{resource} not found",
            request_id=request_id,
        )

    def handle_unauthorized(
        self, message: str = "", request_id: str = ""
    ) -> dict[str, Any]:
        return self._make_error(
            ErrorCode.AUTHENTICATION_REQUIRED,
            message or "Authentication required",
            request_id=request_id,
        )

    def handle_forbidden(
        self, message: str = "", request_id: str = ""
    ) -> dict[str, Any]:
        return self._make_error(
            ErrorCode.AUTHORIZATION_DENIED,
            message or "Access denied",
            request_id=request_id,
        )

    def handle_conflict(
        self, message: str, request_id: str = ""
    ) -> dict[str, Any]:
        return self._make_error(
            ErrorCode.RESOURCE_CONFLICT,
            message,
            request_id=request_id,
        )

    def handle_rate_limit(
        self, retry_after: int = 60, request_id: str = ""
    ) -> dict[str, Any]:
        result = self._make_error(
            ErrorCode.RATE_LIMIT_EXCEEDED,
            f"Rate limit exceeded. Retry after {retry_after}s",
            request_id=request_id,
        )
        result["retry_after"] = retry_after
        return result

    def handle_internal(
        self, message: str = "", request_id: str = ""
    ) -> dict[str, Any]:
        return self._make_error(
            ErrorCode.INTERNAL_ERROR,
            message or "Internal server error",
            request_id=request_id,
        )

    def handle_timeout(self, request_id: str = "") -> dict[str, Any]:
        return self._make_error(
            ErrorCode.TIMEOUT,
            "Request timed out",
            request_id=request_id,
        )

    def handle_deprecated(
        self,
        message: str = "",
        sunset_date: str = "",
        request_id: str = "",
    ) -> dict[str, Any]:
        result = self._make_error(
            ErrorCode.DEPRECATED,
            message or "This API version is deprecated",
            request_id=request_id,
        )
        if sunset_date:
            result["sunset_date"] = sunset_date
        return result

    def handle_dependency_failure(
        self, dependency: str = "", request_id: str = ""
    ) -> dict[str, Any]:
        return self._make_error(
            ErrorCode.DEPENDENCY_FAILURE,
            f"Dependency failure: {dependency}" if dependency else "Dependency failure",
            request_id=request_id,
        )
