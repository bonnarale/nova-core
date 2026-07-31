"""Deployment manager — top-level orchestrator (re-exports engine)."""

from __future__ import annotations

from app.scaling.engine import ScalingEngine

__all__ = ["ScalingManager"]

ScalingManager = ScalingEngine
