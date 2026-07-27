"""API versioning support."""

from __future__ import annotations

import time
from typing import Any

from app.api.base import APIVersionProvider
from app.api.enums import APIVersion, DeprecationStatus
from app.api.models import APIVersionInfo


class DefaultAPIVersionProvider(APIVersionProvider):
    """Manages API versions, deprecation, and version negotiation."""

    def __init__(self) -> None:
        self._versions: dict[str, APIVersionInfo] = {
            APIVersion.V1.value: APIVersionInfo(
                version=APIVersion.V1.value,
                status=DeprecationStatus.CURRENT.value,
                released_at="2024-01-01",
                description="NOVA CORE API v1",
            ),
            APIVersion.V2.value: APIVersionInfo(
                version=APIVersion.V2.value,
                status=DeprecationStatus.CURRENT.value,
                released_at="2026-01-01",
                description="NOVA CORE API v2",
            ),
        }
        self._default_version = APIVersion.V1.value

    def get_version(self) -> str:
        return self._default_version

    def get_supported_versions(self) -> list[str]:
        return list(self._versions.keys())

    def is_deprecated(self, version: str) -> bool:
        info = self._versions.get(version)
        if info is None:
            return True
        return info.status in (DeprecationStatus.DEPRECATED.value, DeprecationStatus.SUNSET.value)

    def get_deprecation_date(self, version: str) -> str | None:
        info = self._versions.get(version)
        if info is None:
            return None
        return info.sunset_date or None

    def negotiate(self, accept_header: str | None) -> str:
        if accept_header and "application/vnd.nova.v2+json" in accept_header:
            if "v2" in self._versions:
                return "v2"
        return self._default_version

    def get_version_info(self, version: str) -> APIVersionInfo | None:
        return self._versions.get(version)

    def get_all_version_info(self) -> list[dict[str, Any]]:
        return [v.to_dict() for v in self._versions.values()]

    def add_version(self, info: APIVersionInfo) -> None:
        self._versions[info.version] = info

    def set_default(self, version: str) -> None:
        if version in self._versions:
            self._default_version = version
