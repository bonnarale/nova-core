"""Tests for the RuleBasedStrategy."""

from __future__ import annotations

import pytest

from app.executive.strategy import PlanningOutput, RuleBasedStrategy, SuggestedTask


class TestRuleBasedStrategy:
    @pytest.fixture
    def strategy(self):
        return RuleBasedStrategy()

    @pytest.mark.asyncio
    async def test_empty_goals_returns_empty_output(self, strategy):
        output = await strategy.analyze(
            goals=[], tasks=[], profile=None, recent_messages=[]
        )
        assert isinstance(output, PlanningOutput)
        assert output.reviewed_goal_ids == []
        assert output.suggested_tasks == []
        assert output.observations == []

    @pytest.mark.asyncio
    async def test_skips_completed_goals(self, strategy):
        goals = [{"id": "g1", "title": "Done", "status": "completed", "priority": 1, "progress": 100}]
        output = await strategy.analyze(goals, [], None, [])
        assert "g1" in output.reviewed_goal_ids
        assert output.suggested_tasks == []

    @pytest.mark.asyncio
    async def test_skips_abandoned_goals(self, strategy):
        goals = [{"id": "g1", "title": "Abandoned", "status": "abandoned", "priority": 1, "progress": 0}]
        output = await strategy.analyze(goals, [], None, [])
        assert output.suggested_tasks == []

    @pytest.mark.asyncio
    async def test_creates_task_for_active_goal(self, strategy):
        goals = [{"id": "g1", "title": "Build login page", "status": "active", "priority": 5, "progress": 0}]
        output = await strategy.analyze(goals, [], None, [])
        assert len(output.suggested_tasks) == 1
        t = output.suggested_tasks[0]
        assert t.goal_id == "g1"
        assert t.goal_title == "Build login page"
        assert t.priority == 5

    @pytest.mark.asyncio
    async def test_suggests_coder_for_build_keyword(self, strategy):
        goals = [{"id": "g1", "title": "Build API endpoint", "status": "active", "priority": 3, "progress": 0}]
        output = await strategy.analyze(goals, [], None, [])
        assert output.suggested_tasks[0].suggested_agent == "coder"

    @pytest.mark.asyncio
    async def test_suggests_researcher_for_research_keyword(self, strategy):
        goals = [{"id": "g2", "title": "Research ML models", "status": "active", "priority": 2, "progress": 0}]
        output = await strategy.analyze(goals, [], None, [])
        assert output.suggested_tasks[0].suggested_agent == "researcher"

    @pytest.mark.asyncio
    async def test_suggests_planner_for_plan_keyword(self, strategy):
        goals = [{"id": "g3", "title": "Plan sprint goals", "status": "active", "priority": 1, "progress": 0}]
        output = await strategy.analyze(goals, [], None, [])
        assert output.suggested_tasks[0].suggested_agent == "planner"

    @pytest.mark.asyncio
    async def test_suggests_reviewer_for_review_keyword(self, strategy):
        goals = [{"id": "g4", "title": "Inspect and validate output", "status": "active", "priority": 3, "progress": 0}]
        output = await strategy.analyze(goals, [], None, [])
        assert output.suggested_tasks[0].suggested_agent == "reviewer"

    @pytest.mark.asyncio
    async def test_suggests_memory_for_remember_keyword(self, strategy):
        goals = [{"id": "g7", "title": "Remember user preferences", "status": "active", "priority": 2, "progress": 0}]
        output = await strategy.analyze(goals, [], None, [])
        assert output.suggested_tasks[0].suggested_agent == "memory"

    @pytest.mark.asyncio
    async def test_suggests_executor_for_deploy_keyword(self, strategy):
        goals = [{"id": "g5", "title": "Deploy to production", "status": "active", "priority": 4, "progress": 0}]
        output = await strategy.analyze(goals, [], None, [])
        assert output.suggested_tasks[0].suggested_agent == "executor"

    @pytest.mark.asyncio
    async def test_defaults_to_executor_when_no_keyword_match(self, strategy):
        goals = [{"id": "g6", "title": "Something generic", "status": "active", "priority": 3, "progress": 0}]
        output = await strategy.analyze(goals, [], None, [])
        assert output.suggested_tasks[0].suggested_agent == "executor"

    @pytest.mark.asyncio
    async def test_skips_goal_with_active_task(self, strategy):
        goals = [{"id": "g1", "title": "Build feature", "status": "active", "priority": 5, "progress": 30}]
        tasks = [{"goal_id": "g1", "status": "RUNNING"}]
        output = await strategy.analyze(goals, tasks, None, [])
        assert output.suggested_tasks == []
        assert any("already has an active task" in obs for obs in output.observations)

    @pytest.mark.asyncio
    async def test_skips_goal_with_completed_task_and_100_progress(self, strategy):
        goals = [{"id": "g1", "title": "Done feature", "status": "active", "priority": 3, "progress": 100}]
        tasks = [{"goal_id": "g1", "status": "COMPLETED"}]
        output = await strategy.analyze(goals, tasks, None, [])
        assert output.suggested_tasks == []

    @pytest.mark.asyncio
    async def test_suggests_task_when_completed_task_but_low_progress(self, strategy):
        goals = [{"id": "g1", "title": "Partial feature", "status": "active", "priority": 3, "progress": 50}]
        tasks = [{"goal_id": "g1", "status": "COMPLETED"}]
        output = await strategy.analyze(goals, tasks, None, [])
        assert len(output.suggested_tasks) >= 1

    @pytest.mark.asyncio
    async def test_generates_task_using_description(self, strategy):
        goals = [{
            "id": "g1", "title": "Goal title", "status": "active",
            "priority": 3, "progress": 0, "description": "Implement the user authentication module",
        }]
        output = await strategy.analyze(goals, [], None, [])
        assert "authentication" in output.suggested_tasks[0].title or "authentication" in output.suggested_tasks[0].description

    @pytest.mark.asyncio
    async def test_agent_suggestion_from_description(self, strategy):
        goals = [{
            "id": "g1", "title": "Some goal", "status": "active",
            "priority": 3, "progress": 0, "description": "Research and investigate the best approach",
        }]
        output = await strategy.analyze(goals, [], None, [])
        assert output.suggested_tasks[0].suggested_agent == "researcher"

    @pytest.mark.asyncio
    async def test_goal_tasks_map_excludes_tasks_without_goal_id(self, strategy):
        goals = [{"id": "g1", "title": "Active goal", "status": "active", "priority": 3, "progress": 0}]
        tasks = [{"status": "RUNNING"}, {"goal_id": "g1", "status": "COMPLETED"}]
        output = await strategy.analyze(goals, tasks, None, [])
        assert len(output.suggested_tasks) == 1

    @pytest.mark.asyncio
    async def test_multiple_goals_all_suggested(self, strategy):
        goals = [
            {"id": "g1", "title": "Build A", "status": "active", "priority": 5, "progress": 0},
            {"id": "g2", "title": "Build B", "status": "active", "priority": 3, "progress": 0},
            {"id": "g3", "title": "Build C", "status": "active", "priority": 1, "progress": 0},
        ]
        output = await strategy.analyze(goals, [], None, [])
        assert len(output.suggested_tasks) == 3
        assert {t.goal_id for t in output.suggested_tasks} == {"g1", "g2", "g3"}
