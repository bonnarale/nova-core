"""Factory for creating PerformanceOptimizer instances."""

from __future__ import annotations

import logging
from typing import Any

from app.performance.optimizer import PerformanceOptimizer

logger = logging.getLogger(__name__)


class PerformanceFactory:
    """Static factory for creating PerformanceOptimizer instances."""

    _instance: PerformanceOptimizer | None = None

    @classmethod
    def create(cls, **kwargs: Any) -> PerformanceOptimizer:
        engine = PerformanceOptimizer()
        for key, value in kwargs.items():
            if hasattr(engine, key):
                setattr(engine, key, value)
        logger.info("Created PerformanceOptimizer via factory")
        return engine

    @classmethod
    def create_default(cls) -> PerformanceOptimizer:
        return cls.create()

    @classmethod
    def get_or_create(cls) -> PerformanceOptimizer:
        if cls._instance is None:
            cls._instance = cls.create_default()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
