"""Abstract Tool base class for NOVA CORE Tool Runtime."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.tools.result import ToolResult


@dataclass
class ToolParam:
    """Parameter specification for a tool."""

    name: str
    type: str  # "string", "integer", "boolean", "list", "dict"
    required: bool = False
    description: str = ""
    default: Any = None


@dataclass
class ToolSpec:
    """Specification / metadata for a tool.

    This is the declarative contract that agents use to discover
    what a tool does and what parameters it expects.
    """

    name: str
    description: str = ""
    category: str = "general"
    parameters: list[ToolParam] = field(default_factory=list)
    timeout_default: float = 30.0
    retry_default: int = 0
    permission_level: str = "read"
    tool_id: str = ""
    version: str = "1.0.0"
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    policy: str = "immediate"

    def __post_init__(self) -> None:
        if not self.tool_id:
            self.tool_id = self.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "required": p.required,
                    "description": p.description,
                    "default": p.default,
                }
                for p in self.parameters
            ],
            "input_schema": dict(self.input_schema),
            "output_schema": dict(self.output_schema),
            "capabilities": list(self.capabilities),
            "tags": list(self.tags),
            "policy": self.policy,
            "timeout_default": self.timeout_default,
            "retry_default": self.retry_default,
            "permission_level": self.permission_level,
        }


class Tool(ABC):
    """Abstract base for all tools.

    Subclasses must implement:
    - ``spec`` property returning a ToolSpec.
    - ``run(params)`` coroutine performing the actual work.

    Lifecycle hooks (optional):
    - ``before_run(params)``
    - ``after_run(result)``
    - ``initialize()``
    - ``shutdown()``
    - ``cancel()``
    - ``health()``
    """

    @property
    @abstractmethod
    def spec(self) -> ToolSpec:
        """Return the tool's specification."""
        ...

    @abstractmethod
    async def run(self, params: dict[str, Any]) -> ToolResult:
        """Execute the tool with the given parameters.

        Must return a ``ToolResult`` instance.
        """
        ...

    async def before_run(self, params: dict[str, Any]) -> dict[str, Any]:
        """Hook called before execution. Can mutate params."""
        return params

    async def after_run(self, result: ToolResult) -> ToolResult:
        """Hook called after execution. Can mutate result."""
        return result

    async def initialize(self) -> None:
        """Called once after registration."""

    async def shutdown(self) -> None:
        """Called once before the tool is torn down."""

    async def cancel(self) -> bool:
        """Request graceful cancellation. Returns True if cancelled."""
        return False

    async def health(self) -> dict[str, Any]:
        """Return health status."""
        return {"tool_id": self.spec.tool_id, "status": "healthy"}

    def validate(self, params: dict[str, Any]) -> None:
        """Validate input parameters against the spec.

        Raises ``ToolValidationError`` on failure.
        """
        from app.tools.exceptions import ToolValidationError

        spec = self.spec
        for param in spec.parameters:
            if param.required and param.name not in params:
                raise ToolValidationError(
                    tool_name=spec.name,
                    message=f"Missing required parameter '{param.name}'",
                )
            if param.name in params:
                val = params[param.name]
                if param.type == "string" and not isinstance(val, str):
                    raise ToolValidationError(
                        tool_name=spec.name,
                        message=f"Parameter '{param.name}' must be a string, got {type(val).__name__}",
                    )
                if param.type == "integer" and not isinstance(val, int):
                    raise ToolValidationError(
                        tool_name=spec.name,
                        message=f"Parameter '{param.name}' must be an integer, got {type(val).__name__}",
                    )
                if param.type == "boolean" and not isinstance(val, bool):
                    raise ToolValidationError(
                        tool_name=spec.name,
                        message=f"Parameter '{param.name}' must be a boolean, got {type(val).__name__}",
                    )

        if spec.input_schema:
            from app.tools.schema import validate_schema
            validate_schema(params, spec.input_schema, tool_name=spec.name)

    async def execute(
        self,
        params: dict[str, Any],
        timeout: float | None = None,
    ) -> ToolResult:
        """Full execution lifecycle: validate -> before -> run -> after.

        This is the primary entry point used by ``ToolExecutor``.
        """
        self.validate(params)
        params = await self.before_run(params)
        result = await self.run(params)
        result = await self.after_run(result)
        return result
