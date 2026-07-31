"""Pydantic schemas for the API Platform."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PaginationQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    cursor: str = ""
    offset: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)


class FilterQuery(BaseModel):
    filters: dict[str, Any] = Field(default_factory=dict)


class SortQuery(BaseModel):
    sort: str = ""


class VersionNegotiation(BaseModel):
    accept: str = ""


class APIResponseSchema(BaseModel):
    success: bool
    data: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    request_id: str = ""
    timestamp: float = 0.0


class APIErrorResponse(BaseModel):
    success: bool = False
    data: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    request_id: str = ""


class EndpointRegistration(BaseModel):
    path: str
    method: str = "GET"
    tags: list[str] = Field(default_factory=list)
    version: str = "v1"
    summary: str = ""
    description: str = ""
    deprecated: bool = False


class VersionInfo(BaseModel):
    version: str
    status: str = "current"
    released_at: str = ""
    sunset_date: str = ""
    description: str = ""


class APIStatisticsResponse(BaseModel):
    total_endpoints: int = 0
    endpoints_by_version: dict[str, int] = Field(default_factory=dict)
    endpoints_by_tag: dict[str, int] = Field(default_factory=dict)
    deprecated_endpoints: int = 0
    total_requests: int = 0
    average_latency_ms: float = 0.0
    error_rate: float = 0.0


class APIMetricsResponse(BaseModel):
    total_requests: int = 0
    total_responses: int = 0
    total_errors: int = 0
    average_latency_ms: float = 0.0
    error_rate: float = 0.0
    throughput_per_second: float = 0.0
    endpoint_usage: dict[str, int] = Field(default_factory=dict)
