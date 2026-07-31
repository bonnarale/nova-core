"""Enums for the Deployment subsystem."""

from __future__ import annotations

from enum import Enum


class DeployEnvironment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class DeployState(str, Enum):
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    FAILED = "failed"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class SecretSource(str, Enum):
    ENVIRONMENT = "environment"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    VAULT = "vault"
    FILE = "file"


class ConfigFormat(str, Enum):
    JSON = "json"
    YAML = "yaml"
    ENV = "env"
    TOML = "toml"
