"""GoalQueryTool — query and manage goals."""

from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.result import ToolResult


class GoalQueryTool(Tool):
    """Query and interact with the goal management system."""

    def __init__(self, goal_manager: Any = None) -> None:
        self._goal_manager = goal_manager

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="goal_query",
            description="Query and manage goals — list, get, check status, and progress.",
            category="retrieval",
            tool_id="goal_query",
            version="1.0.0",
            capabilities=["goal", "query", "management"],
            tags=["goal", "query", "planning"],
            policy="immediate",
            timeout_default=10.0,
            retry_default=0,
            permission_level="read",
            parameters=[
                ToolParam(name="operation", type="string", required=True, description="One of: list, get, status"),
                ToolParam(name="goal_id", type="string", required=False, description="Goal ID (for get/status)"),
                ToolParam(name="user_id", type="string", required=False, description="User ID (for list)"),
                ToolParam(name="status_filter", type="string", required=False, description="Filter by status"),
            ],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        operation = params.get("operation", "")

        if not self._goal_manager:
            return ToolResult(
                success=True,
                data={"results": [], "message": "Goal manager not configured"},
                metadata={"stub": True},
            )

        try:
            if operation == "list":
                return await self._list_goals(params)
            elif operation == "get":
                return await self._get_goal(params)
            elif operation == "status":
                return await self._goal_status(params)
            else:
                return ToolResult.error_result("goal_query", f"Unknown operation: {operation}")
        except Exception as exc:
            return ToolResult.error_result("goal_query", f"Goal query failed: {exc}")

    async def _list_goals(self, params: dict[str, Any]) -> ToolResult:
        from uuid import UUID
        user_id = params.get("user_id", "")
        status_filter = params.get("status_filter")
        if not user_id:
            return ToolResult.error_result("goal_query", "user_id is required for list")
        goals = await self._goal_manager.list_goals(UUID(user_id), status=status_filter)
        return ToolResult(
            success=True,
            data={"goals": goals, "total": len(goals)},
        )

    async def _get_goal(self, params: dict[str, Any]) -> ToolResult:
        from uuid import UUID
        goal_id = params.get("goal_id", "")
        if not goal_id:
            return ToolResult.error_result("goal_query", "goal_id is required for get")
        goal = await self._goal_manager.get_goal(UUID(goal_id))
        if goal is None:
            return ToolResult.error_result("goal_query", f"Goal {goal_id} not found")
        return ToolResult(success=True, data=goal)

    async def _goal_status(self, params: dict[str, Any]) -> ToolResult:
        from uuid import UUID
        goal_id = params.get("goal_id", "")
        if not goal_id:
            return ToolResult.error_result("goal_query", "goal_id is required for status")
        goal = await self._goal_manager.get_goal(UUID(goal_id))
        if goal is None:
            return ToolResult.error_result("goal_query", f"Goal {goal_id} not found")
        return ToolResult(
            success=True,
            data={"goal_id": goal_id, "status": goal.get("status"), "progress": goal.get("progress")},
        )
