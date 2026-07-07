"""Kernel configuration and settings."""

import logging
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class KernelSettings(BaseSettings):
    """Configuration for the kernel execution engine."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="KERNEL_"
    )

    max_concurrent_tasks: int = Field(default=10, alias="MAX_CONCURRENT_TASKS")
    task_timeout_seconds: int = Field(default=300, alias="TASK_TIMEOUT_SECONDS")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    retry_delay_seconds: float = Field(default=1.0, alias="RETRY_DELAY_SECONDS")
    enable_event_logging: bool = Field(default=True, alias="ENABLE_EVENT_LOGGING")
    default_agent_timeout: int = Field(default=60, alias="DEFAULT_AGENT_TIMEOUT")


def get_kernel_settings() -> KernelSettings:
    """Get kernel settings instance."""
    return KernelSettings()