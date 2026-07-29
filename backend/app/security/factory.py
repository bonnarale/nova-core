"""Security factory — creates and wires all security components."""

from __future__ import annotations

import logging
from typing import Any

from app.security.engine import SecurityEngine
from app.security.headers import SecurityConfig

logger = logging.getLogger(__name__)


class SecurityFactory:
    """Factory that creates all security components and wires them together."""

    @staticmethod
    def create_engine(config: SecurityConfig | None = None) -> SecurityEngine:
        """Create a fully wired SecurityEngine instance."""
        engine = SecurityEngine(config=config)
        logger.info("SecurityFactory created engine")
        return engine

    @staticmethod
    def create_engine_with_components(config: SecurityConfig | None = None) -> dict[str, Any]:
        """Create engine and return all components."""
        engine = SecurityFactory.create_engine(config)
        return {
            "engine": engine,
            "config": engine.config,
            "tokens": engine.tokens,
            "passwords": engine.passwords,
            "rbac": engine.rbac,
            "sessions": engine.sessions,
            "audit": engine.audit,
            "api_keys": engine.api_keys,
            "rate_limiter": engine.rate_limiter,
            "ip_filter": engine.ip_filter,
            "headers": engine.headers,
            "policy_engine": engine.policy_engine,
            "repository": engine.repository,
        }
