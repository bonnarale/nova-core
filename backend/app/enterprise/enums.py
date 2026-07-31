"""Enterprise enums and state definitions."""

from __future__ import annotations

from enum import Enum


class EnterpriseState(str, Enum):
    """Lifecycle states for the enterprise layer."""
    REGISTERED = "registered"
    INITIALIZED = "initialized"
    READY = "ready"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    DELETED = "deleted"


class OrganizationStatus(str, Enum):
    """Organization lifecycle status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    DELETED = "deleted"


class TenantStatus(str, Enum):
    """Tenant lifecycle status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class WorkspaceStatus(str, Enum):
    """Workspace lifecycle status."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class TeamStatus(str, Enum):
    """Team status."""
    ACTIVE = "active"
    DISSOLVED = "dissolved"


class MembershipRole(str, Enum):
    """Roles within a team."""
    OWNER = "owner"
    LEAD = "lead"
    MEMBER = "member"
    OBSERVER = "observer"


class EnterpriseRole(str, Enum):
    """Default enterprise roles (RBAC)."""
    OWNER = "owner"
    ADMINISTRATOR = "administrator"
    MANAGER = "manager"
    DEVELOPER = "developer"
    OPERATOR = "operator"
    ANALYST = "analyst"
    VIEWER = "viewer"


class PermissionScope(str, Enum):
    """Permission scope levels."""
    SYSTEM = "system"
    ORGANIZATION = "organization"
    WORKSPACE = "workspace"
    RESOURCE = "resource"
    CUSTOM = "custom"


class PermissionAction(str, Enum):
    """Permission actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    MANAGE = "manage"
    ADMIN = "admin"
    SHARE = "share"


class PolicyType(str, Enum):
    """Enterprise policy types."""
    ACCESS = "access"
    EXECUTION = "execution"
    SECURITY = "security"
    RETENTION = "retention"


class AuditEventType(str, Enum):
    """Types of audit events."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    API_USAGE = "api_usage"
    WORKFLOW_EXECUTION = "workflow_execution"
    ADMINISTRATIVE = "administrative"
    CONFIGURATION = "configuration"


class LicenseEdition(str, Enum):
    """License editions."""
    COMMUNITY = "community"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


class QuotaType(str, Enum):
    """Quota resource types."""
    USERS = "users"
    AGENTS = "agents"
    WORKFLOWS = "workflows"
    EXECUTIONS = "executions"
    STORAGE = "storage"
    API_REQUESTS = "api_requests"
    VECTOR_MEMORY = "vector_memory"
    PLUGINS = "plugins"


class BillingStatus(str, Enum):
    """Billing subscription status."""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIAL = "trial"
    EXPIRED = "expired"
