"""Factory for creating AutonomyEngine instances."""

from __future__ import annotations

import logging
from typing import Any

from app.autonomy.engine import AutonomyEngine

logger = logging.getLogger(__name__)


class AutonomyFactory:
    """Static factory for creating AutonomyEngine instances."""

    _instance: AutonomyEngine | None = None

    @classmethod
    def create(cls, **kwargs: Any) -> AutonomyEngine:
        engine = AutonomyEngine()
        for key, value in kwargs.items():
            if hasattr(engine.manager, key):
                setattr(engine.manager, key, value)
        logger.info("Created AutonomyEngine via factory")
        return engine

    @classmethod
    def create_default(cls) -> AutonomyEngine:
        return cls.create()

    @classmethod
    def get_or_create(cls) -> AutonomyEngine:
        if cls._instance is None:
            cls._instance = cls.create_default()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
