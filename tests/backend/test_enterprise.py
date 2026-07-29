"""Tests for the Enterprise Features subsystem (Ch36)."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import pytest

from app.enterprise.enums import (
    AuditEventType,
    BillingStatus,
    EnterpriseRole,
    EnterpriseState,
    LicenseEdition,
    MembershipRole,
    OrganizationStatus,
    PermissionAction,
    PermissionScope,
    PolicyType,
    QuotaType,
    TeamStatus,
    TenantStatus,
    WorkspaceStatus,
)
from app.enterprise.base import (
    EnterpriseProvider,
    OrganizationProvider,
    TenantProvider,
    RoleProvider,
    PermissionProvider,
    AuditProvider,
    LicensingProvider,
    BillingProvider,
)
from app.enterprise.organization import OrganizationManager, Organization
from app.enterprise.tenant import TenantManager, Tenant
from app.enterprise.workspace import WorkspaceManager, Workspace
from app.enterprise.team import TeamManager, Team
from app.enterprise.membership import MembershipManager, Membership
from app.enterprise.role import RoleManager, Role
from app.enterprise.permission import PermissionManager, Permission
from app.enterprise.policy import PolicyManager, EnterprisePolicy
from app.enterprise.audit import AuditManager, AuditEvent
from app.enterprise.billing import BillingManager, Subscription, UsageRecord, Invoice
from app.enterprise.licensing import LicensingManager, License
from app.enterprise.quota import QuotaManager, Quota
from app.enterprise.administration import AdministrationManager
from app.enterprise.lifecycle import EnterpriseLifecycle
from app.enterprise.repository import EnterpriseRepository
from app.enterprise.persistence import InMemoryEnterpriseRepository
from app.enterprise.metrics import EnterpriseMetricsCollector, EnterpriseMetrics
from app.enterprise.tracing import EnterpriseTracer
from app.enterprise.manager import EnterpriseManager
from app.enterprise.engine import EnterpriseEngine
from app.enterprise.factory import EnterpriseFactory


# ===== Enums =====

class TestEnums:
    def test_enterprise_state(self) -> None:
        assert EnterpriseState.REGISTERED.value == "registered"
        assert EnterpriseState.ACTIVE.value == "active"
        assert EnterpriseState.SUSPENDED.value == "suspended"
        assert EnterpriseState.ARCHIVED.value == "archived"
        assert EnterpriseState.DELETED.value == "deleted"

    def test_organization_status(self) -> None:
        assert OrganizationStatus.ACTIVE.value == "active"
        assert OrganizationStatus.SUSPENDED.value == "suspended"
        assert OrganizationStatus.ARCHIVED.value == "archived"
        assert OrganizationStatus.DELETED.value == "deleted"

    def test_tenant_status(self) -> None:
        assert TenantStatus.ACTIVE.value == "active"
        assert TenantStatus.SUSPENDED.value == "suspended"
        assert TenantStatus.DELETED.value == "deleted"

    def test_workspace_status(self) -> None:
        assert WorkspaceStatus.ACTIVE.value == "active"
        assert WorkspaceStatus.ARCHIVED.value == "archived"
        assert WorkspaceStatus.DELETED.value == "deleted"

    def test_team_status(self) -> None:
        assert TeamStatus.ACTIVE.value == "active"
        assert TeamStatus.DISSOLVED.value == "dissolved"

    def test_membership_role(self) -> None:
        assert MembershipRole.OWNER.value == "owner"
        assert MembershipRole.LEAD.value == "lead"
        assert MembershipRole.MEMBER.value == "member"
        assert MembershipRole.OBSERVER.value == "observer"

    def test_enterprise_role(self) -> None:
        assert EnterpriseRole.OWNER.value == "owner"
        assert EnterpriseRole.ADMINISTRATOR.value == "administrator"
        assert EnterpriseRole.MANAGER.value == "manager"
        assert EnterpriseRole.DEVELOPER.value == "developer"
        assert EnterpriseRole.OPERATOR.value == "operator"
        assert EnterpriseRole.ANALYST.value == "analyst"
        assert EnterpriseRole.VIEWER.value == "viewer"

    def test_permission_scope(self) -> None:
        assert PermissionScope.SYSTEM.value == "system"
        assert PermissionScope.ORGANIZATION.value == "organization"
        assert PermissionScope.WORKSPACE.value == "workspace"
        assert PermissionScope.RESOURCE.value == "resource"
        assert PermissionScope.CUSTOM.value == "custom"

    def test_permission_action(self) -> None:
        assert PermissionAction.CREATE.value == "create"
        assert PermissionAction.READ.value == "read"
        assert PermissionAction.UPDATE.value == "update"
        assert PermissionAction.DELETE.value == "delete"
        assert PermissionAction.EXECUTE.value == "execute"
        assert PermissionAction.MANAGE.value == "manage"
        assert PermissionAction.ADMIN.value == "admin"
        assert PermissionAction.SHARE.value == "share"

    def test_policy_type(self) -> None:
        assert PolicyType.ACCESS.value == "access"
        assert PolicyType.EXECUTION.value == "execution"
        assert PolicyType.SECURITY.value == "security"
        assert PolicyType.RETENTION.value == "retention"

    def test_audit_event_type(self) -> None:
        assert AuditEventType.AUTHENTICATION.value == "authentication"
        assert AuditEventType.AUTHORIZATION.value == "authorization"
        assert AuditEventType.API_USAGE.value == "api_usage"
        assert AuditEventType.WORKFLOW_EXECUTION.value == "workflow_execution"
        assert AuditEventType.ADMINISTRATIVE.value == "administrative"
        assert AuditEventType.CONFIGURATION.value == "configuration"

    def test_license_edition(self) -> None:
        assert LicenseEdition.COMMUNITY.value == "community"
        assert LicenseEdition.PROFESSIONAL.value == "professional"
        assert LicenseEdition.ENTERPRISE.value == "enterprise"
        assert LicenseEdition.UNLIMITED.value == "unlimited"

    def test_quota_type(self) -> None:
        assert QuotaType.USERS.value == "users"
        assert QuotaType.AGENTS.value == "agents"
        assert QuotaType.WORKFLOWS.value == "workflows"
        assert QuotaType.EXECUTIONS.value == "executions"
        assert QuotaType.STORAGE.value == "storage"
        assert QuotaType.API_REQUESTS.value == "api_requests"
        assert QuotaType.VECTOR_MEMORY.value == "vector_memory"
        assert QuotaType.PLUGINS.value == "plugins"

    def test_billing_status(self) -> None:
        assert BillingStatus.ACTIVE.value == "active"
        assert BillingStatus.PAST_DUE.value == "past_due"
        assert BillingStatus.CANCELED.value == "canceled"
        assert BillingStatus.TRIAL.value == "trial"
        assert BillingStatus.EXPIRED.value == "expired"


# ===== ABCs =====

class TestABCs:
    def test_enterprise_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            EnterpriseProvider()

    def test_organization_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            OrganizationProvider()

    def test_tenant_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            TenantProvider()

    def test_role_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            RoleProvider()

    def test_permission_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            PermissionProvider()

    def test_audit_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            AuditProvider()

    def test_licensing_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            LicensingProvider()

    def test_billing_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            BillingProvider()


# ===== Organization =====

class TestOrganization:
    def test_create_organization(self) -> None:
        mgr = OrganizationManager()
        org = mgr.create(name="Acme Corp", owner_id="user1")
        assert org.name == "Acme Corp"
        assert org.owner_id == "user1"
        assert org.status == OrganizationStatus.ACTIVE

    def test_get_organization(self) -> None:
        mgr = OrganizationManager()
        org = mgr.create(name="Test Org")
        fetched = mgr.get(org.id)
        assert fetched is not None
        assert fetched.id == org.id

    def test_get_nonexistent(self) -> None:
        mgr = OrganizationManager()
        assert mgr.get("nonexistent") is None

    def test_list_organizations(self) -> None:
        mgr = OrganizationManager()
        mgr.create(name="Org1")
        mgr.create(name="Org2")
        assert mgr.count() == 2

    def test_delete_organization(self) -> None:
        mgr = OrganizationManager()
        org = mgr.create(name="To Delete")
        assert mgr.delete(org.id) is True
        assert mgr.get(org.id).status == OrganizationStatus.DELETED

    def test_delete_nonexistent(self) -> None:
        mgr = OrganizationManager()
        assert mgr.delete("nonexistent") is False

    def test_update_status(self) -> None:
        mgr = OrganizationManager()
        org = mgr.create(name="Test")
        assert mgr.update_status(org.id, OrganizationStatus.SUSPENDED) is True
        assert mgr.get(org.id).status == OrganizationStatus.SUSPENDED

    def test_to_dict(self) -> None:
        org = Organization(name="Dict Test", owner_id="u1", metadata={"key": "val"})
        d = org.to_dict()
        assert d["name"] == "Dict Test"
        assert d["owner_id"] == "u1"
        assert d["metadata"]["key"] == "val"

    def test_get_active(self) -> None:
        mgr = OrganizationManager()
        o1 = mgr.create(name="Active")
        o2 = mgr.create(name="Inactive")
        mgr.update_status(o2.id, OrganizationStatus.SUSPENDED)
        active = mgr.get_active()
        assert len(active) == 1
        assert active[0].name == "Active"


# ===== Tenant =====

class TestTenant:
    def test_create_tenant(self) -> None:
        mgr = TenantManager()
        tenant = mgr.create(org_id="org1", name="Tenant A")
        assert tenant.org_id == "org1"
        assert tenant.name == "Tenant A"
        assert tenant.status == TenantStatus.ACTIVE

    def test_get_tenant(self) -> None:
        mgr = TenantManager()
        t = mgr.create(org_id="org1", name="T1")
        assert mgr.get(t.id) is not None

    def test_list_for_org(self) -> None:
        mgr = TenantManager()
        mgr.create(org_id="org1", name="T1")
        mgr.create(org_id="org1", name="T2")
        mgr.create(org_id="org2", name="T3")
        result = mgr.list_for_org("org1")
        assert len(result) == 2

    def test_update_status(self) -> None:
        mgr = TenantManager()
        t = mgr.create(org_id="org1", name="T1")
        assert mgr.update_status(t.id, TenantStatus.SUSPENDED) is True
        assert mgr.get(t.id).status == TenantStatus.SUSPENDED

    def test_update_config(self) -> None:
        mgr = TenantManager()
        t = mgr.create(org_id="org1", name="T1")
        assert mgr.update_config(t.id, {"theme": "dark"}) is True
        assert mgr.get(t.id).config["theme"] == "dark"

    def test_delete_tenant(self) -> None:
        mgr = TenantManager()
        t = mgr.create(org_id="org1", name="T1")
        assert mgr.delete(t.id) is True
        assert mgr.get(t.id).status == TenantStatus.DELETED

    def test_count_active(self) -> None:
        mgr = TenantManager()
        t1 = mgr.create(org_id="org1", name="T1")
        t2 = mgr.create(org_id="org1", name="T2")
        mgr.update_status(t2.id, TenantStatus.DELETED)
        assert mgr.count_active() == 1

    def test_to_dict(self) -> None:
        t = Tenant(org_id="org1", name="T1", config={"a": 1}, metadata={"b": 2})
        d = t.to_dict()
        assert d["org_id"] == "org1"
        assert d["config"]["a"] == 1


# ===== Workspace =====

class TestWorkspace:
    def test_create_workspace(self) -> None:
        mgr = WorkspaceManager()
        ws = mgr.create(org_id="org1", name="Workspace Alpha")
        assert ws.name == "Workspace Alpha"
        assert ws.status == WorkspaceStatus.ACTIVE

    def test_get_workspace(self) -> None:
        mgr = WorkspaceManager()
        ws = mgr.create(org_id="org1", name="W1")
        assert mgr.get(ws.id) is not None

    def test_list_for_org(self) -> None:
        mgr = WorkspaceManager()
        mgr.create(org_id="org1", name="W1")
        mgr.create(org_id="org2", name="W2")
        assert len(mgr.list_for_org("org1")) == 1

    def test_archive_workspace(self) -> None:
        mgr = WorkspaceManager()
        ws = mgr.create(org_id="org1", name="W1")
        assert mgr.archive(ws.id) is True
        assert mgr.get(ws.id).status == WorkspaceStatus.ARCHIVED

    def test_delete_workspace(self) -> None:
        mgr = WorkspaceManager()
        ws = mgr.create(org_id="org1", name="W1")
        assert mgr.delete(ws.id) is True
        assert mgr.get(ws.id).status == WorkspaceStatus.DELETED

    def test_update_config(self) -> None:
        mgr = WorkspaceManager()
        ws = mgr.create(org_id="org1", name="W1")
        assert mgr.update_config(ws.id, {"setting": "value"}) is True
        assert mgr.get(ws.id).config["setting"] == "value"

    def test_count_active(self) -> None:
        mgr = WorkspaceManager()
        w1 = mgr.create(org_id="org1", name="W1")
        w2 = mgr.create(org_id="org1", name="W2")
        mgr.archive(w2.id)
        assert mgr.count_active() == 1

    def test_to_dict(self) -> None:
        ws = Workspace(org_id="org1", name="W1", metadata={"tag": "prod"})
        d = ws.to_dict()
        assert d["org_id"] == "org1"
        assert d["metadata"]["tag"] == "prod"


# ===== Team =====

class TestTeam:
    def test_create_team(self) -> None:
        mgr = TeamManager()
        team = mgr.create(org_id="org1", name="Engineering")
        assert team.name == "Engineering"
        assert team.status == TeamStatus.ACTIVE

    def test_get_team(self) -> None:
        mgr = TeamManager()
        team = mgr.create(org_id="org1", name="T1")
        assert mgr.get(team.id) is not None

    def test_list_for_org(self) -> None:
        mgr = TeamManager()
        mgr.create(org_id="org1", name="T1")
        mgr.create(org_id="org1", name="T2")
        mgr.create(org_id="org2", name="T3")
        assert len(mgr.list_for_org("org1")) == 2

    def test_list_children(self) -> None:
        mgr = TeamManager()
        parent = mgr.create(org_id="org1", name="Parent")
        mgr.create(org_id="org1", name="Child1", parent_id=parent.id)
        mgr.create(org_id="org1", name="Child2", parent_id=parent.id)
        assert len(mgr.list_children(parent.id)) == 2

    def test_dissolve_team(self) -> None:
        mgr = TeamManager()
        team = mgr.create(org_id="org1", name="T1")
        assert mgr.dissolve(team.id) is True
        assert mgr.get(team.id).status == TeamStatus.DISSOLVED

    def test_delete_team(self) -> None:
        mgr = TeamManager()
        team = mgr.create(org_id="org1", name="T1")
        assert mgr.delete(team.id) is True
        assert mgr.get(team.id) is None

    def test_count_active(self) -> None:
        mgr = TeamManager()
        t1 = mgr.create(org_id="org1", name="T1")
        t2 = mgr.create(org_id="org1", name="T2")
        mgr.dissolve(t2.id)
        assert mgr.count_active() == 1

    def test_to_dict(self) -> None:
        team = Team(org_id="org1", name="T1", parent_id="p1", metadata={"x": 1})
        d = team.to_dict()
        assert d["parent_id"] == "p1"


# ===== Membership =====

class TestMembership:
    def test_add_member(self) -> None:
        mgr = MembershipManager()
        m = mgr.add_member(user_id="u1", team_id="t1", role=MembershipRole.MEMBER)
        assert m.user_id == "u1"
        assert m.team_id == "t1"
        assert m.role == MembershipRole.MEMBER

    def test_get_by_user_and_team(self) -> None:
        mgr = MembershipManager()
        mgr.add_member(user_id="u1", team_id="t1")
        m = mgr.get_by_user_and_team("u1", "t1")
        assert m is not None

    def test_list_for_team(self) -> None:
        mgr = MembershipManager()
        mgr.add_member(user_id="u1", team_id="t1")
        mgr.add_member(user_id="u2", team_id="t1")
        mgr.add_member(user_id="u3", team_id="t2")
        assert len(mgr.list_for_team("t1")) == 2

    def test_list_for_user(self) -> None:
        mgr = MembershipManager()
        mgr.add_member(user_id="u1", team_id="t1")
        mgr.add_member(user_id="u1", team_id="t2")
        assert len(mgr.list_for_user("u1")) == 2

    def test_update_role(self) -> None:
        mgr = MembershipManager()
        m = mgr.add_member(user_id="u1", team_id="t1")
        assert mgr.update_role(m.id, MembershipRole.LEAD) is True
        assert mgr.get(m.id).role == MembershipRole.LEAD

    def test_remove_member(self) -> None:
        mgr = MembershipManager()
        mgr.add_member(user_id="u1", team_id="t1")
        assert mgr.remove_member("u1", "t1") is True
        assert mgr.get_by_user_and_team("u1", "t1") is None

    def test_remove_nonexistent(self) -> None:
        mgr = MembershipManager()
        assert mgr.remove_member("u1", "t1") is False

    def test_count_for_team(self) -> None:
        mgr = MembershipManager()
        mgr.add_member(user_id="u1", team_id="t1")
        mgr.add_member(user_id="u2", team_id="t1")
        assert mgr.count_for_team("t1") == 2

    def test_to_dict(self) -> None:
        m = Membership(user_id="u1", team_id="t1", role=MembershipRole.OWNER, metadata={"a": 1})
        d = m.to_dict()
        assert d["role"] == "owner"
        assert d["metadata"]["a"] == 1


# ===== Role =====

class TestRole:
    def test_default_roles_created(self) -> None:
        mgr = RoleManager()
        assert mgr.count() == 7

    def test_get_default_role(self) -> None:
        mgr = RoleManager()
        role = mgr.get("owner")
        assert role is not None
        assert role.is_default is True
        assert "*" in role.permissions

    def test_create_custom_role(self) -> None:
        mgr = RoleManager()
        role = mgr.create(name="custom_role", display_name="Custom Role", permissions=["read", "write"])
        assert role.name == "custom_role"
        assert role.permissions == ["read", "write"]

    def test_has_permission(self) -> None:
        mgr = RoleManager()
        assert mgr.has_permission("owner", "anything") is True
        assert mgr.has_permission("viewer", "read") is True
        assert mgr.has_permission("viewer", "delete") is False

    def test_update_permissions(self) -> None:
        mgr = RoleManager()
        mgr.update_permissions("developer", ["read", "write", "deploy"])
        assert mgr.get("developer").permissions == ["read", "write", "deploy"]

    def test_delete_custom_role(self) -> None:
        mgr = RoleManager()
        mgr.create(name="temp_role")
        assert mgr.delete("temp_role") is True
        assert mgr.get("temp_role") is None

    def test_cannot_delete_default_role(self) -> None:
        mgr = RoleManager()
        assert mgr.delete("owner") is False

    def test_to_dict(self) -> None:
        role = Role(name="test", display_name="Test", permissions=["read"])
        d = role.to_dict()
        assert d["name"] == "test"
        assert d["permissions"] == ["read"]


# ===== Permission =====

class TestPermission:
    def test_assign_permission(self) -> None:
        mgr = PermissionManager()
        p = mgr.assign(subject="user1", role="developer", scope=PermissionScope.ORGANIZATION, scope_id="org1")
        assert p.subject == "user1"
        assert p.role == "developer"

    def test_check_permission(self) -> None:
        mgr = PermissionManager()
        mgr.assign(subject="user1", role="developer", scope=PermissionScope.SYSTEM)
        assert mgr.check(subject="user1", resource="anything", action="read") is True

    def test_check_no_permission(self) -> None:
        mgr = PermissionManager()
        assert mgr.check(subject="unknown", resource="anything", action="read") is False

    def test_revoke_permission(self) -> None:
        mgr = PermissionManager()
        p = mgr.assign(subject="user1", role="viewer", scope=PermissionScope.SYSTEM)
        assert mgr.revoke(p.id) is True
        assert mgr.check(subject="user1", resource="r", action="read") is False

    def test_revoke_by_subject_role(self) -> None:
        mgr = PermissionManager()
        mgr.assign(subject="user1", role="viewer", scope=PermissionScope.WORKSPACE, scope_id="ws1")
        assert mgr.revoke_by_subject_role("user1", "viewer", PermissionScope.WORKSPACE, "ws1") is True

    def test_get_for_subject(self) -> None:
        mgr = PermissionManager()
        mgr.assign(subject="user1", role="viewer", scope=PermissionScope.SYSTEM)
        mgr.assign(subject="user1", role="admin", scope=PermissionScope.ORGANIZATION)
        assert len(mgr.get_for_subject("user1")) == 2

    def test_checks_count(self) -> None:
        mgr = PermissionManager()
        mgr.check(subject="u1", resource="r", action="read")
        mgr.check(subject="u1", resource="r", action="write")
        assert mgr.get_checks_count() == 2

    def test_to_dict(self) -> None:
        p = Permission(subject="u1", role="viewer", scope=PermissionScope.SYSTEM)
        d = p.to_dict()
        assert d["subject"] == "u1"
        assert d["scope"] == "system"


# ===== Policy =====

class TestPolicy:
    def test_default_policies_created(self) -> None:
        mgr = PolicyManager()
        assert mgr.count() == 4

    def test_get_default_policy(self) -> None:
        mgr = PolicyManager()
        p = mgr.get("default_access")
        assert p is not None
        assert p.policy_type == PolicyType.ACCESS

    def test_create_policy(self) -> None:
        mgr = PolicyManager()
        p = mgr.create(name="custom", policy_type=PolicyType.SECURITY, rules=[{"require_mfa": True}])
        assert p.name == "custom"
        assert p.policy_type == PolicyType.SECURITY

    def test_evaluate_policy(self) -> None:
        mgr = PolicyManager()
        result = mgr.evaluate("default_access", {"action": "read"})
        assert result["allowed"] is True

    def test_evaluate_no_policy(self) -> None:
        mgr = PolicyManager()
        result = mgr.evaluate("nonexistent", {"action": "read"})
        assert result["allowed"] is True
        assert result["reason"] == "no_policy"

    def test_toggle_policy(self) -> None:
        mgr = PolicyManager()
        assert mgr.toggle("default_access", False) is True
        assert mgr.get("default_access").enabled is False

    def test_delete_policy(self) -> None:
        mgr = PolicyManager()
        mgr.create(name="temp", policy_type=PolicyType.ACCESS)
        assert mgr.delete("temp") is True

    def test_list_by_type(self) -> None:
        mgr = PolicyManager()
        access_policies = mgr.list_by_type(PolicyType.ACCESS)
        assert len(access_policies) >= 1

    def test_to_dict(self) -> None:
        p = EnterprisePolicy(name="test", policy_type=PolicyType.ACCESS, rules=[{"a": 1}])
        d = p.to_dict()
        assert d["name"] == "test"
        assert len(d["rules"]) == 1


# ===== Audit =====

class TestAudit:
    def test_record_event(self) -> None:
        mgr = AuditManager()
        event = mgr.record(AuditEventType.AUTHENTICATION, actor="user1", details={"action": "login"})
        assert event.actor == "user1"
        assert event.event_type == AuditEventType.AUTHENTICATION

    def test_get_event(self) -> None:
        mgr = AuditManager()
        event = mgr.record(AuditEventType.AUTHORIZATION, actor="user1")
        fetched = mgr.get(event.id)
        assert fetched is not None

    def test_query_by_type(self) -> None:
        mgr = AuditManager()
        mgr.record(AuditEventType.AUTHENTICATION, actor="user1")
        mgr.record(AuditEventType.AUTHORIZATION, actor="user2")
        mgr.record(AuditEventType.API_USAGE, actor="user1")
        results = mgr.query(event_type=AuditEventType.AUTHENTICATION)
        assert len(results) == 1

    def test_query_by_actor(self) -> None:
        mgr = AuditManager()
        mgr.record(AuditEventType.API_USAGE, actor="user1")
        mgr.record(AuditEventType.API_USAGE, actor="user2")
        results = mgr.query(actor="user1")
        assert len(results) == 1

    def test_count(self) -> None:
        mgr = AuditManager()
        mgr.record(AuditEventType.API_USAGE, actor="user1")
        mgr.record(AuditEventType.API_USAGE, actor="user2")
        assert mgr.count() == 2

    def test_count_by_type(self) -> None:
        mgr = AuditManager()
        mgr.record(AuditEventType.AUTHENTICATION, actor="u1")
        mgr.record(AuditEventType.AUTHENTICATION, actor="u1")
        mgr.record(AuditEventType.API_USAGE, actor="u1")
        counts = mgr.count_by_type()
        assert counts["authentication"] == 2
        assert counts["api_usage"] == 1

    def test_max_events(self) -> None:
        mgr = AuditManager(max_events=5)
        for i in range(10):
            mgr.record(AuditEventType.API_USAGE, actor=f"user{i}")
        assert mgr.count() == 5

    def test_clear(self) -> None:
        mgr = AuditManager()
        mgr.record(AuditEventType.API_USAGE, actor="u1")
        mgr.clear()
        assert mgr.count() == 0

    def test_to_dict(self) -> None:
        e = AuditEvent(event_type=AuditEventType.CONFIGURATION, actor="admin", details={"key": "val"}, ip_address="127.0.0.1")
        d = e.to_dict()
        assert d["actor"] == "admin"
        assert d["ip_address"] == "127.0.0.1"


# ===== Licensing =====

class TestLicensing:
    def test_default_edition(self) -> None:
        mgr = LicensingManager()
        assert mgr.get_edition() == "community"

    def test_set_license(self) -> None:
        mgr = LicensingManager()
        license_obj = License(edition=LicenseEdition.ENTERPRISE, org_id="org1")
        mgr.set_license(license_obj, "org1")
        assert mgr.get_edition("org1") == "enterprise"

    def test_feature_available(self) -> None:
        mgr = LicensingManager()
        license_obj = License(edition=LicenseEdition.ENTERPRISE)
        mgr.set_license(license_obj, "org1")
        assert mgr.is_feature_available("rbac", "org1") is True
        assert mgr.is_feature_available("white_label", "org1") is False

    def test_validate_license(self) -> None:
        mgr = LicensingManager()
        result = mgr.validate_license()
        assert result["valid"] is True
        assert result["edition"] == "community"

    def test_get_capabilities(self) -> None:
        mgr = LicensingManager()
        caps = mgr.get_capabilities()
        assert "basic_agents" in caps

    def test_to_dict(self) -> None:
        l = License(edition=LicenseEdition.PROFESSIONAL, org_id="org1")
        d = l.to_dict()
        assert d["edition"] == "professional"
        assert d["valid"] is True

    def test_expired_license(self) -> None:
        import time
        l = License(edition=LicenseEdition.PROFESSIONAL, expires_at=time.time() - 100)
        assert l.is_valid() is False
        assert l.has_feature("basic_agents") is False

    def test_community_features(self) -> None:
        l = License(edition=LicenseEdition.COMMUNITY)
        assert l.has_feature("basic_agents") is True
        assert l.has_feature("rbac") is False

    def test_unlimited_features(self) -> None:
        l = License(edition=LicenseEdition.UNLIMITED)
        assert l.has_feature("white_label") is True
        assert l.has_feature("dedicated_support") is True


# ===== Billing =====

class TestBilling:
    @pytest.mark.asyncio
    async def test_get_subscription_none(self) -> None:
        mgr = BillingManager()
        result = await mgr.get_subscription("org1")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_subscription(self) -> None:
        mgr = BillingManager()
        sub = await mgr.create_subscription("org1", plan="professional", status=BillingStatus.ACTIVE)
        assert sub.plan == "professional"
        assert sub.org_id == "org1"

    @pytest.mark.asyncio
    async def test_record_usage(self) -> None:
        mgr = BillingManager()
        record = await mgr.record_usage("org1", metric="api_calls", quantity=100)
        assert record.quantity == 100

    @pytest.mark.asyncio
    async def test_get_usage(self) -> None:
        mgr = BillingManager()
        await mgr.record_usage("org1", "api_calls", 50)
        await mgr.record_usage("org1", "api_calls", 30)
        usage = await mgr.get_usage("org1")
        assert usage["totals"]["api_calls"] == 80

    @pytest.mark.asyncio
    async def test_list_invoices(self) -> None:
        mgr = BillingManager()
        await mgr.create_invoice("org1", amount=100.0)
        invoices = await mgr.list_invoices("org1")
        assert len(invoices) == 1
        assert invoices[0]["amount"] == 100.0

    def test_subscription_to_dict(self) -> None:
        s = Subscription(org_id="org1", plan="enterprise", status=BillingStatus.TRIAL)
        d = s.to_dict()
        assert d["plan"] == "enterprise"
        assert d["status"] == "trial"

    def test_usage_record_to_dict(self) -> None:
        u = UsageRecord(org_id="org1", metric="storage", quantity=1024)
        d = u.to_dict()
        assert d["metric"] == "storage"
        assert d["quantity"] == 1024

    def test_invoice_to_dict(self) -> None:
        i = Invoice(org_id="org1", amount=250.0, currency="EUR")
        d = i.to_dict()
        assert d["amount"] == 250.0
        assert d["currency"] == "EUR"

    @pytest.mark.asyncio
    async def test_count_subscriptions(self) -> None:
        mgr = BillingManager()
        await mgr.create_subscription("org1")
        await mgr.create_subscription("org2")
        assert mgr.count_subscriptions() == 2


# ===== Quota =====

class TestQuota:
    def test_default_quotas(self) -> None:
        mgr = QuotaManager()
        q = mgr.get_quota("default", QuotaType.USERS)
        assert q is not None
        assert q.limit == 10

    def test_consume_quota(self) -> None:
        mgr = QuotaManager()
        assert mgr.consume("org1", QuotaType.USERS, 5) is True
        q = mgr.get_quota("org1", QuotaType.USERS)
        assert q.used == 5

    def test_exceed_quota(self) -> None:
        mgr = QuotaManager()
        assert mgr.consume("org1", QuotaType.USERS, 10) is True
        assert mgr.consume("org1", QuotaType.USERS, 1) is False

    def test_check_quota(self) -> None:
        mgr = QuotaManager()
        result = mgr.check("org1", QuotaType.USERS, 1)
        assert result["allowed"] is True

    def test_check_exceeded(self) -> None:
        mgr = QuotaManager()
        mgr.consume("org1", QuotaType.USERS, 10)
        result = mgr.check("org1", QuotaType.USERS, 1)
        assert result["allowed"] is False
        assert result["reason"] == "quota_exceeded"

    def test_release_quota(self) -> None:
        mgr = QuotaManager()
        mgr.consume("org1", QuotaType.USERS, 5)
        mgr.release("org1", QuotaType.USERS, 3)
        q = mgr.get_quota("org1", QuotaType.USERS)
        assert q.used == 2

    def test_set_limit(self) -> None:
        mgr = QuotaManager()
        mgr.set_limit("org1", QuotaType.USERS, 50)
        q = mgr.get_quota("org1", QuotaType.USERS)
        assert q.limit == 50

    def test_get_all(self) -> None:
        mgr = QuotaManager()
        all_q = mgr.get_all("org1")
        assert "users" in all_q
        assert "agents" in all_q

    def test_get_usage_summary(self) -> None:
        mgr = QuotaManager()
        mgr.consume("org1", QuotaType.USERS, 5)
        summary = mgr.get_usage_summary("org1")
        assert summary["total_used"] > 0

    def test_reset(self) -> None:
        mgr = QuotaManager()
        mgr.consume("org1", QuotaType.USERS, 5)
        mgr.reset("org1", QuotaType.USERS)
        q = mgr.get_quota("org1", QuotaType.USERS)
        assert q.used == 0

    def test_quota_to_dict(self) -> None:
        q = Quota(QuotaType.USERS, 10)
        q.used = 3
        d = q.to_dict()
        assert d["limit"] == 10
        assert d["used"] == 3
        assert d["remaining"] == 7

    def test_quota_is_exceeded(self) -> None:
        q = Quota(QuotaType.USERS, 2)
        q.used = 2
        assert q.is_exceeded() is True

    def test_quota_utilization(self) -> None:
        q = Quota(QuotaType.USERS, 10)
        q.used = 5
        assert q.utilization == 0.5


# ===== Administration =====

class TestAdministration:
    def test_get_settings(self) -> None:
        mgr = AdministrationManager()
        settings = mgr.get_all_settings()
        assert "enforce_sso" in settings
        assert "session_timeout" in settings

    def test_set_setting(self) -> None:
        mgr = AdministrationManager()
        mgr.set_setting("custom_key", "custom_value", actor="admin")
        assert mgr.get_setting("custom_key") == "custom_value"

    def test_recorded_actions(self) -> None:
        mgr = AdministrationManager()
        mgr.set_setting("k1", "v1", actor="admin")
        actions = mgr.get_actions()
        assert len(actions) == 1
        assert actions[0]["actor"] == "admin"

    def test_count_actions(self) -> None:
        mgr = AdministrationManager()
        mgr.set_setting("k1", "v1")
        mgr.set_setting("k2", "v2")
        assert mgr.count_actions() == 2

    def test_get_audit_event_type(self) -> None:
        mgr = AdministrationManager()
        assert mgr.get_audit_event_type() == AuditEventType.ADMINISTRATIVE


# ===== Lifecycle =====

class TestLifecycle:
    def test_initial_state(self) -> None:
        lc = EnterpriseLifecycle()
        assert lc.state == EnterpriseState.REGISTERED

    def test_valid_transitions(self) -> None:
        lc = EnterpriseLifecycle()
        assert lc.transition(EnterpriseState.INITIALIZED) is True
        assert lc.transition(EnterpriseState.READY) is True
        assert lc.transition(EnterpriseState.ACTIVE) is True
        assert lc.state == EnterpriseState.ACTIVE

    def test_invalid_transition(self) -> None:
        lc = EnterpriseLifecycle()
        assert lc.transition(EnterpriseState.ACTIVE) is False

    def test_suspended_to_active(self) -> None:
        lc = EnterpriseLifecycle()
        lc.transition(EnterpriseState.INITIALIZED)
        lc.transition(EnterpriseState.READY)
        lc.transition(EnterpriseState.ACTIVE)
        assert lc.transition(EnterpriseState.SUSPENDED) is True
        assert lc.transition(EnterpriseState.ACTIVE) is True

    def test_archive_from_active(self) -> None:
        lc = EnterpriseLifecycle()
        lc.transition(EnterpriseState.INITIALIZED)
        lc.transition(EnterpriseState.READY)
        lc.transition(EnterpriseState.ACTIVE)
        assert lc.transition(EnterpriseState.ARCHIVED) is True
        assert lc.state == EnterpriseState.ARCHIVED

    def test_delete_from_archived(self) -> None:
        lc = EnterpriseLifecycle()
        lc.transition(EnterpriseState.INITIALIZED)
        lc.transition(EnterpriseState.READY)
        lc.transition(EnterpriseState.ARCHIVED)
        assert lc.transition(EnterpriseState.DELETED) is True
        assert lc.state == EnterpriseState.DELETED

    def test_cannot_transition_from_deleted(self) -> None:
        lc = EnterpriseLifecycle()
        lc.transition(EnterpriseState.INITIALIZED)
        lc.transition(EnterpriseState.DELETED)
        assert lc.transition(EnterpriseState.READY) is False

    def test_is_running(self) -> None:
        lc = EnterpriseLifecycle()
        assert lc.is_running() is False
        lc.transition(EnterpriseState.INITIALIZED)
        lc.transition(EnterpriseState.READY)
        assert lc.is_running() is True

    def test_get_status(self) -> None:
        lc = EnterpriseLifecycle()
        status = lc.get_status()
        assert "state" in status
        assert "uptime_seconds" in status

    def test_get_history(self) -> None:
        lc = EnterpriseLifecycle()
        lc.transition(EnterpriseState.INITIALIZED)
        history = lc.get_history()
        assert len(history) == 1
        assert history[0]["to"] == "initialized"

    def test_transition_reason(self) -> None:
        lc = EnterpriseLifecycle()
        lc.transition(EnterpriseState.INITIALIZED, reason="startup")
        history = lc.get_history()
        assert history[0]["reason"] == "startup"


# ===== Repository & Persistence =====

class TestRepository:
    def test_repository_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            EnterpriseRepository()


class TestPersistence:
    @pytest.mark.asyncio
    async def test_save_and_get(self) -> None:
        repo = InMemoryEnterpriseRepository()
        await repo.save("orgs", "o1", {"name": "Org1"})
        result = await repo.get("orgs", "o1")
        assert result is not None
        assert result["name"] == "Org1"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self) -> None:
        repo = InMemoryEnterpriseRepository()
        result = await repo.get("orgs", "missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_list(self) -> None:
        repo = InMemoryEnterpriseRepository()
        await repo.save("orgs", "o1", {"name": "O1"})
        await repo.save("orgs", "o2", {"name": "O2"})
        items = await repo.list("orgs")
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        repo = InMemoryEnterpriseRepository()
        await repo.save("orgs", "o1", {"name": "O1"})
        assert await repo.delete("orgs", "o1") is True
        assert await repo.get("orgs", "o1") is None

    @pytest.mark.asyncio
    async def test_count(self) -> None:
        repo = InMemoryEnterpriseRepository()
        await repo.save("orgs", "o1", {"a": 1})
        await repo.save("orgs", "o2", {"a": 2})
        assert await repo.count("orgs") == 2

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        repo = InMemoryEnterpriseRepository()
        await repo.save("orgs", "o1", {"a": 1})
        repo.clear()
        assert await repo.count("orgs") == 0


# ===== Metrics =====

class TestMetrics:
    def test_start(self) -> None:
        mc = EnterpriseMetricsCollector()
        mc.start()
        s = mc.snapshot()
        assert s.uptime_seconds >= 0

    def test_record_organization(self) -> None:
        mc = EnterpriseMetricsCollector()
        mc.start()
        mc.record_organization_created()
        mc.record_organization_created()
        mc.record_organization_deleted()
        s = mc.snapshot()
        assert s.organizations == 1

    def test_record_tenant(self) -> None:
        mc = EnterpriseMetricsCollector()
        mc.start()
        mc.record_tenant_created()
        s = mc.snapshot()
        assert s.tenants == 1

    def test_record_workspace(self) -> None:
        mc = EnterpriseMetricsCollector()
        mc.start()
        mc.record_workspace_created()
        mc.record_workspace_deleted()
        s = mc.snapshot()
        assert s.workspaces == 0

    def test_record_permission_check(self) -> None:
        mc = EnterpriseMetricsCollector()
        mc.start()
        mc.record_permission_check()
        mc.record_permission_check()
        s = mc.snapshot()
        assert s.permission_checks == 2

    def test_record_audit_event(self) -> None:
        mc = EnterpriseMetricsCollector()
        mc.start()
        mc.record_audit_event()
        s = mc.snapshot()
        assert s.audit_events == 1

    def test_record_quota_usage(self) -> None:
        mc = EnterpriseMetricsCollector()
        mc.start()
        mc.record_quota_usage("users", 5)
        s = mc.snapshot()
        assert s.quota_usage["users"] == 5

    def test_reset(self) -> None:
        mc = EnterpriseMetricsCollector()
        mc.record_organization_created()
        mc.record_permission_check()
        mc.reset()
        s = mc.snapshot()
        assert s.organizations == 0
        assert s.permission_checks == 0

    def test_to_dict(self) -> None:
        s = EnterpriseMetrics(organizations=3, tenants=2, uptime_seconds=100.0)
        d = s.to_dict()
        assert d["organizations"] == 3
        assert d["uptime_seconds"] == 100.0


# ===== Tracing =====

class TestTracing:
    def test_start_trace(self) -> None:
        tracer = EnterpriseTracer()
        trace_id = tracer.start_trace("test_op")
        assert len(trace_id) == 12

    def test_finish_trace(self) -> None:
        tracer = EnterpriseTracer()
        trace_id = tracer.start_trace("test_op")
        tracer.finish_trace(trace_id, status="completed")
        trace = tracer.get_trace(trace_id)
        assert trace is not None
        assert trace["status"] == "completed"
        assert trace["duration_ms"] is not None

    def test_finish_trace_with_error(self) -> None:
        tracer = EnterpriseTracer()
        trace_id = tracer.start_trace("test_op")
        tracer.finish_trace(trace_id, status="error", error="something went wrong")
        trace = tracer.get_trace(trace_id)
        assert trace["error"] == "something went wrong"

    def test_get_traces(self) -> None:
        tracer = EnterpriseTracer()
        tracer.start_trace("op1")
        tracer.start_trace("op2")
        traces = tracer.get_traces(limit=10)
        assert len(traces) == 2

    def test_max_traces(self) -> None:
        tracer = EnterpriseTracer(max_traces=3)
        for i in range(5):
            tracer.start_trace(f"op{i}")
        assert tracer.count() == 3

    def test_clear(self) -> None:
        tracer = EnterpriseTracer()
        tracer.start_trace("op1")
        tracer.clear()
        assert tracer.count() == 0

    def test_get_trace_nonexistent(self) -> None:
        tracer = EnterpriseTracer()
        assert tracer.get_trace("missing") is None


# ===== Concurrency =====

class TestConcurrency:
    def test_concurrent_organization_creation(self) -> None:
        mgr = OrganizationManager()
        errors: list[str] = []

        def create_org(i: int) -> None:
            try:
                mgr.create(name=f"Org{i}")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=create_org, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert mgr.count() == 50

    def test_concurrent_membership_operations(self) -> None:
        mgr = MembershipManager()
        errors: list[str] = []

        def add_member(i: int) -> None:
            try:
                mgr.add_member(user_id=f"u{i}", team_id=f"t{i % 5}")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=add_member, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert mgr.count() == 50

    def test_concurrent_quota_operations(self) -> None:
        mgr = QuotaManager()
        results: list[bool] = []

        def consume(i: int) -> None:
            results.append(mgr.consume("org1", QuotaType.USERS, 1))

        threads = [threading.Thread(target=consume, args=(i,)) for i in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 15
        assert sum(results) == 10

    def test_concurrent_permission_checks(self) -> None:
        mgr = PermissionManager()
        mgr.assign(subject="user1", role="viewer", scope=PermissionScope.SYSTEM)
        results: list[bool] = []

        def check_perm() -> None:
            results.append(mgr.check(subject="user1", resource="r", action="read"))

        threads = [threading.Thread(target=check_perm) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert all(r is True for r in results)

    def test_concurrent_audit_recording(self) -> None:
        mgr = AuditManager()

        def record(i: int) -> None:
            mgr.record(AuditEventType.API_USAGE, actor=f"user{i}")

        threads = [threading.Thread(target=record, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert mgr.count() == 30


# ===== Manager =====

class TestEnterpriseManager:
    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        mgr = EnterpriseManager()
        await mgr.start()
        assert mgr.is_running() is True
        await mgr.shutdown()
        assert mgr.is_running() is False

    @pytest.mark.asyncio
    async def test_create_organization(self) -> None:
        mgr = EnterpriseManager()
        await mgr.start()
        org = await mgr.create_organization(name="TestOrg", owner_id="user1")
        assert org["name"] == "TestOrg"

    @pytest.mark.asyncio
    async def test_create_tenant(self) -> None:
        mgr = EnterpriseManager()
        await mgr.start()
        tenant = await mgr.create_tenant(org_id="org1", name="Tenant1")
        assert tenant["org_id"] == "org1"

    @pytest.mark.asyncio
    async def test_create_workspace(self) -> None:
        mgr = EnterpriseManager()
        await mgr.start()
        ws = await mgr.create_workspace(org_id="org1", name="Workspace1")
        assert ws["name"] == "Workspace1"

    @pytest.mark.asyncio
    async def test_create_team(self) -> None:
        mgr = EnterpriseManager()
        await mgr.start()
        team = await mgr.create_team(org_id="org1", name="Team1")
        assert team["name"] == "Team1"

    @pytest.mark.asyncio
    async def test_list_roles(self) -> None:
        mgr = EnterpriseManager()
        roles = await mgr.list_roles()
        assert len(roles) == 7

    @pytest.mark.asyncio
    async def test_create_role(self) -> None:
        mgr = EnterpriseManager()
        role = await mgr.create_role(name="custom", permissions=["read"])
        assert role["name"] == "custom"

    @pytest.mark.asyncio
    async def test_list_policies(self) -> None:
        mgr = EnterpriseManager()
        policies = await mgr.list_policies()
        assert len(policies) >= 4

    def test_get_status(self) -> None:
        mgr = EnterpriseManager()
        status = mgr.get_status()
        assert "state" in status
        assert "edition" in status

    def test_get_metrics(self) -> None:
        mgr = EnterpriseManager()
        metrics = mgr.get_metrics()
        assert "organizations" in metrics

    def test_get_traces(self) -> None:
        mgr = EnterpriseManager()
        traces = mgr.get_traces()
        assert isinstance(traces, list)

    @pytest.mark.asyncio
    async def test_get_license(self) -> None:
        mgr = EnterpriseManager()
        license_info = await mgr.get_license()
        assert license_info["edition"] == "community"

    @pytest.mark.asyncio
    async def test_get_quotas(self) -> None:
        mgr = EnterpriseManager()
        quotas = await mgr.get_quotas()
        assert "users" in quotas

    @pytest.mark.asyncio
    async def test_get_audit_events(self) -> None:
        mgr = EnterpriseManager()
        events = await mgr.get_audit_events()
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_check_permission(self) -> None:
        mgr = EnterpriseManager()
        await mgr.start()
        result = await mgr.check_permission(subject="user1", resource="r", action="read")
        assert result is False

    @pytest.mark.asyncio
    async def test_create_policy(self) -> None:
        mgr = EnterpriseManager()
        policy = await mgr.create_policy(name="test_policy", policy_type=PolicyType.SECURITY)
        assert policy["name"] == "test_policy"


# ===== Engine =====

class TestEnterpriseEngine:
    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        engine = EnterpriseEngine()
        await engine.start()
        assert engine.is_running() is True
        await engine.shutdown()
        assert engine.is_running() is False

    def test_get_status(self) -> None:
        engine = EnterpriseEngine()
        status = engine.get_status()
        assert "state" in status

    def test_get_metrics(self) -> None:
        engine = EnterpriseEngine()
        metrics = engine.get_metrics()
        assert "organizations" in metrics

    def test_get_traces(self) -> None:
        engine = EnterpriseEngine()
        traces = engine.get_traces()
        assert isinstance(traces, list)

    @pytest.mark.asyncio
    async def test_create_organization(self) -> None:
        engine = EnterpriseEngine()
        await engine.start()
        org = await engine.create_organization(name="Acme", owner_id="u1")
        assert org["name"] == "Acme"

    @pytest.mark.asyncio
    async def test_list_organizations(self) -> None:
        engine = EnterpriseEngine()
        await engine.start()
        await engine.create_organization(name="O1")
        orgs = await engine.list_organizations()
        assert len(orgs) == 1

    @pytest.mark.asyncio
    async def test_create_tenant(self) -> None:
        engine = EnterpriseEngine()
        await engine.start()
        t = await engine.create_tenant(org_id="org1", name="Tenant1")
        assert t["name"] == "Tenant1"

    @pytest.mark.asyncio
    async def test_list_tenants(self) -> None:
        engine = EnterpriseEngine()
        await engine.start()
        tenants = await engine.list_tenants()
        assert isinstance(tenants, list)

    @pytest.mark.asyncio
    async def test_create_workspace(self) -> None:
        engine = EnterpriseEngine()
        await engine.start()
        ws = await engine.create_workspace(org_id="org1", name="WS1")
        assert ws["name"] == "WS1"

    @pytest.mark.asyncio
    async def test_list_workspaces(self) -> None:
        engine = EnterpriseEngine()
        await engine.start()
        wss = await engine.list_workspaces()
        assert isinstance(wss, list)

    @pytest.mark.asyncio
    async def test_create_team(self) -> None:
        engine = EnterpriseEngine()
        await engine.start()
        team = await engine.create_team(org_id="org1", name="Dev")
        assert team["name"] == "Dev"

    @pytest.mark.asyncio
    async def test_list_teams(self) -> None:
        engine = EnterpriseEngine()
        await engine.start()
        teams = await engine.list_teams()
        assert isinstance(teams, list)

    @pytest.mark.asyncio
    async def test_list_roles(self) -> None:
        engine = EnterpriseEngine()
        roles = await engine.list_roles()
        assert len(roles) == 7

    @pytest.mark.asyncio
    async def test_create_role(self) -> None:
        engine = EnterpriseEngine()
        role = await engine.create_role(name="custom_role", permissions=["read", "write"])
        assert role["name"] == "custom_role"

    @pytest.mark.asyncio
    async def test_check_permission(self) -> None:
        engine = EnterpriseEngine()
        await engine.start()
        result = await engine.check_permission(subject="u1", resource="r", action="read")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_permissions(self) -> None:
        engine = EnterpriseEngine()
        perms = await engine.list_permissions()
        assert isinstance(perms, list)

    @pytest.mark.asyncio
    async def test_list_policies(self) -> None:
        engine = EnterpriseEngine()
        policies = await engine.list_policies()
        assert len(policies) >= 4

    @pytest.mark.asyncio
    async def test_create_policy(self) -> None:
        engine = EnterpriseEngine()
        p = await engine.create_policy(name="test_pol", policy_type="execution")
        assert p["name"] == "test_pol"

    @pytest.mark.asyncio
    async def test_get_license(self) -> None:
        engine = EnterpriseEngine()
        lic = await engine.get_license()
        assert lic["edition"] == "community"

    @pytest.mark.asyncio
    async def test_get_quotas(self) -> None:
        engine = EnterpriseEngine()
        q = await engine.get_quotas()
        assert "users" in q

    @pytest.mark.asyncio
    async def test_get_audit_events(self) -> None:
        engine = EnterpriseEngine()
        events = await engine.get_audit_events()
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_delete_organization(self) -> None:
        engine = EnterpriseEngine()
        await engine.start()
        org = await engine.create_organization(name="ToDelete")
        result = await engine.delete_organization(org["id"])
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_tenant(self) -> None:
        engine = EnterpriseEngine()
        await engine.start()
        t = await engine.create_tenant(org_id="org1", name="ToDelete")
        result = await engine.delete_tenant(t["id"])
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_workspace(self) -> None:
        engine = EnterpriseEngine()
        await engine.start()
        ws = await engine.create_workspace(org_id="org1", name="ToDelete")
        result = await engine.delete_workspace(ws["id"])
        assert result is True


# ===== Factory =====

class TestFactory:
    def test_create(self) -> None:
        engine = EnterpriseFactory.create()
        assert engine is not None
        assert isinstance(engine, EnterpriseEngine)

    def test_create_default(self) -> None:
        engine = EnterpriseFactory.create_default()
        assert engine is not None

    def test_get_or_create_singleton(self) -> None:
        EnterpriseFactory.reset()
        e1 = EnterpriseFactory.get_or_create()
        e2 = EnterpriseFactory.get_or_create()
        assert e1 is e2

    def test_reset(self) -> None:
        EnterpriseFactory.reset()
        e1 = EnterpriseFactory.get_or_create()
        EnterpriseFactory.reset()
        e2 = EnterpriseFactory.get_or_create()
        assert e1 is not e2

    def test_create_with_kwargs(self) -> None:
        engine = EnterpriseFactory.create(custom_attr="test")
        assert engine is not None


# ===== Edge Cases =====

class TestEdgeCases:
    def test_organization_metadata(self) -> None:
        mgr = OrganizationManager()
        org = mgr.create(name="Test", metadata={"nested": {"key": "value"}})
        assert org.metadata["nested"]["key"] == "value"

    def test_tenant_config_update(self) -> None:
        mgr = TenantManager()
        t = mgr.create(org_id="org1", name="T1", config={"a": 1})
        mgr.update_config(t.id, {"b": 2})
        assert mgr.get(t.id).config == {"a": 1, "b": 2}

    def test_workspace_full_lifecycle(self) -> None:
        mgr = WorkspaceManager()
        ws = mgr.create(org_id="org1", name="W1")
        assert ws.status == WorkspaceStatus.ACTIVE
        mgr.archive(ws.id)
        assert mgr.get(ws.id).status == WorkspaceStatus.ARCHIVED

    def test_team_hierarchy(self) -> None:
        mgr = TeamManager()
        parent = mgr.create(org_id="org1", name="Parent")
        child = mgr.create(org_id="org1", name="Child", parent_id=parent.id)
        children = mgr.list_children(parent.id)
        assert len(children) == 1
        assert children[0].id == child.id

    def test_membership_role_update(self) -> None:
        mgr = MembershipManager()
        m = mgr.add_member(user_id="u1", team_id="t1", role=MembershipRole.MEMBER)
        mgr.update_role(m.id, MembershipRole.OWNER)
        assert mgr.get(m.id).role == MembershipRole.OWNER

    def test_role_permission_check(self) -> None:
        mgr = RoleManager()
        assert mgr.has_permission("owner", "anything") is True
        assert mgr.has_permission("viewer", "read") is True
        assert mgr.has_permission("viewer", "admin") is False

    def test_permission_scope_check(self) -> None:
        mgr = PermissionManager()
        mgr.assign(subject="u1", role="admin", scope=PermissionScope.ORGANIZATION, scope_id="org1")
        assert mgr.check(subject="u1", resource="r", action="admin", scope=PermissionScope.ORGANIZATION, scope_id="org1") is True
        assert mgr.check(subject="u1", resource="r", action="admin", scope=PermissionScope.ORGANIZATION, scope_id="org2") is False

    def test_quota_all_types(self) -> None:
        mgr = QuotaManager()
        for qt in QuotaType:
            q = mgr.get_quota("default", qt)
            assert q is not None

    def test_audit_query_combined(self) -> None:
        mgr = AuditManager()
        mgr.record(AuditEventType.AUTHENTICATION, actor="user1", resource="login")
        mgr.record(AuditEventType.AUTHENTICATION, actor="user2", resource="login")
        mgr.record(AuditEventType.API_USAGE, actor="user1")
        results = mgr.query(event_type=AuditEventType.AUTHENTICATION, actor="user1")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_billing_usage_per_org(self) -> None:
        mgr = BillingManager()
        await mgr.record_usage("org1", "api_calls", 10)
        await mgr.record_usage("org2", "api_calls", 20)
        usage1 = await mgr.get_usage("org1")
        usage2 = await mgr.get_usage("org2")
        assert usage1["totals"]["api_calls"] == 10
        assert usage2["totals"]["api_calls"] == 20

    def test_licensing_feature_gating(self) -> None:
        mgr = LicensingManager()
        community = License(edition=LicenseEdition.COMMUNITY)
        enterprise = License(edition=LicenseEdition.ENTERPRISE)
        mgr.set_license(community, "org_community")
        mgr.set_license(enterprise, "org_enterprise")
        assert mgr.is_feature_available("rbac", "org_community") is False
        assert mgr.is_feature_available("rbac", "org_enterprise") is True

    def test_quota_release(self) -> None:
        mgr = QuotaManager()
        mgr.consume("org1", QuotaType.USERS, 8)
        mgr.release("org1", QuotaType.USERS, 3)
        q = mgr.get_quota("org1", QuotaType.USERS)
        assert q.used == 5
        assert q.remaining == 5

    def test_admin_settings_persistence(self) -> None:
        mgr = AdministrationManager()
        mgr.set_setting("key1", "value1", actor="admin")
        mgr.set_setting("key2", "value2", actor="admin")
        assert mgr.get_setting("key1") == "value1"
        assert mgr.get_setting("key2") == "value2"

    def test_engine_manager_property(self) -> None:
        engine = EnterpriseEngine()
        assert engine.manager is not None
        assert isinstance(engine.manager, EnterpriseManager)
