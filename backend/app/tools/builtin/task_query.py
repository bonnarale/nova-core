"""TaskQueryTool — query and manage tasks."""

from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.result import ToolResult


class TaskQueryTool(Tool):
    """Query and interact with the task management system."""

    def __init__(self, task_manager: Any = None) -> None:
        self._task_manager = task_manager

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="task_query",
            description="Query and manage tasks — list, get, check status, and dependencies.",
            category="retrieval",
            tool_id="task_query",
            version="1.0.0",
            capabilities=["task", "query", "management"],
            tags=["task", "query", "orchestration"],
            policy="immediate",
            timeout_default=10.0,
            retry_default=0,
            permission_level="read",
            parameters=[
                ToolParam(name="operation", type="string", required=True, description="One of: list, get, status"),
                ToolParam(name="task_id", type="string", required=False, description="Task ID (for get/status)"),
                ToolParam(name="status_filter", type="string", required=False, description="Filter by status"),
                ToolParam(name="limit", type="integer", required=False, description="Max results"),
            ],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        operation = params.get("operation", "")

        if not self._task_manager:
            return ToolResult(
                success=True,
                data={"results": [], "message": "Task manager not configured"},
                metadata={"stub": True},
            )

        try:
            if operation == "list":
                return await self._list_tasks(params)
            elif operation == "get":
                return await self._get_task(params)
            elif operation == "status":
                return await self._task_status(params)
            else:
                return ToolResult.error_result("task_query", f"Unknown operation: {operation}")
        except Exception as exc:
            return ToolResult.error_result("task_query", f"Task query failed: {exc}")

    async def _list_tasks(self, params: dict[str, Any]) -> ToolResult:
        status_filter = params.get("status_filter")
        limit = params.get("limit", 50)
        tasks = await self._task_manager.list_tasks(status=status_filter, limit=limit)
        return ToolResult(
            success=True,
            data={"tasks": tasks, "total": len(tasks)},
        )

    async def _get_task(self, params: dict[str, Any]) -> ToolResult:
        from uuid import UUID
        task_id = params.get("task_id", "")
        if not task_id:
            return ToolResult.error_result("task_query", "task_id is required for get")
        task = await self._task_manager.get_task(UUID(task_id))
        if task is None:
            return ToolResult.error_result("task_query", f"Task {task_id} not found")
        return ToolResult(success=True, data=task)

    async def _task_status(self, params: dict[str, Any]) -> ToolResult:
        from uuid import UUID
        task_id = params.get("task_id", "")
        if not task_id:
            return ToolResult.error_result("task_query", "task_id is required for status")
        task = await self._task_manager.get_task(UUID(task_id))
        if task is None:
            return ToolResult.error_result("task_query", f"Task {task_id} not found")
        return ToolResult(
            success=True,
            data={"task_id": task_id, "status": task.get("status")},
        )
