"""Enterprise Pydantic schemas for API requests and responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., description="Organization name")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class WorkspaceCreate(BaseModel):
    name: str = Field(..., description="Workspace name")
    org_id: str = Field(..., description="Organization ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TeamCreate(BaseModel):
    name: str = Field(..., description="Team name")
    org_id: str = Field(..., description="Organization ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RoleCreate(BaseModel):
    name: str = Field(..., description="Role name")
    permissions: list[str] = Field(default_factory=list, description="Permission IDs")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class PolicyCreate(BaseModel):
    name: str = Field(..., description="Policy name")
    policy_type: str = Field(..., description="Policy type")
    rules: list[dict[str, Any]] = Field(default_factory=list, description="Policy rules")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EnterpriseStatusResponse(BaseModel):
    state: str
    uptime_seconds: float
    total_organizations: int
    total_tenants: int
    total_workspaces: int
    total_users: int
    edition: str


class EnterpriseMetricsResponse(BaseModel):
    organizations: int
    tenants: int
    workspaces: int
    users: int
    role_assignments: int
    permission_checks: int
    audit_events: int
    quota_usage: dict[str, Any]
