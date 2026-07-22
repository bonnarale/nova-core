"""Standardized ToolResult for every tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Standard result wrapper for all tool executions.

    Attributes:
        success: Whether the tool completed successfully.
        data: The output data produced by the tool.
        error: Error message if the tool failed.
        duration_ms: Execution duration in milliseconds.
        tool_name: Name of the tool that produced this result.
        metadata: Additional metadata (warnings, partial results, etc.).
    """

    success: bool = True
    data: Any = None
    error: str = ""
    duration_ms: float = 0.0
    tool_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "tool_name": self.tool_name,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def error_result(
        cls,
        tool_name: str,
        error: str,
        duration_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> ToolResult:
        return cls(
            success=False,
            data=None,
            error=error,
            duration_ms=duration_ms,
            tool_name=tool_name,
            metadata=metadata or {},
        )
