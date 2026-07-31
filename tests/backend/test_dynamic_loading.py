"""Tests for AgentFactory dynamic module loading."""

from __future__ import annotations

import pytest

from app.agents.factory import AgentFactory, ModuleNotAllowed
from app.agents.runtime import AgentRuntime


class TestDynamicModuleLoading:
    @pytest.fixture
    def factory(self):
        runtime = AgentRuntime()
        return AgentFactory(runtime=runtime)

    def test_register_from_module_valid(self, factory):
        """Should register BaseAgent subclasses from a valid module."""
        # Use a known module with agents
        agents = factory.register_from_module(
            "app.agents.builtins.planner_agent",
            whitelist=["app.agents"],
        )
        assert len(agents) >= 1
        assert agents[0].agent_id == "planner"

    def test_register_from_module_not_found(self, factory):
        """Should raise ModuleNotFoundError for non-existent modules within whitelist."""
        with pytest.raises(ModuleNotFoundError):
            factory.register_from_module(
                "app.agents.nonexistent_module_xyz",
                whitelist=["app.agents"],
            )

    def test_register_from_module_disallowed_prefix(self, factory):
        """Should raise ModuleNotAllowed for disallowed module paths."""
        with pytest.raises(ModuleNotAllowed):
            factory.register_from_module(
                "os",
                whitelist=["app.agents"],
            )

    def test_register_from_module_custom_whitelist(self, factory):
        """Should respect custom whitelist."""
        with pytest.raises(ModuleNotAllowed):
            factory.register_from_module(
                "app.agents.builtins.planner_agent",
                whitelist=["custom.prefix"],
            )

    def test_register_from_module_specific_class(self, factory):
        """Should register a specific class by name."""
        agents = factory.register_from_module(
            "app.agents.builtins.planner_agent",
            class_name="PlannerAgent",
            whitelist=["app.agents"],
        )
        assert len(agents) == 1
        assert agents[0].agent_id == "planner"

    def test_register_from_module_all_subclasses(self, factory):
        """Should register all BaseAgent subclasses when no class_name given."""
        agents = factory.register_from_module(
            "app.agents.builtins.opencode_agent",
            whitelist=["app.agents"],
        )
        assert len(agents) >= 1
        agent_ids = [a.agent_id for a in agents]
        assert "opencode" in agent_ids

    def test_registered_agent_is_usable(self, factory):
        """Dynamically registered agent should be usable via runtime."""
        factory.register_from_module(
            "app.agents.builtins.planner_agent",
            whitelist=["app.agents"],
        )
        agent = factory.runtime.registry.get("planner")
        assert agent is not None
        assert agent.agent_id == "planner"

    def test_default_whitelist(self, factory):
        """Should use default whitelist when none provided."""
        # This should work with the default whitelist ["app.agents"]
        agents = factory.register_from_module("app.agents.builtins.planner_agent")
        assert len(agents) >= 1

    def test_invalid_class_name(self, factory):
        """Should raise AttributeError for non-existent class name."""
        with pytest.raises(AttributeError):
            factory.register_from_module(
                "app.agents.builtins.planner_agent",
                class_name="NonExistentAgent",
                whitelist=["app.agents"],
            )
