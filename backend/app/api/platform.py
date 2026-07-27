"""Top-level API Platform orchestrator."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.api.enums import LifecycleState
from app.api.errors import StandardErrorHandler
from app.api.filtering import FilteringHandler
from app.api.lifecycle import APILifecycle
from app.api.metrics import APIMetricsCollector
from app.api.models import APIStatistics
from app.api.pagination import PaginationHandler
from app.api.registry import DefaultAPIRegistry
from app.api.response import StandardResponseFormatter
from app.api.sorting import SortingHandler
from app.api.tracing import APITracer
from app.api.versioning import DefaultAPIVersionProvider

logger = logging.getLogger(__name__)


class APIPlatform:
    """Orchestrator for the API platform subsystem."""

    def __init__(self) -> None:
        self.registry = DefaultAPIRegistry()
        self.version_provider = DefaultAPIVersionProvider()
        self.response_formatter = StandardResponseFormatter()
        self.error_handler = StandardErrorHandler()
        self.pagination_handler = PaginationHandler()
        self.filtering_handler = FilteringHandler()
        self.sorting_handler = SortingHandler()
        self.lifecycle = APILifecycle()
        self.metrics = APIMetricsCollector()
        self.tracer = APITracer()
        self._start_time: float = 0.0

    async def start(self) -> None:
        self._start_time = time.time()
        self.lifecycle.transition(LifecycleState.INITIALIZED, "platform init")
        self.lifecycle.transition(LifecycleState.READY, "components ready")
        self.lifecycle.transition(LifecycleState.RUNNING, "accepting requests")
        logger.info("API Platform started")

    async def shutdown(self) -> None:
        self.lifecycle.transition(LifecycleState.SHUTDOWN, "shutdown")
        logger.info("API Platform shut down")

    def health(self) -> dict[str, Any]:
        ls = self.lifecycle.get_status()
        return {
            "status": "ok" if self.lifecycle.is_running() else "degraded",
            "lifecycle": ls,
            "endpoints": self.registry.count(),
            "versions": self.version_provider.get_supported_versions(),
        }

    def get_statistics(self) -> dict[str, Any]:
        reg_stats = self.registry.get_statistics()
        metrics = self.metrics.get_statistics()
        return {
            "endpoints": reg_stats,
            "metrics": metrics,
            "lifecycle": self.lifecycle.get_status(),
            "tracing": self.tracer.get_statistics(),
        }

    def format_success(self, data: Any = None, request_id: str = "") -> dict[str, Any]:
        return self.response_formatter.success(data=data, request_id=request_id)

    def format_error(self, code: Any, message: str, request_id: str = "") -> dict[str, Any]:
        return self.response_formatter.error(code=code, message=message, request_id=request_id)

    def format_paginated(self, data: list[Any], total: int, page: int = 1, page_size: int = 20, request_id: str = "") -> dict[str, Any]:
        return self.response_formatter.paginated(data=data, total=total, page=page, page_size=page_size, request_id=request_id)

    def paginate_page(self, items: list[Any], total: int, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        return self.pagination_handler.paginate_page(items=items, total=total, page=page, page_size=page_size)

    def paginate_offset(self, items: list[Any], total: int, offset: int = 0, limit: int = 20) -> dict[str, Any]:
        return self.pagination_handler.paginate_offset(items=items, total=total, offset=offset, limit=limit)

    def paginate_cursor(self, items: list[Any], cursor: str = "", limit: int = 20) -> dict[str, Any]:
        return self.pagination_handler.paginate_cursor(items=items, cursor=cursor, limit=limit)

    def filter_items(self, items: list[Any], raw_filters: dict[str, Any]) -> list[Any]:
        filters = self.filtering_handler.parse_filters(raw_filters)
        return self.filtering_handler.apply(items, filters)

    def sort_items(self, items: list[Any], sort_str: str = "") -> list[Any]:
        sort_params = self.sorting_handler.parse_sort(sort_str)
        return self.sorting_handler.sort(items, sort_params)

    def record_request(self, path: str = "", method: str = "GET") -> None:
        self.metrics.record_request(path, method)

    def record_response(self, path: str = "", status_code: int = 200) -> None:
        self.metrics.record_response(path, status_code)

    def record_latency(self, latency_ms: float) -> None:
        self.metrics.record_latency(latency_ms)
