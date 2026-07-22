"""Tests for enhanced metrics — OutputQuality, ResourceMetrics, SystemImpact, and extended ExecutionOutcome."""

import pytest

from app.learning.models import (
    ExecutionOutcome,
    OutputQuality,
    ResourceMetrics,
    SystemImpact,
)
from app.long_term_memory.models import MemoryType


class TestOutputQuality:
    """Tests for OutputQuality dataclass."""

    def test_create_valid_quality_score(self):
        quality = OutputQuality(score=85)
        assert quality.score == 85
        assert quality.scoring_method == "manual"

    def test_create_quality_with_heuristic_method(self):
        quality = OutputQuality(score=72, scoring_method="heuristic")
        assert quality.scoring_method == "heuristic"

    def test_quality_score_boundary_zero(self):
        quality = OutputQuality(score=0)
        assert quality.score == 0

    def test_quality_score_boundary_hundred(self):
        quality = OutputQuality(score=100)
        assert quality.score == 100

    def test_quality_score_below_range_raises(self):
        with pytest.raises(ValueError, match="between 0 and 100"):
            OutputQuality(score=-1)

    def test_quality_score_above_range_raises(self):
        with pytest.raises(ValueError, match="between 0 and 100"):
            OutputQuality(score=101)


class TestResourceMetrics:
    """Tests for ResourceMetrics dataclass."""

    def test_create_empty_resource_metrics(self):
        metrics = ResourceMetrics()
        assert metrics.memory_used_mb is None
        assert metrics.cpu_time_ms is None
        assert metrics.tokens_used is None

    def test_create_with_all_fields(self):
        metrics = ResourceMetrics(
            memory_used_mb=256.5,
            cpu_time_ms=1500.0,
            tokens_used=4096,
        )
        assert metrics.memory_used_mb == 256.5
        assert metrics.cpu_time_ms == 1500.0
        assert metrics.tokens_used == 4096

    def test_create_with_partial_fields(self):
        metrics = ResourceMetrics(tokens_used=2048)
        assert metrics.memory_used_mb is None
        assert metrics.cpu_time_ms is None
        assert metrics.tokens_used == 2048


class TestSystemImpact:
    """Tests for SystemImpact dataclass."""

    def test_create_empty_system_impact(self):
        impact = SystemImpact()
        assert impact.latency_ms is None
        assert impact.throughput_ops_per_sec is None

    def test_create_with_all_fields(self):
        impact = SystemImpact(
            latency_ms=45.2,
            throughput_ops_per_sec=120.5,
        )
        assert impact.latency_ms == 45.2
        assert impact.throughput_ops_per_sec == 120.5

    def test_create_with_partial_fields(self):
        impact = SystemImpact(latency_ms=30.0)
        assert impact.latency_ms == 30.0
        assert impact.throughput_ops_per_sec is None


class TestExecutionOutcomeExtended:
    """Tests for extended ExecutionOutcome with new fields."""

    def test_default_outcome_has_no_quality(self):
        outcome = ExecutionOutcome(
            id="o1", execution_id="e1", outcome="success"
        )
        assert outcome.quality_score is None
        assert outcome.resource_metrics is None
        assert outcome.system_impact is None

    def test_outcome_with_quality_score(self):
        outcome = ExecutionOutcome(
            id="o1",
            execution_id="e1",
            outcome="success",
            quality_score=85,
        )
        assert outcome.quality_score == 85

    def test_outcome_with_resource_metrics(self):
        rm = ResourceMetrics(memory_used_mb=128.0, tokens_used=1024)
        outcome = ExecutionOutcome(
            id="o1",
            execution_id="e1",
            outcome="success",
            resource_metrics=rm,
        )
        assert outcome.resource_metrics.memory_used_mb == 128.0
        assert outcome.resource_metrics.tokens_used == 1024

    def test_outcome_with_system_impact(self):
        si = SystemImpact(latency_ms=50.0)
        outcome = ExecutionOutcome(
            id="o1",
            execution_id="e1",
            outcome="success",
            system_impact=si,
        )
        assert outcome.system_impact.latency_ms == 50.0

    def test_outcome_quality_none_for_partial(self):
        outcome = ExecutionOutcome(
            id="o1", execution_id="e1", outcome="partial"
        )
        assert outcome.quality_score is None

    def test_outcome_quality_none_for_failure(self):
        outcome = ExecutionOutcome(
            id="o1", execution_id="e1", outcome="failure"
        )
        assert outcome.quality_score is None

    def test_to_dict_includes_new_fields(self):
        outcome = ExecutionOutcome(
            id="o1",
            execution_id="e1",
            outcome="success",
            quality_score=90,
            resource_metrics=ResourceMetrics(memory_used_mb=64.0, tokens_used=512),
            system_impact=SystemImpact(latency_ms=25.0),
        )
        d = outcome.to_dict()
        assert d["quality_score"] == 90
        assert d["resource_metrics"]["memory_used_mb"] == 64.0
        assert d["resource_metrics"]["tokens_used"] == 512
        assert d["system_impact"]["latency_ms"] == 25.0

    def test_to_dict_none_fields(self):
        outcome = ExecutionOutcome(
            id="o1", execution_id="e1", outcome="failure"
        )
        d = outcome.to_dict()
        assert d["quality_score"] is None
        assert d["resource_metrics"] is None
        assert d["system_impact"] is None

    def test_from_dict_reconstructs_nested_dataclasses(self):
        d = {
            "id": "o1",
            "execution_id": "e1",
            "outcome": "success",
            "quality_score": 75,
            "resource_metrics": {
                "memory_used_mb": 32.0,
                "cpu_time_ms": 100.0,
                "tokens_used": 256,
            },
            "system_impact": {
                "latency_ms": 10.0,
                "throughput_ops_per_sec": 200.0,
            },
        }
        outcome = ExecutionOutcome.from_dict(d)
        assert outcome.quality_score == 75
        assert isinstance(outcome.resource_metrics, ResourceMetrics)
        assert outcome.resource_metrics.memory_used_mb == 32.0
        assert isinstance(outcome.system_impact, SystemImpact)
        assert outcome.system_impact.throughput_ops_per_sec == 200.0

    def test_from_dict_handles_none_nested(self):
        d = {
            "id": "o1",
            "execution_id": "e1",
            "outcome": "failure",
            "quality_score": None,
            "resource_metrics": None,
            "system_impact": None,
        }
        outcome = ExecutionOutcome.from_dict(d)
        assert outcome.quality_score is None
        assert outcome.resource_metrics is None
        assert outcome.system_impact is None

    def test_roundtrip_serialization(self):
        original = ExecutionOutcome(
            id="o1",
            execution_id="e1",
            outcome="success",
            quality_score=88,
            resource_metrics=ResourceMetrics(memory_used_mb=512.0, tokens_used=8192),
            system_impact=SystemImpact(latency_ms=33.3, throughput_ops_per_sec=150.0),
        )
        d = original.to_dict()
        restored = ExecutionOutcome.from_dict(d)
        assert restored.id == original.id
        assert restored.quality_score == original.quality_score
        assert restored.resource_metrics.memory_used_mb == original.resource_metrics.memory_used_mb
        assert restored.system_impact.latency_ms == original.system_impact.latency_ms


class TestMemoryTypeEnum:
    """Tests for MemoryType enum extensions."""

    def test_preference_enum_value(self):
        assert MemoryType.PREFERENCE.value == "preference"

    def test_error_pattern_enum_value(self):
        assert MemoryType.ERROR_PATTERN.value == "error_pattern"

    def test_preference_is_memory_type(self):
        assert isinstance(MemoryType.PREFERENCE, MemoryType)

    def test_error_pattern_is_memory_type(self):
        assert isinstance(MemoryType.ERROR_PATTERN, MemoryType)
