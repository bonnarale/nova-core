"""Abstract base classes for the Enterprise subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EnterpriseProvider(ABC):
    """Base interface for the enterprise engine."""

    @abstractmethod
    async def initialize(self) -> None:
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        ...

    @abstractmethod
    def is_running(self) -> bool:
        ...

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        ...


class OrganizationProvider(ABC):
    """Base interface for organization management."""

    @abstractmethod
    async def create_organization(self, name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        ...

    @abstractmethod
    async def get_organization(self, org_id: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    async def list_organizations(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def delete_organization(self, org_id: str) -> bool:
        ...


class TenantProvider(ABC):
    """Base interface for tenant management."""

    @abstractmethod
    async def create_tenant(self, org_id: str, name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        ...

    @abstractmethod
    async def get_tenant(self, tenant_id: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    async def list_tenants(self, org_id: str | None = None) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def delete_tenant(self, tenant_id: str) -> bool:
        ...


class RoleProvider(ABC):
    """Base interface for role management."""

    @abstractmethod
    async def create_role(self, name: str, permissions: list[str] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        ...

    @abstractmethod
    async def get_role(self, role_id: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    async def list_roles(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def delete_role(self, role_id: str) -> bool:
        ...


class PermissionProvider(ABC):
    """Base interface for permission evaluation."""

    @abstractmethod
    async def check_permission(self, subject: str, resource: str, action: str) -> bool:
        ...

    @abstractmethod
    async def assign_role(self, subject: str, role: str, scope: str, scope_id: str = "") -> bool:
        ...

    @abstractmethod
    async def revoke_role(self, subject: str, role: str, scope: str, scope_id: str = "") -> bool:
        ...

    @abstractmethod
    async def get_permissions(self, subject: str) -> list[dict[str, Any]]:
        ...


class AuditProvider(ABC):
    """Base interface for audit logging."""

    @abstractmethod
    async def record_event(self, event_type: str, actor: str, details: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    async def query_events(self, filters: dict[str, Any] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def get_event(self, event_id: str) -> dict[str, Any] | None:
        ...


class LicensingProvider(ABC):
    """Base interface for license management."""

    @abstractmethod
    def get_edition(self) -> str:
        ...

    @abstractmethod
    def is_feature_available(self, feature: str) -> bool:
        ...

    @abstractmethod
    def validate_license(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        ...


class BillingProvider(ABC):
    """Base interface for billing management."""

    @abstractmethod
    async def get_subscription(self, org_id: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    async def record_usage(self, org_id: str, metric: str, quantity: float) -> dict[str, Any]:
        ...

    @abstractmethod
    async def get_usage(self, org_id: str, period: str = "current") -> dict[str, Any]:
        ...

    @abstractmethod
    async def list_invoices(self, org_id: str) -> list[dict[str, Any]]:
        ...
