"""Domain models for the API Platform subsystem."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class APIResponse:
    """Unified API response structure."""

    success: bool = True
    data: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    request_id: str = ""
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "success": self.success,
            "data": self.data,
            "metadata": self.metadata,
            "errors": self.errors,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
        }
        return result


@dataclass
class PaginatedResponse:
    """Paginated API response structure."""

    success: bool = True
    data: list[Any] = field(default_factory=list)
    pagination: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    request_id: str = ""
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "pagination": self.pagination,
            "metadata": self.metadata,
            "errors": self.errors,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
        }


@dataclass
class ErrorDetail:
    """Detailed error information."""

    code: str = ""
    message: str = ""
    field: str = ""
    location: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
            "location": self.location,
        }


@dataclass
class PaginationParams:
    """Pagination parameters."""

    page: int = 1
    page_size: int = 20
    cursor: str = ""
    offset: int = 0
    limit: int = 20

    def to_dict(self) -> dict[str, Any]:
        return {
            "page": self.page,
            "page_size": self.page_size,
            "cursor": self.cursor,
            "offset": self.offset,
            "limit": self.limit,
        }


@dataclass
class FilterParams:
    """Filter parameters."""

    field: str = ""
    operator: str = "eq"
    value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
        }


@dataclass
class SortParams:
    """Sort parameters."""

    field: str = ""
    direction: str = "asc"

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "direction": self.direction,
        }


@dataclass
class EndpointInfo:
    """Information about a registered endpoint."""

    path: str = ""
    method: str = "GET"
    handler: Any = None
    tags: list[str] = field(default_factory=list)
    version: str = "v1"
    summary: str = ""
    description: str = ""
    deprecated: bool = False
    sunset_date: str = ""
    permission_level: str = ""
    rate_limit: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "method": self.method,
            "tags": list(self.tags),
            "version": self.version,
            "summary": self.summary,
            "description": self.description,
            "deprecated": self.deprecated,
            "sunset_date": self.sunset_date,
            "permission_level": self.permission_level,
            "rate_limit": self.rate_limit,
        }


@dataclass
class APIMetrics:
    """API metrics data."""

    total_requests: int = 0
    total_responses: int = 0
    total_errors: int = 0
    average_latency_ms: float = 0.0
    endpoint_usage: dict[str, int] = field(default_factory=dict)
    error_rate: float = 0.0
    throughput_per_second: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "total_responses": self.total_responses,
            "total_errors": self.total_errors,
            "average_latency_ms": self.average_latency_ms,
            "endpoint_usage": dict(self.endpoint_usage),
            "error_rate": self.error_rate,
            "throughput_per_second": self.throughput_per_second,
        }


@dataclass
class APIVersionInfo:
    """API version metadata."""

    version: str = ""
    status: str = "current"
    released_at: str = ""
    sunset_date: str = ""
    description: str = ""
    changelog_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "status": self.status,
            "released_at": self.released_at,
            "sunset_date": self.sunset_date,
            "description": self.description,
            "changelog_url": self.changelog_url,
        }


@dataclass
class APIStatistics:
    """Aggregate API statistics."""

    total_endpoints: int = 0
    endpoints_by_version: dict[str, int] = field(default_factory=dict)
    endpoints_by_tag: dict[str, int] = field(default_factory=dict)
    deprecated_endpoints: int = 0
    total_requests: int = 0
    average_latency_ms: float = 0.0
    error_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_endpoints": self.total_endpoints,
            "endpoints_by_version": dict(self.endpoints_by_version),
            "endpoints_by_tag": dict(self.endpoints_by_tag),
            "deprecated_endpoints": self.deprecated_endpoints,
            "total_requests": self.total_requests,
            "average_latency_ms": self.average_latency_ms,
            "error_rate": self.error_rate,
        }
