"""MemorySearchTool — search conversation and semantic memory."""

from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.result import ToolResult


class MemorySearchTool(Tool):
    """Search conversation memory and semantic memory for relevant context."""

    def __init__(self, memory: Any = None, semantic_memory: Any = None) -> None:
        self._memory = memory
        self._semantic_memory = semantic_memory

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="memory_search",
            description="Search conversation and semantic memory for relevant information.",
            category="retrieval",
            tool_id="memory_search",
            version="1.0.0",
            capabilities=["memory", "search", "retrieval"],
            tags=["memory", "search", "semantic"],
            policy="immediate",
            timeout_default=10.0,
            retry_default=1,
            permission_level="read",
            parameters=[
                ToolParam(name="query", type="string", required=True, description="Search query"),
                ToolParam(name="scope", type="string", required=False, description="Memory scope: conversation, semantic, or all"),
                ToolParam(name="limit", type="integer", required=False, description="Max results to return (default: 10)"),
                ToolParam(name="session_id", type="string", required=False, description="Session ID to scope search"),
            ],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        query = params.get("query", "")
        if not query:
            return ToolResult.error_result("memory_search", "query is required")

        scope = params.get("scope", "all")
        limit = params.get("limit", 10)

        results: list[dict[str, Any]] = []

        if scope in ("conversation", "all") and self._memory:
            try:
                conv_results = await self._search_conversation(query, limit)
                results.extend(conv_results)
            except Exception:
                pass

        if scope in ("semantic", "all") and self._semantic_memory:
            try:
                sem_results = await self._search_semantic(query, limit)
                results.extend(sem_results)
            except Exception:
                pass

        if not results and not self._memory and not self._semantic_memory:
            return ToolResult(
                success=True,
                data={"results": [], "total": 0, "message": "No memory backends configured"},
                metadata={"stub": True},
            )

        return ToolResult(
            success=True,
            data={"results": results[:limit], "total": len(results)},
        )

    async def _search_conversation(self, query: str, limit: int) -> list[dict[str, Any]]:
        if hasattr(self._memory, "search"):
            return await self._memory.search(query, limit=limit)
        return []

    async def _search_semantic(self, query: str, limit: int) -> list[dict[str, Any]]:
        if hasattr(self._semantic_memory, "search"):
            return await self._semantic_memory.search(query, limit=limit)
        return []
