"""Tool Runtime exceptions."""

from __future__ import annotations


class ToolError(Exception):
    """Base exception for all tool errors."""

    def __init__(self, message: str, tool_name: str = "") -> None:
        self.tool_name = tool_name
        super().__init__(message)


class ToolNotFoundError(ToolError):
    """Raised when a tool is not registered."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Tool '{tool_name}' not found", tool_name=tool_name)


class ToolValidationError(ToolError):
    """Raised when input parameters fail validation."""

    def __init__(self, tool_name: str, message: str) -> None:
        super().__init__(message, tool_name=tool_name)


class ToolPermissionError(ToolError):
    """Raised when the caller lacks permission for the tool."""

    def __init__(self, tool_name: str, agent_id: str = "") -> None:
        msg = f"Agent '{agent_id}' lacks permission for tool '{tool_name}'"
        super().__init__(msg, tool_name=tool_name)
        self.agent_id = agent_id


class ToolTimeoutError(ToolError):
    """Raised when a tool execution times out."""

    def __init__(self, tool_name: str, timeout: float) -> None:
        super().__init__(
            f"Tool '{tool_name}' timed out after {timeout}s",
            tool_name=tool_name,
        )
        self.timeout = timeout


class ToolExecutionError(ToolError):
    """Raised when a tool execution itself fails."""

    def __init__(self, tool_name: str, message: str, cause: Exception | None = None) -> None:
        super().__init__(message, tool_name=tool_name)
        self.cause = cause
