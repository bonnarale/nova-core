"""Factory for creating EnterpriseEngine instances."""

from __future__ import annotations

import logging
from typing import Any

from app.enterprise.engine import EnterpriseEngine

logger = logging.getLogger(__name__)


class EnterpriseFactory:
    """Static factory for creating EnterpriseEngine instances."""

    _instance: EnterpriseEngine | None = None

    @classmethod
    def create(cls, **kwargs: Any) -> EnterpriseEngine:
        engine = EnterpriseEngine()
        for key, value in kwargs.items():
            if hasattr(engine.manager, key):
                setattr(engine.manager, key, value)
        logger.info("Created EnterpriseEngine via factory")
        return engine

    @classmethod
    def create_default(cls) -> EnterpriseEngine:
        return cls.create()

    @classmethod
    def get_or_create(cls) -> EnterpriseEngine:
        if cls._instance is None:
            cls._instance = cls.create_default()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
