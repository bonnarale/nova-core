"""Licensing — edition metadata, feature availability, license validation, capability gating."""

from __future__ import annotations

import threading
import time
from typing import Any

from app.enterprise.enums import LicenseEdition


_EDITION_FEATURES: dict[LicenseEdition, list[str]] = {
    LicenseEdition.COMMUNITY: [
        "basic_agents",
        "basic_workflows",
        "single_user",
        "local_models",
    ],
    LicenseEdition.PROFESSIONAL: [
        "basic_agents",
        "basic_workflows",
        "multi_user",
        "local_models",
        "cloud_models",
        "priority_support",
        "advanced_workflows",
    ],
    LicenseEdition.ENTERPRISE: [
        "basic_agents",
        "basic_workflows",
        "multi_user",
        "local_models",
        "cloud_models",
        "priority_support",
        "advanced_workflows",
        "multi_tenant",
        "sso",
        "audit_log",
        "rbac",
        "custom_policies",
        "sla_guarantees",
    ],
    LicenseEdition.UNLIMITED: [
        "basic_agents",
        "basic_workflows",
        "multi_user",
        "local_models",
        "cloud_models",
        "priority_support",
        "advanced_workflows",
        "multi_tenant",
        "sso",
        "audit_log",
        "rbac",
        "custom_policies",
        "sla_guarantees",
        "white_label",
        "unlimited_agents",
        "unlimited_storage",
        "dedicated_support",
    ],
}


class License:
    """Represents a license."""

    __slots__ = (
        "edition", "org_id", "issued_at", "expires_at",
        "features", "metadata",
    )

    def __init__(
        self,
        edition: LicenseEdition = LicenseEdition.COMMUNITY,
        org_id: str = "",
        expires_at: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.edition = edition
        self.org_id = org_id
        self.issued_at = time.time()
        self.expires_at = expires_at
        self.features = list(_EDITION_FEATURES.get(edition, []))
        self.metadata = metadata or {}

    def is_valid(self) -> bool:
        if self.expires_at and time.time() > self.expires_at:
            return False
        return True

    def has_feature(self, feature: str) -> bool:
        if not self.is_valid():
            return False
        return feature in self.features or "unlimited_agents" in self.features

    def to_dict(self) -> dict[str, Any]:
        return {
            "edition": self.edition.value,
            "org_id": self.org_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "features": self.features,
            "valid": self.is_valid(),
            "metadata": self.metadata,
        }


class LicensingManager:
    """Manages licenses with thread-safe operations."""

    def __init__(self, default_edition: LicenseEdition = LicenseEdition.COMMUNITY) -> None:
        self._default_edition = default_edition
        self._licenses: dict[str, License] = {}
        self._lock = threading.RLock()

    def get_license(self, org_id: str = "") -> License:
        with self._lock:
            return self._licenses.get(org_id, License(edition=self._default_edition, org_id=org_id))

    def set_license(self, license_obj: License, org_id: str = "") -> None:
        with self._lock:
            self._licenses[org_id] = license_obj

    def get_edition(self, org_id: str = "") -> str:
        return self.get_license(org_id).edition.value

    def is_feature_available(self, feature: str, org_id: str = "") -> bool:
        return self.get_license(org_id).has_feature(feature)

    def validate_license(self, org_id: str = "") -> dict[str, Any]:
        license_obj = self.get_license(org_id)
        return {
            "valid": license_obj.is_valid(),
            "edition": license_obj.edition.value,
            "features": license_obj.features,
            "expires_at": license_obj.expires_at,
        }

    def get_capabilities(self, org_id: str = "") -> list[str]:
        return list(self.get_license(org_id).features)

    def count(self) -> int:
        with self._lock:
            return len(self._licenses)
