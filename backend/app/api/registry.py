"""Endpoint registry for the API Platform."""

from __future__ import annotations

import logging
from typing import Any

from app.api.base import APIRegistry
from app.api.models import EndpointInfo

logger = logging.getLogger(__name__)


class DefaultAPIRegistry(APIRegistry):
    """Registry for all API endpoints with indexing by path, method, tag, and version."""

    def __init__(self) -> None:
        self._endpoints: list[EndpointInfo] = []
        self._index: dict[str, EndpointInfo] = {}

    def _key(self, path: str, method: str) -> str:
        return f"{method.upper()}:{path}"

    def register_endpoint(
        self,
        path: str,
        method: str,
        handler: Any,
        tags: list[str] | None = None,
        version: str = "v1",
        **kwargs: Any,
    ) -> None:
        key = self._key(path, method)
        endpoint = EndpointInfo(
            path=path,
            method=method.upper(),
            handler=handler,
            tags=tags or [],
            version=version,
            summary=kwargs.get("summary", ""),
            description=kwargs.get("description", ""),
            deprecated=kwargs.get("deprecated", False),
            sunset_date=kwargs.get("sunset_date", ""),
            permission_level=kwargs.get("permission_level", ""),
            rate_limit=kwargs.get("rate_limit", 0),
            metadata=kwargs.get("metadata", {}),
        )
        self._endpoints.append(endpoint)
        self._index[key] = endpoint
        logger.debug("Registered endpoint: %s %s", method, path)

    def get_endpoints(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._endpoints]

    def get_endpoint(self, path: str, method: str) -> dict[str, Any] | None:
        ep = self._index.get(self._key(path, method))
        return ep.to_dict() if ep else None

    def list_by_tag(self, tag: str) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._endpoints if tag in e.tags]

    def list_by_version(self, version: str) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._endpoints if e.version == version]

    def list_deprecated(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._endpoints if e.deprecated]

    def count(self) -> int:
        return len(self._endpoints)

    def get_tags(self) -> list[str]:
        tags: set[str] = set()
        for e in self._endpoints:
            tags.update(e.tags)
        return sorted(tags)

    def get_statistics(self) -> dict[str, Any]:
        by_version: dict[str, int] = {}
        by_tag: dict[str, int] = {}
        deprecated_count = 0
        for e in self._endpoints:
            by_version[e.version] = by_version.get(e.version, 0) + 1
            if e.deprecated:
                deprecated_count += 1
            for t in e.tags:
                by_tag[t] = by_tag.get(t, 0) + 1
        return {
            "total": len(self._endpoints),
            "by_version": by_version,
            "by_tag": by_tag,
            "deprecated": deprecated_count,
        }
