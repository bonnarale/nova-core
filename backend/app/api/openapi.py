"""OpenAPI schema generation for the API Platform."""

from __future__ import annotations

from typing import Any

from app.api.base import OpenAPIProvider
from app.api.registry import DefaultAPIRegistry
from app.api.versioning import DefaultAPIVersionProvider


class DefaultOpenAPIProvider(OpenAPIProvider):
    """Generates OpenAPI metadata from the endpoint registry."""

    def __init__(
        self,
        registry: DefaultAPIRegistry | None = None,
        version_provider: DefaultAPIVersionProvider | None = None,
    ) -> None:
        self._registry = registry or DefaultAPIRegistry()
        self._version_provider = version_provider or DefaultAPIVersionProvider()

    def get_schema(self) -> dict[str, Any]:
        return {
            "openapi": "3.0.3",
            "info": self.get_info(),
            "paths": self._get_paths(),
            "tags": self.get_tags(),
            "components": {"securitySchemes": self.get_security_schemes()},
        }

    def get_tags(self) -> list[dict[str, str]]:
        tag_map: dict[str, str] = {}
        for ep in self._registry.get_endpoints():
            for tag in ep.get("tags", []):
                if tag not in tag_map:
                    tag_map[tag] = tag.replace("_", " ").title()
        return [{"name": name, "description": desc} for name, desc in tag_map.items()]

    def get_security_schemes(self) -> dict[str, Any]:
        return {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "Token",
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
            },
        }

    def get_info(self) -> dict[str, Any]:
        versions = self._version_provider.get_all_version_info()
        return {
            "title": "NOVA CORE API",
            "description": "NOVA CORE AI operating system API.",
            "version": self._version_provider.get_version(),
            "versions": [v.get("version", "") for v in versions],
        }

    def get_endpoint_count(self) -> int:
        return self._registry.count()

    def _get_paths(self) -> dict[str, Any]:
        paths: dict[str, Any] = {}
        for ep in self._registry.get_endpoints():
            path = ep.get("path", "")
            method = ep.get("method", "GET").lower()
            if path not in paths:
                paths[path] = {}
            paths[path][method] = {
                "summary": ep.get("summary", ""),
                "description": ep.get("description", ""),
                "tags": ep.get("tags", []),
                "deprecated": ep.get("deprecated", False),
            }
        return paths
