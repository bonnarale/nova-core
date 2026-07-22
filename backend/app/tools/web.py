"""WebSearchTool — search the web (stub interface only).

Per the requirements, this is a stub / interface that provides the
contract for web search without a concrete implementation.
"""

from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.result import ToolResult


class WebSearchTool(Tool):
    """Search the web.

    NOTE: This is a **stub** that returns a placeholder result.
    A concrete implementation (e.g. using a search API) should
    replace this in production.
    """

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="web_search",
            description="Search the web for information. Stub — returns placeholder results.",
            category="network",
            timeout_default=15.0,
            retry_default=1,
            permission_level="read",
            parameters=[
                ToolParam(name="query", type="string", required=True, description="Search query string"),
                ToolParam(name="num_results", type="integer", required=False, description="Number of results to return (default: 5)"),
                ToolParam(name="source", type="string", required=False, description="Search source (web, news, academic)"),
            ],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        query = params.get("query", "")
        if not query:
            return ToolResult.error_result("web_search", "query is required")

        return ToolResult(
            success=True,
            data={
                "query": query,
                "results": [],
                "total_results": 0,
                "message": "WebSearchTool is a stub — no search backend configured.",
            },
            metadata={"stub": True},
        )
