"""Factory for creating ResilienceEngine instances."""

from __future__ import annotations

import logging
from typing import Any

from app.resilience.engine import ResilienceEngine

logger = logging.getLogger(__name__)


class ResilienceFactory:
    """Static factory for creating ResilienceEngine instances."""

    _instance: ResilienceEngine | None = None

    @classmethod
    def create(cls, **kwargs: Any) -> ResilienceEngine:
        engine = ResilienceEngine()
        for key, value in kwargs.items():
            if hasattr(engine, key):
                setattr(engine, key, value)
        logger.info("Created ResilienceEngine via factory")
        return engine

    @classmethod
    def create_default(cls) -> ResilienceEngine:
        return cls.create()

    @classmethod
    def get_or_create(cls) -> ResilienceEngine:
        if cls._instance is None:
            cls._instance = cls.create_default()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
