"""Documentation endpoints for the API Platform."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from app.api.openapi import DefaultOpenAPIProvider
from app.api.registry import DefaultAPIRegistry

logger = logging.getLogger(__name__)


class APIDocumentation:
    """Provides Swagger, ReDoc, OpenAPI JSON, and endpoint catalog."""

    def __init__(self, registry: DefaultAPIRegistry | None = None) -> None:
        self._registry = registry or DefaultAPIRegistry()
        self._openapi_provider = DefaultOpenAPIProvider(self._registry)
        self.router = APIRouter(tags=["documentation"])
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.get("/api/docs/catalog", summary="Endpoint catalog")
        async def endpoint_catalog() -> dict[str, Any]:
            endpoints = self._registry.get_endpoints()
            tags = self._registry.get_tags()
            return {
                "success": True,
                "data": {
                    "total_endpoints": len(endpoints),
                    "tags": tags,
                    "endpoints": endpoints,
                },
            }

        @self.router.get("/api/docs/openapi-spec", summary="OpenAPI JSON spec")
        async def openapi_spec() -> dict[str, Any]:
            return self._openapi_provider.get_schema()

        @self.router.get("/api/docs/info", summary="API documentation info")
        async def docs_info() -> dict[str, Any]:
            return {
                "success": True,
                "data": {
                    "openapi_url": "/openapi.json",
                    "swagger_url": "/docs",
                    "redoc_url": "/redoc",
                    "catalog_url": "/api/docs/catalog",
                    "spec_url": "/api/docs/openapi-spec",
                    "info": self._openapi_provider.get_info(),
                },
            }

        @self.router.get("/api/docs/endpoints-by-tag/{tag}", summary="Endpoints by tag")
        async def endpoints_by_tag(tag: str) -> dict[str, Any]:
            endpoints = self._registry.list_by_tag(tag)
            return {
                "success": True,
                "data": {"tag": tag, "endpoints": endpoints},
            }

    def get_router(self) -> APIRouter:
        return self.router
