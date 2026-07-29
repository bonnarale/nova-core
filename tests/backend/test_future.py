"""Comprehensive tests for Chapter 30 — Future Roadmap."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.future.enums import (
    CapabilityState,
    CompatibilityLevel,
    DeprecationSeverity,
    ExperimentState,
    ExperimentType,
    FeatureState,
    FlagScope,
    VersionBumpType,
)
from app.future.base import (
    CapabilityProvider,
    CompatibilityProvider,
    ExperimentProvider,
    ExtensionProvider,
    FeatureFlagProvider,
)
from app.future.roadmap import Roadmap, RoadmapItem
from app.future.feature_flags import FeatureFlag, FeatureFlagManager
from app.future.experiments import Experiment, ExperimentManager, ExperimentMetrics, ExperimentVariant
from app.future.compatibility import CompatibilityManager, CompatibilityEntry, _parse_version
from app.future.capabilities import Capability, CapabilityRegistry
from app.future.extension_points import ExtensionPoint, ExtensionPointRegistry
from app.future.versioning import SemanticVersion, VersionManager, MigrationRecord
from app.future.deprecation import DeprecationManager, DeprecationEntry
from app.future.configuration import FutureConfig, ConfigurationManager
from app.future.lifecycle import LifecycleManager, LifecycleState
from app.future.metrics import FutureMetrics, get_feature_metrics, get_experiment_metrics
from app.future.tracing import FutureTracer, TraceSpan
from app.future.registry import FutureRegistry
from app.future.factory import FutureFactory


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_feature_state_values(self) -> None:
        vals = [s.value for s in FeatureState]
        assert "disabled" in vals
        assert "enabled" in vals
        assert "experimental" in vals
        assert "beta" in vals
        assert "stable" in vals
        assert "deprecated" in vals
        assert "removed" in vals

    def test_experiment_type_values(self) -> None:
        vals = [s.value for s in ExperimentType]
        assert "a_b" in vals
        assert "canary" in vals
        assert "shadow" in vals
        assert "multivariate" in vals

    def test_experiment_state_values(self) -> None:
        vals = [s.value for s in ExperimentState]
        assert "draft" in vals
        assert "running" in vals
        assert "paused" in vals
        assert "completed" in vals
        assert "cancelled" in vals

    def test_capability_state_values(self) -> None:
        vals = [s.value for s in CapabilityState]
        assert "registered" in vals
        assert "stable" in vals
        assert "deprecated" in vals

    def test_compatibility_level_values(self) -> None:
        vals = [s.value for s in CompatibilityLevel]
        assert "full" in vals
        assert "partial" in vals
        assert "incompatible" in vals

    def test_deprecation_severity_values(self) -> None:
        vals = [s.value for s in DeprecationSeverity]
        assert "info" in vals
        assert "warning" in vals
        assert "error" in vals

    def test_version_bump_type_values(self) -> None:
        vals = [s.value for s in VersionBumpType]
        assert "major" in vals
        assert "minor" in vals
        assert "patch" in vals

    def test_flag_scope_values(self) -> None:
        vals = [s.value for s in FlagScope]
        assert "global" in vals
        assert "user" in vals
        assert "environment" in vals
        assert "percentage" in vals
        assert "scheduled" in vals


# ---------------------------------------------------------------------------
# Base ABCs
# ---------------------------------------------------------------------------

class TestBaseABCs:
    def test_feature_flag_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            FeatureFlagProvider()  # type: ignore

    def test_experiment_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ExperimentProvider()  # type: ignore

    def test_capability_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            CapabilityProvider()  # type: ignore

    def test_compatibility_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            CompatibilityProvider()  # type: ignore

    def test_extension_provider_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ExtensionProvider()  # type: ignore


# ---------------------------------------------------------------------------
# Roadmap
# ---------------------------------------------------------------------------

class TestRoadmap:
    def test_create_roadmap(self) -> None:
        r = Roadmap()
        assert r.list_items() == []

    def test_add_and_get(self) -> None:
        r = Roadmap()
        item = RoadmapItem(id="1", name="test", description="desc", state="experimental")
        r.add(item)
        assert r.get("1") is not None
        assert r.get("1").name == "test"

    def test_add_multiple(self) -> None:
        r = Roadmap()
        r.add(RoadmapItem(id="1", name="a", description="", state="experimental"))
        r.add(RoadmapItem(id="2", name="b", description="", state="stable"))
        assert len(r.list_items()) == 2

    def test_list_by_state(self) -> None:
        r = Roadmap()
        r.add(RoadmapItem(id="1", name="a", description="", state="experimental"))
        r.add(RoadmapItem(id="2", name="b", description="", state="stable"))
        assert len(r.list_items(state="experimental")) == 1

    def test_update_state(self) -> None:
        r = Roadmap()
        r.add(RoadmapItem(id="1", name="a", description="", state="experimental"))
        assert r.update_state("1", "stable") is True
        assert r.get("1").state == "stable"

    def test_update_nonexistent(self) -> None:
        r = Roadmap()
        assert r.update_state("missing", "stable") is False

    def test_remove(self) -> None:
        r = Roadmap()
        r.add(RoadmapItem(id="1", name="a", description="", state="experimental"))
        assert r.remove("1") is True
        assert r.get("1") is None

    def test_remove_nonexistent(self) -> None:
        r = Roadmap()
        assert r.remove("missing") is False

    def test_summary(self) -> None:
        r = Roadmap()
        r.add(RoadmapItem(id="1", name="a", description="", state="experimental"))
        r.add(RoadmapItem(id="2", name="b", description="", state="stable"))
        s = r.summary()
        assert s["total"] == 2
        assert s["by_state"]["experimental"] == 1

    def test_to_dict(self) -> None:
        item = RoadmapItem(id="1", name="test", description="desc", state="stable")
        d = item.to_dict()
        assert d["id"] == "1"
        assert d["name"] == "test"

    def test_sorted_by_priority(self) -> None:
        r = Roadmap()
        r.add(RoadmapItem(id="1", name="low", description="", state="experimental", priority=1))
        r.add(RoadmapItem(id="2", name="high", description="", state="experimental", priority=10))
        items = r.list_items()
        assert items[0].name == "high"


# ---------------------------------------------------------------------------
# Feature Flags
# ---------------------------------------------------------------------------

class TestFeatureFlags:
    def test_create_manager(self) -> None:
        fm = FeatureFlagManager()
        assert fm.get_flags() == {}

    def test_set_and_get(self) -> None:
        fm = FeatureFlagManager()
        fm.set_flag("test_flag", enabled=True)
        assert fm.is_enabled("test_flag") is True

    def test_disabled_flag(self) -> None:
        fm = FeatureFlagManager()
        fm.set_flag("test_flag", enabled=False)
        assert fm.is_enabled("test_flag") is False

    def test_unknown_flag(self) -> None:
        fm = FeatureFlagManager()
        assert fm.is_enabled("unknown") is False

    def test_delete_flag(self) -> None:
        fm = FeatureFlagManager()
        fm.set_flag("test_flag", enabled=True)
        assert fm.delete_flag("test_flag") is True
        assert fm.is_enabled("test_flag") is False

    def test_delete_nonexistent(self) -> None:
        fm = FeatureFlagManager()
        assert fm.delete_flag("missing") is False

    def test_get_flags(self) -> None:
        fm = FeatureFlagManager()
        fm.set_flag("a", enabled=True)
        fm.set_flag("b", enabled=False)
        flags = fm.get_flags()
        assert flags["a"] is True
        assert flags["b"] is False

    def test_list_flags(self) -> None:
        fm = FeatureFlagManager()
        fm.set_flag("a", enabled=True)
        fm.set_flag("b", enabled=False)
        assert len(fm.list_flags()) == 2

    def test_user_override(self) -> None:
        fm = FeatureFlagManager()
        fm.set_flag("test_flag", enabled=True, scope="user")
        fm.set_user_override("test_flag", "user1", False)
        assert fm.is_enabled("test_flag", user_id="user1") is False
        assert fm.is_enabled("test_flag", user_id="user2") is True

    def test_percentage_rollout(self) -> None:
        fm = FeatureFlagManager()
        fm.set_flag("pct_flag", enabled=True, scope="percentage", percentage=100.0)
        assert fm.is_enabled("pct_flag", user_id="anyone") is True
        fm.set_percentage("pct_flag", 0.0)
        assert fm.is_enabled("pct_flag", user_id="anyone") is False

    def test_set_percentage_nonexistent(self) -> None:
        fm = FeatureFlagManager()
        assert fm.set_percentage("missing", 50.0) is False

    def test_environment_scope(self) -> None:
        fm = FeatureFlagManager()
        flag = FeatureFlag(name="env_flag", enabled=True, scope=FlagScope.ENVIRONMENT, environment_values={"prod": True, "staging": False})
        fm._flags["env_flag"] = flag
        assert fm.is_enabled("env_flag", context={"environment": "prod"}) is True
        assert fm.is_enabled("env_flag", context={"environment": "staging"}) is False

    def test_summary(self) -> None:
        fm = FeatureFlagManager()
        fm.set_flag("a", enabled=True)
        fm.set_flag("b", enabled=False)
        s = fm.summary()
        assert s["total"] == 2
        assert s["enabled"] == 1

    def test_feature_flag_to_dict(self) -> None:
        f = FeatureFlag(name="test", enabled=True)
        d = f.to_dict()
        assert d["name"] == "test"
        assert d["enabled"] is True


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------

class TestExperiments:
    def test_create_manager(self) -> None:
        em = ExperimentManager()
        assert em.get_experiments() == []

    def test_create_experiment(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        assert exp.name == "test"
        assert exp.experiment_type == ExperimentType.A_B

    def test_start_experiment(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        assert em.start_experiment(exp.id) is True
        assert exp.state == ExperimentState.RUNNING

    def test_start_nonexistent(self) -> None:
        em = ExperimentManager()
        assert em.start_experiment("missing") is False

    def test_start_already_running(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        em.start_experiment(exp.id)
        assert em.start_experiment(exp.id) is False

    def test_stop_experiment(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        em.start_experiment(exp.id)
        assert em.stop_experiment(exp.id) is True
        assert exp.state == ExperimentState.COMPLETED

    def test_stop_non_running(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        assert em.stop_experiment(exp.id) is False

    def test_pause_experiment(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        em.start_experiment(exp.id)
        assert em.pause_experiment(exp.id) is True
        assert exp.state == ExperimentState.PAUSED

    def test_pause_non_running(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        assert em.pause_experiment(exp.id) is False

    def test_add_variant(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        v = ExperimentVariant(name="control", weight=1.0)
        assert em.add_variant(exp.id, v) is True
        assert len(exp.variants) == 1

    def test_add_variant_nonexistent(self) -> None:
        em = ExperimentManager()
        v = ExperimentVariant(name="control")
        assert em.add_variant("missing", v) is False

    def test_get_variant(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        em.add_variant(exp.id, ExperimentVariant(name="control", weight=1.0))
        em.add_variant(exp.id, ExperimentVariant(name="treatment", weight=1.0))
        em.start_experiment(exp.id)
        variant = em.get_variant(exp.id, user_id="user1")
        assert variant in ("control", "treatment")

    def test_get_variant_not_running(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        em.add_variant(exp.id, ExperimentVariant(name="control"))
        assert em.get_variant(exp.id) is None

    def test_record_impression(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        em.add_variant(exp.id, ExperimentVariant(name="control"))
        em.start_experiment(exp.id)
        assert em.record_impression(exp.id, "control") is True
        assert exp.metrics["control"].impressions == 1

    def test_record_conversion(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        em.add_variant(exp.id, ExperimentVariant(name="control"))
        em.start_experiment(exp.id)
        em.record_impression(exp.id, "control")
        em.record_conversion(exp.id, "control")
        assert exp.metrics["control"].conversions == 1

    def test_record_nonexistent(self) -> None:
        em = ExperimentManager()
        assert em.record_impression("missing", "control") is False
        assert em.record_conversion("missing", "control") is False

    def test_get_metrics(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        em.add_variant(exp.id, ExperimentVariant(name="control"))
        metrics = em.get_metrics(exp.id)
        assert "control" in metrics

    def test_get_metrics_nonexistent(self) -> None:
        em = ExperimentManager()
        assert em.get_metrics("missing") == {}

    def test_delete_experiment(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "a_b")
        assert em.delete_experiment(exp.id) is True
        assert em.get_experiment(exp.id) is None

    def test_summary(self) -> None:
        em = ExperimentManager()
        em.create_experiment("a", "a_b")
        em.create_experiment("b", "canary")
        s = em.summary()
        assert s["total"] == 2

    def test_variant_to_dict(self) -> None:
        v = ExperimentVariant(name="control", weight=1.0)
        d = v.to_dict()
        assert d["name"] == "control"

    def test_experiment_to_dict(self) -> None:
        exp = Experiment(id="1", name="test", experiment_type=ExperimentType.A_B)
        d = exp.to_dict()
        assert d["id"] == "1"
        assert d["experiment_type"] == "a_b"

    def test_metrics_to_dict(self) -> None:
        m = ExperimentMetrics(impressions=100, conversions=10, conversion_rate=0.1)
        d = m.to_dict()
        assert d["impressions"] == 100


# ---------------------------------------------------------------------------
# Compatibility
# ---------------------------------------------------------------------------

class TestCompatibility:
    def test_create_manager(self) -> None:
        cm = CompatibilityManager()
        report = cm.get_compatibility_report()
        assert report["checks"] == 0

    def test_register_component(self) -> None:
        cm = CompatibilityManager()
        cm.register_component("api", "1.0.0")
        assert cm.get_component_version("api") == "1.0.0"

    def test_check_api_compatibility(self) -> None:
        cm = CompatibilityManager()
        result = cm.check_api_compatibility("1.0.0", "1.0.1")
        assert result["level"] == "full"

    def test_check_api_major_incompatible(self) -> None:
        cm = CompatibilityManager()
        result = cm.check_api_compatibility("1.0.0", "2.0.0")
        assert result["level"] == "incompatible"

    def test_check_api_partial(self) -> None:
        cm = CompatibilityManager()
        result = cm.check_api_compatibility("1.0.0", "1.1.0")
        assert result["level"] == "partial"

    def test_check_model_compatibility(self) -> None:
        cm = CompatibilityManager()
        cm.register_component("model", "1.0.0")
        result = cm.check_model_compatibility("model", "1.0.1")
        assert result["level"] == "full"

    def test_check_plugin_compatibility(self) -> None:
        cm = CompatibilityManager()
        result = cm.check_plugin_compatibility("my_plugin", "2.0.0")
        assert result["component"] == "plugin:my_plugin"

    def test_check_workflow_compatibility(self) -> None:
        cm = CompatibilityManager()
        result = cm.check_workflow_compatibility("my_wf", "1.0.0")
        assert result["component"] == "workflow:my_wf"

    def test_check_schema_compatibility(self) -> None:
        cm = CompatibilityManager()
        result = cm.check_schema_compatibility("my_schema", "1.0.0")
        assert result["component"] == "schema:my_schema"

    def test_compatibility_report(self) -> None:
        cm = CompatibilityManager()
        cm.check_api_compatibility("1.0.0", "1.0.1")
        cm.check_api_compatibility("1.0.0", "2.0.0")
        report = cm.get_compatibility_report()
        assert report["checks"] == 2
        assert report["full"] == 1
        assert report["incompatible"] == 1

    def test_get_entries(self) -> None:
        cm = CompatibilityManager()
        cm.check_api_compatibility("1.0.0", "1.0.1")
        entries = cm.get_entries()
        assert len(entries) == 1

    def test_parse_version(self) -> None:
        assert _parse_version("1.2.3") == (1, 2, 3)
        assert _parse_version("invalid") is None

    def test_determine_level_invalid_version(self) -> None:
        level = CompatibilityManager._determine_level("invalid", "1.0.0")
        assert level == CompatibilityLevel.PARTIAL

    def test_entry_to_dict(self) -> None:
        entry = CompatibilityEntry(
            component="api", from_version="1.0.0", to_version="1.0.1",
            level=CompatibilityLevel.FULL,
        )
        d = entry.to_dict()
        assert d["component"] == "api"
        assert d["level"] == "full"


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

class TestCapabilities:
    def test_create_registry(self) -> None:
        cr = CapabilityRegistry()
        assert cr.list_capabilities() == []

    def test_register(self) -> None:
        cr = CapabilityRegistry()
        cap = cr.register("multimodal", "0.1.0")
        assert cap.name == "multimodal"
        assert cap.version == "0.1.0"

    def test_get(self) -> None:
        cr = CapabilityRegistry()
        cr.register("multimodal", "0.1.0")
        cap = cr.get("multimodal")
        assert cap is not None
        assert cap.version == "0.1.0"

    def test_get_nonexistent(self) -> None:
        cr = CapabilityRegistry()
        assert cr.get("missing") is None

    def test_is_available(self) -> None:
        cr = CapabilityRegistry()
        cr.register("multimodal", "0.1.0")
        cr.update_state("multimodal", "stable")
        assert cr.is_available("multimodal") is True

    def test_not_available(self) -> None:
        cr = CapabilityRegistry()
        cr.register("multimodal", "0.1.0")
        assert cr.is_available("multimodal") is False

    def test_update_state(self) -> None:
        cr = CapabilityRegistry()
        cr.register("multimodal", "0.1.0")
        assert cr.update_state("multimodal", "beta") is True
        assert cr.get("multimodal").state == CapabilityState.BETA

    def test_update_state_nonexistent(self) -> None:
        cr = CapabilityRegistry()
        assert cr.update_state("missing", "beta") is False

    def test_remove(self) -> None:
        cr = CapabilityRegistry()
        cr.register("multimodal", "0.1.0")
        assert cr.remove("multimodal") is True
        assert cr.get("multimodal") is None

    def test_list_by_state(self) -> None:
        cr = CapabilityRegistry()
        cr.register("a", "1.0")
        cr.register("b", "1.0")
        cr.update_state("a", "stable")
        assert len(cr.list_by_state("stable")) == 1

    def test_summary(self) -> None:
        cr = CapabilityRegistry()
        cr.register("a", "1.0")
        cr.register("b", "1.0")
        s = cr.summary()
        assert s["total"] == 2

    def test_default_capabilities(self) -> None:
        defaults = CapabilityRegistry.default_capabilities()
        assert len(defaults) == 7
        names = [d["name"] for d in defaults]
        assert "multimodal_providers" in names

    def test_capability_to_dict(self) -> None:
        cap = Capability(name="test", version="1.0")
        d = cap.to_dict()
        assert d["name"] == "test"


# ---------------------------------------------------------------------------
# Extension Points
# ---------------------------------------------------------------------------

class TestExtensionPoints:
    def test_create_registry(self) -> None:
        epr = ExtensionPointRegistry()
        assert epr.list_extensions() == []

    def test_register(self) -> None:
        epr = ExtensionPointRegistry()
        ep = epr.register("my_ext", "provider", metadata={"key": "value"})
        assert ep.name == "my_ext"
        assert ep.extension_type == "provider"

    def test_get(self) -> None:
        epr = ExtensionPointRegistry()
        epr.register("my_ext", "provider")
        assert epr.get("my_ext") is not None

    def test_get_nonexistent(self) -> None:
        epr = ExtensionPointRegistry()
        assert epr.get("missing") is None

    def test_remove(self) -> None:
        epr = ExtensionPointRegistry()
        epr.register("my_ext", "provider")
        assert epr.remove("my_ext") is True
        assert epr.get("my_ext") is None

    def test_list_by_type(self) -> None:
        epr = ExtensionPointRegistry()
        epr.register("a", "provider")
        epr.register("b", "middleware")
        assert len(epr.list_by_type("provider")) == 1

    def test_has_extension(self) -> None:
        epr = ExtensionPointRegistry()
        epr.register("my_ext", "provider")
        assert epr.has_extension("my_ext") is True
        assert epr.has_extension("missing") is False

    def test_summary(self) -> None:
        epr = ExtensionPointRegistry()
        epr.register("a", "provider")
        epr.register("b", "middleware")
        s = epr.summary()
        assert s["total"] == 2

    def test_to_dict(self) -> None:
        ep = ExtensionPoint(name="test", extension_type="provider")
        d = ep.to_dict()
        assert d["name"] == "test"


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

class TestVersioning:
    def test_semantic_version_parse(self) -> None:
        v = SemanticVersion.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_semantic_version_str(self) -> None:
        v = SemanticVersion(1, 2, 3)
        assert str(v) == "1.2.3"

    def test_semantic_version_eq(self) -> None:
        assert SemanticVersion(1, 2, 3) == SemanticVersion(1, 2, 3)
        assert SemanticVersion(1, 2, 3) != SemanticVersion(1, 2, 4)

    def test_semantic_version_lt(self) -> None:
        assert SemanticVersion(1, 0, 0) < SemanticVersion(2, 0, 0)
        assert SemanticVersion(1, 0, 0) < SemanticVersion(1, 1, 0)
        assert SemanticVersion(1, 0, 0) < SemanticVersion(1, 0, 1)

    def test_bump_major(self) -> None:
        v = SemanticVersion(1, 2, 3)
        new = v.bump("major")
        assert str(new) == "2.0.0"

    def test_bump_minor(self) -> None:
        v = SemanticVersion(1, 2, 3)
        new = v.bump("minor")
        assert str(new) == "1.3.0"

    def test_bump_patch(self) -> None:
        v = SemanticVersion(1, 2, 3)
        new = v.bump("patch")
        assert str(new) == "1.2.4"

    def test_version_manager(self) -> None:
        vm = VersionManager("1.0.0")
        assert str(vm.current) == "1.0.0"

    def test_version_manager_bump(self) -> None:
        vm = VersionManager("1.0.0")
        vm.bump("minor")
        assert str(vm.current) == "1.1.0"

    def test_version_manager_set(self) -> None:
        vm = VersionManager("1.0.0")
        vm.set_version("2.3.4")
        assert str(vm.current) == "2.3.4"

    def test_is_compatible(self) -> None:
        vm = VersionManager("1.5.0")
        assert vm.is_compatible("1.0.0") is True
        assert vm.is_compatible("2.0.0") is False

    def test_get_history(self) -> None:
        vm = VersionManager("1.0.0")
        vm.bump("patch")
        vm.bump("patch")
        history = vm.get_history()
        assert len(history) == 2

    def test_record_migration(self) -> None:
        vm = VersionManager("1.0.0")
        rec = vm.record_migration("0.9.0", "1.0.0", "Initial release")
        assert rec.success is True

    def test_summary(self) -> None:
        vm = VersionManager("1.0.0")
        s = vm.summary()
        assert s["current_version"] == "1.0.0"
        assert s["total_migrations"] == 0

    def test_migration_record_to_dict(self) -> None:
        rec = MigrationRecord(from_version="1.0.0", to_version="2.0.0", description="Major")
        d = rec.to_dict()
        assert d["from_version"] == "1.0.0"

    def test_version_to_dict(self) -> None:
        v = SemanticVersion(1, 2, 3)
        d = v.to_dict()
        assert d["major"] == 1


# ---------------------------------------------------------------------------
# Deprecation
# ---------------------------------------------------------------------------

class TestDeprecation:
    def test_create_manager(self) -> None:
        dm = DeprecationManager()
        assert dm.get_entries() == []

    def test_register(self) -> None:
        dm = DeprecationManager()
        entry = dm.register("old_feature", "warning", message="Use new_feature", deprecated_in="1.0.0", remove_in="2.0.0")
        assert entry.feature == "old_feature"
        assert entry.severity == DeprecationSeverity.WARNING

    def test_is_deprecated(self) -> None:
        dm = DeprecationManager()
        dm.register("old_feature", "warning")
        assert dm.is_deprecated("old_feature") is True
        assert dm.is_deprecated("new_feature") is False

    def test_get_entry(self) -> None:
        dm = DeprecationManager()
        dm.register("old_feature", "info")
        entry = dm.get_entry("old_feature")
        assert entry is not None

    def test_check_feature(self) -> None:
        dm = DeprecationManager()
        dm.register("old_feature", "warning", message="Deprecated")
        result = dm.check_feature("old_feature")
        assert result is not None
        assert result["feature"] == "old_feature"
        assert dm.get_usage()["old_feature"] == 1

    def test_check_nonexistent(self) -> None:
        dm = DeprecationManager()
        assert dm.check_feature("missing") is None

    def test_remove_entry(self) -> None:
        dm = DeprecationManager()
        dm.register("old_feature", "warning")
        assert dm.remove_entry("old_feature") is True
        assert dm.is_deprecated("old_feature") is False

    def test_get_warnings(self) -> None:
        dm = DeprecationManager()
        dm.register("a", "info")
        dm.register("b", "warning")
        dm.register("c", "error")
        warnings = dm.get_warnings()
        assert len(warnings) == 2

    def test_summary(self) -> None:
        dm = DeprecationManager()
        dm.register("a", "info")
        dm.register("b", "warning")
        s = dm.summary()
        assert s["total"] == 2
        assert s["by_severity"]["info"] == 1

    def test_entry_to_dict(self) -> None:
        entry = DeprecationEntry(feature="test", severity=DeprecationSeverity.WARNING, message="msg")
        d = entry.to_dict()
        assert d["feature"] == "test"
        assert d["severity"] == "warning"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class TestConfiguration:
    def test_default_config(self) -> None:
        cfg = FutureConfig()
        assert cfg.feature_flags_enabled is True
        assert cfg.max_flags == 1000

    def test_manager(self) -> None:
        cm = ConfigurationManager()
        assert cm.get("feature_flags_enabled") is True

    def test_set_override(self) -> None:
        cm = ConfigurationManager()
        cm.set("custom_key", "custom_value")
        assert cm.get("custom_key") == "custom_value"

    def test_reset(self) -> None:
        cm = ConfigurationManager()
        cm.set("key", "value")
        cm.reset()
        assert cm.get("key") is None

    def test_to_dict(self) -> None:
        cm = ConfigurationManager()
        d = cm.to_dict()
        assert "feature_flags_enabled" in d

    def test_is_enabled(self) -> None:
        cm = ConfigurationManager()
        assert cm.is_enabled("feature_flags_enabled") is True

    def test_custom_config(self) -> None:
        cfg = FutureConfig(max_flags=100)
        cm = ConfigurationManager(config=cfg)
        assert cm.get("max_flags") == 100


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

class TestLifecycle:
    def test_create_manager(self) -> None:
        lm = LifecycleManager()
        assert lm.list_components() == []

    def test_register(self) -> None:
        lm = LifecycleManager()
        state = lm.register("component_a")
        assert state.state == "registered"

    def test_valid_transition(self) -> None:
        lm = LifecycleManager()
        lm.register("comp")
        assert lm.transition("comp", "experimental") is True
        assert lm.get_state("comp").state == "experimental"

    def test_invalid_transition(self) -> None:
        lm = LifecycleManager()
        lm.register("comp")
        assert lm.transition("comp", "stable") is False

    def test_transition_nonexistent(self) -> None:
        lm = LifecycleManager()
        assert lm.transition("missing", "beta") is False

    def test_full_lifecycle(self) -> None:
        lm = LifecycleManager()
        lm.register("comp")
        assert lm.transition("comp", "experimental") is True
        assert lm.transition("comp", "beta") is True
        assert lm.transition("comp", "stable") is True
        assert lm.transition("comp", "deprecated") is True
        assert lm.transition("comp", "removed") is True

    def test_get_history(self) -> None:
        lm = LifecycleManager()
        lm.register("comp")
        lm.transition("comp", "experimental")
        history = lm.get_history("comp")
        assert len(history) == 2

    def test_is_valid_transition(self) -> None:
        assert LifecycleManager().is_valid_transition("registered", "experimental") is True
        assert LifecycleManager().is_valid_transition("registered", "stable") is False

    def test_summary(self) -> None:
        lm = LifecycleManager()
        lm.register("a")
        lm.register("b")
        s = lm.summary()
        assert s["total"] == 2


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class TestMetrics:
    def test_create_metrics(self) -> None:
        fm = FutureMetrics()
        s = fm.summary()
        assert s["total_points"] == 0

    def test_record(self) -> None:
        fm = FutureMetrics()
        fm.record("feature_used")
        assert fm.count("feature_used") == 1

    def test_increment(self) -> None:
        fm = FutureMetrics()
        fm.increment("hits")
        fm.increment("hits")
        assert fm.count("hits") == 2

    def test_gauge(self) -> None:
        fm = FutureMetrics()
        fm.gauge("cpu", 0.5)
        assert fm.sum_values("cpu") == 0.5

    def test_sum_values(self) -> None:
        fm = FutureMetrics()
        fm.record("a", 1.0)
        fm.record("a", 2.0)
        assert fm.sum_values("a") == 3.0

    def test_get_points(self) -> None:
        fm = FutureMetrics()
        fm.record("test", 1.0)
        points = fm.get_points("test")
        assert len(points) == 1

    def test_all_names(self) -> None:
        fm = FutureMetrics()
        fm.record("x", 1.0)
        fm.record("y", 1.0)
        assert set(fm.all_names()) == {"x", "y"}

    def test_reset(self) -> None:
        fm = FutureMetrics()
        fm.record("x", 1.0)
        fm.reset()
        assert fm.count("x") == 0

    def test_singleton_metrics(self) -> None:
        m1 = get_feature_metrics()
        m2 = get_feature_metrics()
        assert m1 is m2

    def test_singleton_experiment_metrics(self) -> None:
        m1 = get_experiment_metrics()
        m2 = get_experiment_metrics()
        assert m1 is m2


# ---------------------------------------------------------------------------
# Tracing
# ---------------------------------------------------------------------------

class TestTracing:
    def test_create_tracer(self) -> None:
        t = FutureTracer()
        s = t.summary()
        assert s["total_spans"] == 0

    def test_start_and_end_span(self) -> None:
        t = FutureTracer()
        span_id = t.start_span("test_op")
        time.sleep(0.001)
        span = t.end_span(span_id)
        assert span is not None
        assert span.name == "test_op"
        assert span.duration_ms > 0
        assert span.status == "ok"

    def test_end_nonexistent_span(self) -> None:
        t = FutureTracer()
        assert t.end_span("missing") is None

    def test_get_spans(self) -> None:
        t = FutureTracer()
        sid = t.start_span("op1")
        t.end_span(sid)
        assert len(t.get_spans()) == 1

    def test_get_span(self) -> None:
        t = FutureTracer()
        sid = t.start_span("op1")
        t.end_span(sid)
        span = t.get_span(sid)
        assert span is not None

    def test_get_spans_by_name(self) -> None:
        t = FutureTracer()
        sid1 = t.start_span("op1")
        t.end_span(sid1)
        sid2 = t.start_span("op2")
        t.end_span(sid2)
        assert len(t.get_spans_by_name("op1")) == 1

    def test_clear(self) -> None:
        t = FutureTracer()
        sid = t.start_span("op1")
        t.end_span(sid)
        t.clear()
        assert len(t.get_spans()) == 0

    def test_parent_id(self) -> None:
        t = FutureTracer()
        parent = t.start_span("parent")
        child = t.start_span("child", parent_id=parent)
        t.end_span(child)
        span = t.get_span(child)
        assert span.parent_id == parent

    def test_summary(self) -> None:
        t = FutureTracer()
        sid = t.start_span("test")
        t.end_span(sid)
        s = t.summary()
        assert s["total_spans"] == 1

    def test_span_to_dict(self) -> None:
        span = TraceSpan(span_id="1", name="test", start_time=0.0, end_time=1.0, duration_ms=1.0)
        d = span.to_dict()
        assert d["span_id"] == "1"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_singleton(self) -> None:
        FutureRegistry.reset()
        r1 = FutureRegistry()
        r2 = FutureRegistry()
        assert r1 is r2

    def test_reset(self) -> None:
        FutureRegistry.reset()
        r = FutureRegistry()
        FutureRegistry.reset()
        r2 = FutureRegistry()
        assert r is not r2

    def test_has_all_components(self) -> None:
        FutureRegistry.reset()
        r = FutureRegistry()
        assert hasattr(r, "feature_flags")
        assert hasattr(r, "experiments")
        assert hasattr(r, "capabilities")
        assert hasattr(r, "compatibility")
        assert hasattr(r, "deprecation")
        assert hasattr(r, "extension_points")
        assert hasattr(r, "roadmap")
        assert hasattr(r, "lifecycle")
        assert hasattr(r, "versioning")
        assert hasattr(r, "metrics")
        assert hasattr(r, "tracing")

    def test_summary(self) -> None:
        FutureRegistry.reset()
        r = FutureRegistry()
        s = r.summary()
        assert "feature_flags" in s
        assert "experiments" in s
        assert "capabilities" in s
        assert "compatibility" in s
        assert "deprecation" in s
        assert "extensions" in s
        assert "roadmap" in s
        assert "versioning" in s
        assert "metrics" in s
        assert "tracing" in s


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class TestFactory:
    def test_create_feature_flags(self) -> None:
        ff = FutureFactory.create_feature_flags()
        assert isinstance(ff, FeatureFlagManager)

    def test_create_experiments(self) -> None:
        em = FutureFactory.create_experiments()
        assert isinstance(em, ExperimentManager)

    def test_create_capabilities(self) -> None:
        cr = FutureFactory.create_capabilities()
        assert isinstance(cr, CapabilityRegistry)

    def test_create_compatibility(self) -> None:
        cm = FutureFactory.create_compatibility()
        assert isinstance(cm, CompatibilityManager)

    def test_create_deprecation(self) -> None:
        dm = FutureFactory.create_deprecation()
        assert isinstance(dm, DeprecationManager)

    def test_create_extension_points(self) -> None:
        epr = FutureFactory.create_extension_points()
        assert isinstance(epr, ExtensionPointRegistry)

    def test_create_roadmap(self) -> None:
        rm = FutureFactory.create_roadmap()
        assert isinstance(rm, Roadmap)

    def test_create_lifecycle(self) -> None:
        lm = FutureFactory.create_lifecycle()
        assert isinstance(lm, LifecycleManager)

    def test_create_versioning(self) -> None:
        vm = FutureFactory.create_versioning("2.0.0")
        assert str(vm.current) == "2.0.0"

    def test_create_metrics(self) -> None:
        fm = FutureFactory.create_metrics()
        assert isinstance(fm, FutureMetrics)

    def test_create_tracing(self) -> None:
        ft = FutureFactory.create_tracing()
        assert isinstance(ft, FutureTracer)

    def test_create_configuration(self) -> None:
        cm = FutureFactory.create_configuration()
        assert isinstance(cm, ConfigurationManager)

    def test_create_full(self) -> None:
        full = FutureFactory.create_full()
        assert "feature_flags" in full
        assert "experiments" in full
        assert len(full) == 12

    def test_create_registry(self) -> None:
        FutureRegistry.reset()
        r = FutureFactory.create_registry()
        assert isinstance(r, FutureRegistry)


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

class TestAPIRoutes:
    @pytest.mark.asyncio
    async def test_future_features_no_registry(self) -> None:
        from app.api.v1.routes.future import set_dependencies
        set_dependencies(None)
        from app.api.v1.routes.future import future_features
        result = await future_features()
        assert result["success"] is True
        assert result["data"]["total"] == 0

    @pytest.mark.asyncio
    async def test_future_experiments_no_registry(self) -> None:
        from app.api.v1.routes.future import future_experiments
        result = await future_experiments()
        assert result["success"] is True
        assert result["data"]["total"] == 0

    @pytest.mark.asyncio
    async def test_future_capabilities_no_registry(self) -> None:
        from app.api.v1.routes.future import future_capabilities
        result = await future_capabilities()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_future_compatibility_no_registry(self) -> None:
        from app.api.v1.routes.future import future_compatibility
        result = await future_compatibility()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_future_deprecations_no_registry(self) -> None:
        from app.api.v1.routes.future import future_deprecations
        result = await future_deprecations()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_future_roadmap_no_registry(self) -> None:
        from app.api.v1.routes.future import future_roadmap
        result = await future_roadmap()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_future_metrics_no_registry(self) -> None:
        from app.api.v1.routes.future import future_metrics
        result = await future_metrics()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_future_statistics_no_registry(self) -> None:
        from app.api.v1.routes.future import future_statistics
        result = await future_statistics()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_future_features_with_registry(self) -> None:
        FutureRegistry.reset()
        r = FutureRegistry()
        r.feature_flags.set_flag("test_flag", enabled=True)
        from app.api.v1.routes.future import set_dependencies, future_features
        set_dependencies(r)
        result = await future_features()
        assert result["success"] is True
        assert result["data"]["total"] == 1
        set_dependencies(None)

    @pytest.mark.asyncio
    async def test_future_experiments_with_registry(self) -> None:
        FutureRegistry.reset()
        r = FutureRegistry()
        r.experiments.create_experiment("test_exp", "a_b")
        from app.api.v1.routes.future import set_dependencies, future_experiments
        set_dependencies(r)
        result = await future_experiments()
        assert result["success"] is True
        assert result["data"]["total"] == 1
        set_dependencies(None)

    @pytest.mark.asyncio
    async def test_future_statistics_with_registry(self) -> None:
        FutureRegistry.reset()
        r = FutureRegistry()
        from app.api.v1.routes.future import set_dependencies, future_statistics
        set_dependencies(r)
        result = await future_statistics()
        assert result["success"] is True
        assert "feature_flags" in result["data"]
        set_dependencies(None)


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_feature_flag_with_experiment(self) -> None:
        fm = FeatureFlagManager()
        em = ExperimentManager()
        fm.set_flag("new_ui", enabled=True, scope="percentage", percentage=50.0)
        exp = em.create_experiment("ui_experiment", "a_b")
        em.add_variant(exp.id, ExperimentVariant(name="control", weight=1.0))
        em.add_variant(exp.id, ExperimentVariant(name="treatment", weight=1.0))
        em.start_experiment(exp.id)
        for uid in range(100):
            if fm.is_enabled("new_ui", user_id=str(uid)):
                variant = em.get_variant(exp.id, user_id=str(uid))
                assert variant in ("control", "treatment")

    def test_capability_lifecycle(self) -> None:
        cr = CapabilityRegistry()
        lm = LifecycleManager()
        cr.register("voice", "0.1.0")
        lm.register("voice")
        cr.update_state("voice", "experimental")
        lm.transition("voice", "experimental")
        assert cr.is_available("voice") is False
        cr.update_state("voice", "beta")
        lm.transition("voice", "beta")
        assert cr.is_available("voice") is True

    def test_deprecation_with_versioning(self) -> None:
        dm = DeprecationManager()
        vm = VersionManager("1.0.0")
        dm.register("old_api", "warning", deprecated_in="1.0.0", remove_in="3.0.0")
        vm.bump("major")
        assert dm.is_deprecated("old_api") is True
        assert str(vm.current) == "2.0.0"

    def test_compatibility_with_versioning(self) -> None:
        cm = CompatibilityManager()
        vm = VersionManager("1.0.0")
        cm.register_component("api", "1.0.0")
        vm.bump("minor")
        result = cm.check_api_compatibility("1.0.0", str(vm.current))
        assert result["level"] == "partial"

    def test_extension_points_with_capabilities(self) -> None:
        epr = ExtensionPointRegistry()
        cr = CapabilityRegistry()
        epr.register("voice_provider", "provider")
        cr.register("voice", "0.1.0")
        assert epr.has_extension("voice_provider")
        assert cr.get("voice") is not None


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_feature_flags(self) -> None:
        fm = FeatureFlagManager()
        assert fm.summary()["total"] == 0

    def test_empty_experiments(self) -> None:
        em = ExperimentManager()
        assert em.summary()["total"] == 0

    def test_empty_capabilities(self) -> None:
        cr = CapabilityRegistry()
        assert cr.summary()["total"] == 0

    def test_empty_compatibility(self) -> None:
        cm = CompatibilityManager()
        report = cm.get_compatibility_report()
        assert report["checks"] == 0

    def test_empty_deprecation(self) -> None:
        dm = DeprecationManager()
        assert dm.summary()["total"] == 0

    def test_empty_roadmap(self) -> None:
        r = Roadmap()
        assert r.summary()["total"] == 0

    def test_empty_lifecycle(self) -> None:
        lm = LifecycleManager()
        assert lm.summary()["total"] == 0

    def test_version_parse_invalid(self) -> None:
        v = SemanticVersion.parse("abc")
        assert v.major == 0

    def test_feature_flag_zero_percentage(self) -> None:
        fm = FeatureFlagManager()
        fm.set_flag("f", enabled=True, scope="percentage", percentage=0.0)
        assert fm.is_enabled("f") is False

    def test_experiment_single_variant(self) -> None:
        em = ExperimentManager()
        exp = em.create_experiment("test", "canary")
        em.add_variant(exp.id, ExperimentVariant(name="only"))
        em.start_experiment(exp.id)
        assert em.get_variant(exp.id, user_id="u1") == "only"

    def test_metrics_record_with_tags(self) -> None:
        fm = FutureMetrics()
        fm.record("test", 1.0, tags={"env": "prod"})
        points = fm.get_points("test")
        assert points[0].tags["env"] == "prod"

    def test_tracing_metadata(self) -> None:
        t = FutureTracer()
        sid = t.start_span("test", metadata={"key": "value"})
        t.end_span(sid)
        span = t.get_span(sid)
        assert span.metadata["key"] == "value"
