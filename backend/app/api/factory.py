"""Factory for creating API platform components."""

from __future__ import annotations

import logging
from typing import Any

from app.api.docs import APIDocumentation
from app.api.errors import StandardErrorHandler
from app.api.filtering import FilteringHandler
from app.api.lifecycle import APILifecycle
from app.api.metrics import APIMetricsCollector
from app.api.openapi import DefaultOpenAPIProvider
from app.api.pagination import PaginationHandler
from app.api.registry import DefaultAPIRegistry
from app.api.response import StandardResponseFormatter
from app.api.sorting import SortingHandler
from app.api.tracing import APITracer
from app.api.versioning import DefaultAPIVersionProvider

logger = logging.getLogger(__name__)


class APIPlatformFactory:
    """Creates all API platform components."""

    @staticmethod
    def create_all() -> dict[str, Any]:
        registry = DefaultAPIRegistry()
        version_provider = DefaultAPIVersionProvider()
        response_formatter = StandardResponseFormatter()
        error_handler = StandardErrorHandler()
        pagination_handler = PaginationHandler()
        filtering_handler = FilteringHandler()
        sorting_handler = SortingHandler()
        lifecycle = APILifecycle()
        metrics = APIMetricsCollector()
        tracer = APITracer()
        openapi_provider = DefaultOpenAPIProvider(registry, version_provider)
        documentation = APIDocumentation(registry)

        return {
            "registry": registry,
            "version_provider": version_provider,
            "response_formatter": response_formatter,
            "error_handler": error_handler,
            "pagination_handler": pagination_handler,
            "filtering_handler": filtering_handler,
            "sorting_handler": sorting_handler,
            "lifecycle": lifecycle,
            "metrics": metrics,
            "tracer": tracer,
            "openapi_provider": openapi_provider,
            "documentation": documentation,
        }

    @staticmethod
    def create_registry() -> DefaultAPIRegistry:
        return DefaultAPIRegistry()

    @staticmethod
    def create_version_provider() -> DefaultAPIVersionProvider:
        return DefaultAPIVersionProvider()

    @staticmethod
    def create_response_formatter() -> StandardResponseFormatter:
        return StandardResponseFormatter()

    @staticmethod
    def create_error_handler() -> StandardErrorHandler:
        return StandardErrorHandler()

    @staticmethod
    def create_pagination_handler() -> PaginationHandler:
        return PaginationHandler()

    @staticmethod
    def create_filtering_handler() -> FilteringHandler:
        return FilteringHandler()

    @staticmethod
    def create_sorting_handler() -> SortingHandler:
        return SortingHandler()

    @staticmethod
    def create_lifecycle() -> APILifecycle:
        return APILifecycle()

    @staticmethod
    def create_metrics() -> APIMetricsCollector:
        return APIMetricsCollector()

    @staticmethod
    def create_tracer() -> APITracer:
        return APITracer()
