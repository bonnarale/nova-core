"""KnowledgeSearchTool — search the knowledge graph."""

from __future__ import annotations

from typing import Any

from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.result import ToolResult


class KnowledgeSearchTool(Tool):
    """Search the knowledge graph for entities, relationships, and context."""

    def __init__(self, knowledge_engine: Any = None) -> None:
        self._engine = knowledge_engine

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="knowledge_search",
            description="Search the knowledge graph for entities, relationships, and contextual information.",
            category="retrieval",
            tool_id="knowledge_search",
            version="1.0.0",
            capabilities=["knowledge", "search", "graph", "entity", "relationship"],
            tags=["knowledge", "search", "graph"],
            policy="immediate",
            timeout_default=10.0,
            retry_default=1,
            permission_level="read",
            parameters=[
                ToolParam(name="query", type="string", required=True, description="Search query"),
                ToolParam(name="search_type", type="string", required=False, description="Search type: entity, relationship, context"),
                ToolParam(name="limit", type="integer", required=False, description="Max results (default: 10)"),
            ],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        query = params.get("query", "")
        if not query:
            return ToolResult.error_result("knowledge_search", "query is required")

        if not self._engine:
            return ToolResult(
                success=True,
                data={"results": [], "total": 0, "message": "Knowledge engine not configured"},
                metadata={"stub": True},
            )

        search_type = params.get("search_type", "context")
        limit = params.get("limit", 10)

        try:
            if search_type == "entity" and hasattr(self._engine, "search_entities"):
                results = await self._engine.search_entities(query, limit=limit)
            elif search_type == "relationship" and hasattr(self._engine, "search_relationships"):
                results = await self._engine.search_relationships(query, limit=limit)
            elif hasattr(self._engine, "search"):
                results = await self._engine.search(query, limit=limit)
            else:
                results = []

            if isinstance(results, list):
                data_results = [r.to_dict() if hasattr(r, "to_dict") else r for r in results]
            else:
                data_results = [results]

            return ToolResult(
                success=True,
                data={"results": data_results, "total": len(data_results), "search_type": search_type},
            )

        except Exception as exc:
            return ToolResult.error_result("knowledge_search", f"Search failed: {exc}")
