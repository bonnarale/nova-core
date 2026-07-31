"""Enterprise engine — top-level coordinator."""

from __future__ import annotations

import logging
from typing import Any

from app.enterprise.enums import PolicyType
from app.enterprise.manager import EnterpriseManager

logger = logging.getLogger(__name__)


class EnterpriseEngine:
    """Top-level enterprise features engine."""

    def __init__(self) -> None:
        self._manager = EnterpriseManager()

    @property
    def manager(self) -> EnterpriseManager:
        return self._manager

    async def start(self) -> None:
        await self._manager.start()

    async def shutdown(self) -> None:
        await self._manager.shutdown()

    def is_running(self) -> bool:
        return self._manager.is_running()

    def get_status(self) -> dict[str, Any]:
        return self._manager.get_status()

    def get_metrics(self) -> dict[str, Any]:
        return self._manager.get_metrics()

    def get_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._manager.get_traces(limit)

    # Organization
    async def create_organization(self, name: str, owner_id: str = "", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._manager.create_organization(name=name, owner_id=owner_id, metadata=metadata)

    async def get_organization(self, org_id: str) -> dict[str, Any] | None:
        return await self._manager.get_organization(org_id)

    async def list_organizations(self) -> list[dict[str, Any]]:
        return await self._manager.list_organizations()

    async def delete_organization(self, org_id: str) -> bool:
        return await self._manager.delete_organization(org_id)

    # Tenant
    async def create_tenant(self, org_id: str, name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._manager.create_tenant(org_id=org_id, name=name, metadata=metadata)

    async def get_tenant(self, tenant_id: str) -> dict[str, Any] | None:
        return await self._manager.get_tenant(tenant_id)

    async def list_tenants(self, org_id: str | None = None) -> list[dict[str, Any]]:
        return await self._manager.list_tenants(org_id=org_id)

    async def delete_tenant(self, tenant_id: str) -> bool:
        return await self._manager.delete_tenant(tenant_id)

    # Workspace
    async def create_workspace(self, org_id: str, name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._manager.create_workspace(org_id=org_id, name=name, metadata=metadata)

    async def get_workspace(self, workspace_id: str) -> dict[str, Any] | None:
        return await self._manager.get_workspace(workspace_id)

    async def list_workspaces(self, org_id: str | None = None) -> list[dict[str, Any]]:
        return await self._manager.list_workspaces(org_id=org_id)

    async def delete_workspace(self, workspace_id: str) -> bool:
        return await self._manager.delete_workspace(workspace_id)

    # Team
    async def create_team(self, org_id: str, name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._manager.create_team(org_id=org_id, name=name, metadata=metadata)

    async def list_teams(self, org_id: str | None = None) -> list[dict[str, Any]]:
        return await self._manager.list_teams(org_id=org_id)

    # Role
    async def list_roles(self) -> list[dict[str, Any]]:
        return await self._manager.list_roles()

    async def create_role(self, name: str, permissions: list[str] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._manager.create_role(name=name, permissions=permissions, metadata=metadata)

    # Permission
    async def check_permission(self, subject: str, resource: str, action: str) -> bool:
        return await self._manager.check_permission(subject=subject, resource=resource, action=action)

    async def list_permissions(self) -> list[dict[str, Any]]:
        return await self._manager.list_permissions()

    # Policy
    async def list_policies(self) -> list[dict[str, Any]]:
        return await self._manager.list_policies()

    async def create_policy(self, name: str, policy_type: str, rules: list[dict[str, Any]] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._manager.create_policy(name=name, policy_type=PolicyType(policy_type), rules=rules, metadata=metadata)

    # License
    async def get_license(self) -> dict[str, Any]:
        return await self._manager.get_license()

    # Quota
    async def get_quotas(self) -> dict[str, Any]:
        return await self._manager.get_quotas()

    # Audit
    async def get_audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return await self._manager.get_audit_events(limit=limit)
