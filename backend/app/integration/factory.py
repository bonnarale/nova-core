"""Factory for creating configured integration engine instances."""

from __future__ import annotations

import logging
from typing import Any

from app.integration.engine import IntegrationEngine

logger = logging.getLogger(__name__)


class IntegrationFactory:
    """Static factory for creating IntegrationEngine instances."""

    _instance: IntegrationEngine | None = None

    @classmethod
    def create(cls, **kwargs: Any) -> IntegrationEngine:
        engine = IntegrationEngine()
        for key, value in kwargs.items():
            if hasattr(engine, key):
                setattr(engine, key, value)
        logger.info("Created IntegrationEngine via factory")
        return engine

    @classmethod
    def create_default(cls) -> IntegrationEngine:
        return cls.create()

    @classmethod
    def get_or_create(cls) -> IntegrationEngine:
        if cls._instance is None:
            cls._instance = cls.create_default()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
