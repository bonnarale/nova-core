"""Enterprise manager — coordinates all enterprise subsystems."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.enterprise.administration import AdministrationManager
from app.enterprise.audit import AuditManager
from app.enterprise.billing import BillingManager
from app.enterprise.enums import (
    AuditEventType,
    EnterpriseState,
    EnterpriseRole,
    MembershipRole,
    OrganizationStatus,
    PermissionAction,
    PermissionScope,
    PolicyType,
    QuotaType,
    TenantStatus,
    WorkspaceStatus,
)
from app.enterprise.lifecycle import EnterpriseLifecycle
from app.enterprise.licensing import License, LicenseEdition, LicensingManager
from app.enterprise.membership import MembershipManager
from app.enterprise.metrics import EnterpriseMetricsCollector
from app.enterprise.organization import OrganizationManager
from app.enterprise.permission import PermissionManager
from app.enterprise.policy import PolicyManager
from app.enterprise.quota import QuotaManager
from app.enterprise.role import RoleManager
from app.enterprise.team import TeamManager
from app.enterprise.tenant import TenantManager
from app.enterprise.tracing import EnterpriseTracer
from app.enterprise.workspace import WorkspaceManager

logger = logging.getLogger(__name__)


class EnterpriseManager:
    """Coordinates all enterprise subsystems into a cohesive layer."""

    def __init__(self) -> None:
        self._lifecycle = EnterpriseLifecycle()
        self._organizations = OrganizationManager()
        self._tenants = TenantManager()
        self._workspaces = WorkspaceManager()
        self._teams = TeamManager()
        self._membership = MembershipManager()
        self._roles = RoleManager()
        self._permissions = PermissionManager()
        self._policies = PolicyManager()
        self._audit = AuditManager()
        self._billing = BillingManager()
        self._licensing = LicensingManager()
        self._quotas = QuotaManager()
        self._administration = AdministrationManager()
        self._metrics = EnterpriseMetricsCollector()
        self._tracer = EnterpriseTracer()
        self._running = False

    @property
    def lifecycle(self) -> EnterpriseLifecycle:
        return self._lifecycle

    @property
    def organizations(self) -> OrganizationManager:
        return self._organizations

    @property
    def tenants(self) -> TenantManager:
        return self._tenants

    @property
    def workspaces(self) -> WorkspaceManager:
        return self._workspaces

    @property
    def teams(self) -> TeamManager:
        return self._teams

    @property
    def membership(self) -> MembershipManager:
        return self._membership

    @property
    def roles(self) -> RoleManager:
        return self._roles

    @property
    def permissions(self) -> PermissionManager:
        return self._permissions

    @property
    def policies(self) -> PolicyManager:
        return self._policies

    @property
    def audit(self) -> AuditManager:
        return self._audit

    @property
    def billing(self) -> BillingManager:
        return self._billing

    @property
    def licensing(self) -> LicensingManager:
        return self._licensing

    @property
    def quotas(self) -> QuotaManager:
        return self._quotas

    @property
    def administration(self) -> AdministrationManager:
        return self._administration

    @property
    def metrics(self) -> EnterpriseMetricsCollector:
        return self._metrics

    @property
    def tracer(self) -> EnterpriseTracer:
        return self._tracer

    async def start(self) -> None:
        self._metrics.start()
        self._lifecycle.transition(EnterpriseState.INITIALIZED, "init")
        self._lifecycle.transition(EnterpriseState.READY, "ready")
        self._lifecycle.transition(EnterpriseState.ACTIVE, "start")
        self._running = True
        logger.info("Enterprise manager started")

    async def shutdown(self) -> None:
        self._lifecycle.transition(EnterpriseState.SUSPENDED, "shutdown")
        self._running = False
        logger.info("Enterprise manager stopped")

    def is_running(self) -> bool:
        return self._running

    # --- Organization ---

    async def create_organization(self, name: str, owner_id: str = "", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("create_organization")
        org = self._organizations.create(name=name, owner_id=owner_id, metadata=metadata)
        self._metrics.record_organization_created()
        self._audit.record(AuditEventType.ADMINISTRATIVE, owner_id or "system", {"action": "create_organization", "org_id": org.id})
        self._tracer.finish_trace(trace_id)
        return org.to_dict()

    async def get_organization(self, org_id: str) -> dict[str, Any] | None:
        org = self._organizations.get(org_id)
        return org.to_dict() if org else None

    async def list_organizations(self) -> list[dict[str, Any]]:
        return [o.to_dict() for o in self._organizations.get_all()]

    async def delete_organization(self, org_id: str) -> bool:
        trace_id = self._tracer.start_trace("delete_organization")
        result = self._organizations.delete(org_id)
        if result:
            self._metrics.record_organization_deleted()
            self._audit.record(AuditEventType.ADMINISTRATIVE, "system", {"action": "delete_organization", "org_id": org_id})
        self._tracer.finish_trace(trace_id)
        return result

    # --- Tenant ---

    async def create_tenant(self, org_id: str, name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("create_tenant")
        tenant = self._tenants.create(org_id=org_id, name=name, metadata=metadata)
        self._metrics.record_tenant_created()
        self._audit.record(AuditEventType.ADMINISTRATIVE, "system", {"action": "create_tenant", "tenant_id": tenant.id})
        self._tracer.finish_trace(trace_id)
        return tenant.to_dict()

    async def get_tenant(self, tenant_id: str) -> dict[str, Any] | None:
        tenant = self._tenants.get(tenant_id)
        return tenant.to_dict() if tenant else None

    async def list_tenants(self, org_id: str | None = None) -> list[dict[str, Any]]:
        if org_id:
            return [t.to_dict() for t in self._tenants.list_for_org(org_id)]
        return [t.to_dict() for t in self._tenants.get_all()]

    async def delete_tenant(self, tenant_id: str) -> bool:
        trace_id = self._tracer.start_trace("delete_tenant")
        result = self._tenants.delete(tenant_id)
        if result:
            self._metrics.record_tenant_deleted()
        self._tracer.finish_trace(trace_id)
        return result

    # --- Workspace ---

    async def create_workspace(self, org_id: str, name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("create_workspace")
        ws = self._workspaces.create(org_id=org_id, name=name, metadata=metadata)
        self._metrics.record_workspace_created()
        self._audit.record(AuditEventType.ADMINISTRATIVE, "system", {"action": "create_workspace", "workspace_id": ws.id})
        self._tracer.finish_trace(trace_id)
        return ws.to_dict()

    async def get_workspace(self, workspace_id: str) -> dict[str, Any] | None:
        ws = self._workspaces.get(workspace_id)
        return ws.to_dict() if ws else None

    async def list_workspaces(self, org_id: str | None = None) -> list[dict[str, Any]]:
        if org_id:
            return [w.to_dict() for w in self._workspaces.list_for_org(org_id)]
        return [w.to_dict() for w in self._workspaces.get_all()]

    async def delete_workspace(self, workspace_id: str) -> bool:
        trace_id = self._tracer.start_trace("delete_workspace")
        result = self._workspaces.delete(workspace_id)
        if result:
            self._metrics.record_workspace_deleted()
        self._tracer.finish_trace(trace_id)
        return result

    # --- Team ---

    async def create_team(self, org_id: str, name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("create_team")
        team = self._teams.create(org_id=org_id, name=name, metadata=metadata)
        self._audit.record(AuditEventType.ADMINISTRATIVE, "system", {"action": "create_team", "team_id": team.id})
        self._tracer.finish_trace(trace_id)
        return team.to_dict()

    async def list_teams(self, org_id: str | None = None) -> list[dict[str, Any]]:
        if org_id:
            return [t.to_dict() for t in self._teams.list_for_org(org_id)]
        return [t.to_dict() for t in self._teams.get_all()]

    # --- Role ---

    async def list_roles(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._roles.get_all()]

    async def create_role(self, name: str, permissions: list[str] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("create_role")
        role = self._roles.create(name=name, permissions=permissions, metadata=metadata)
        self._audit.record(AuditEventType.ADMINISTRATIVE, "system", {"action": "create_role", "role_name": name})
        self._tracer.finish_trace(trace_id)
        return role.to_dict()

    # --- Permission ---

    async def check_permission(self, subject: str, resource: str, action: str) -> bool:
        trace_id = self._tracer.start_trace("check_permission")
        self._metrics.record_permission_check()
        result = self._permissions.check(subject=subject, resource=resource, action=action)
        self._tracer.finish_trace(trace_id)
        return result

    async def list_permissions(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._permissions.get_all()]

    # --- Policy ---

    async def list_policies(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._policies.get_all()]

    async def create_policy(self, name: str, policy_type: PolicyType, rules: list[dict[str, Any]] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        trace_id = self._tracer.start_trace("create_policy")
        policy = self._policies.create(name=name, policy_type=policy_type, rules=rules, metadata=metadata)
        self._audit.record(AuditEventType.CONFIGURATION, "system", {"action": "create_policy", "policy_name": name})
        self._tracer.finish_trace(trace_id)
        return policy.to_dict()

    # --- License ---

    async def get_license(self) -> dict[str, Any]:
        return self._licensing.validate_license()

    # --- Quota ---

    async def get_quotas(self) -> dict[str, Any]:
        return self._quotas.get_all()

    # --- Audit ---

    async def get_audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._audit.query(limit=limit)]

    # --- Status & Metrics ---

    def get_status(self) -> dict[str, Any]:
        status = self._lifecycle.get_status()
        return {
            **status,
            "edition": self._licensing.get_edition(),
            "total_organizations": self._organizations.count(),
            "total_tenants": self._tenants.count(),
            "total_workspaces": self._workspaces.count(),
            "total_users": self._membership.count(),
        }

    def get_metrics(self) -> dict[str, Any]:
        return self._metrics.snapshot().to_dict()

    def get_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._tracer.get_traces(limit)
