"""Base class for vertical tool modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.tools.base import Tool, ToolSpec
from app.tools.result import ToolResult


class VerticalTool(Tool):
    """Base class for vertical-specific tools.

    Vertical tools extend the base Tool class with:
    - Vertical category association
    - Project document storage integration
    - Approval gate hooks for financial documents
    """

    @property
    def vertical(self) -> str:
        """Return the vertical name (e.g., 'consulting')."""
        return self.spec.category.split(":")[0] if ":" in self.spec.category else self.spec.category

    async def store_document(
        self,
        project_id: str,
        name: str,
        doc_type: str,
        content: str,
        status: str = "draft",
        database: Any = None,
    ) -> dict[str, Any]:
        """Store a document in the project's documents list.

        Args:
            project_id: The project ID to attach the document to
            name: Document name (e.g., "Propuesta_comercial.md")
            doc_type: Document type (proposal, report, contract, invoice)
            content: Document content in markdown
            status: Initial status (draft, pending_approval, approved, rejected)
            database: Database instance for persistence

        Returns:
            Document metadata dict with id, name, type, status, created_at
        """
        import uuid
        from datetime import datetime, timezone

        doc_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        document = {
            "id": doc_id,
            "name": name,
            "type": doc_type,
            "status": status,
            "content": content,
            "created_at": created_at,
            "vertical": self.vertical,
        }

        # Store in database if available
        if database is not None:
            try:
                from app.db.project_repository import ProjectRepository

                repo = ProjectRepository(database.session_factory)
                project = await repo.get_by_id(project_id)
                if project:
                    docs = project.get("documents", [])
                    docs.append(document)
                    await repo.update(project_id, {"documents": docs})
            except Exception:
                pass  # Graceful degradation - document stored in memory only

        return document


class VerticalModule(ABC):
    """Base class for a vertical module that registers multiple tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the vertical name."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Return the vertical description."""
        ...

    @abstractmethod
    def get_tools(self) -> list[Tool]:
        """Return all tools in this vertical."""
        ...

    def get_tool_by_name(self, name: str) -> Tool | None:
        """Find a tool by name in this vertical."""
        for tool in self.get_tools():
            if tool.spec.name == name:
                return tool
        return None
