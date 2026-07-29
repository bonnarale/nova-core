"""Registries for workflow definitions and step handlers."""

from __future__ import annotations

from typing import Any

from app.workflows.base import StepHandler
from app.workflows.models import WorkflowDefinition, WorkflowStep


class WorkflowRegistry:
    """Registry of available workflow definitions."""

    def __init__(self) -> None:
        self._definitions: dict[str, WorkflowDefinition] = {}

    @property
    def definitions(self) -> dict[str, WorkflowDefinition]:
        return dict(self._definitions)

    def register(self, definition: WorkflowDefinition) -> None:
        self._definitions[definition.id] = definition

    def unregister(self, workflow_id: str) -> None:
        self._definitions.pop(workflow_id, None)

    def get(self, workflow_id: str) -> WorkflowDefinition | None:
        return self._definitions.get(workflow_id)

    def list(self) -> list[WorkflowDefinition]:
        return list(self._definitions.values())

    def find_by_tag(self, tag: str) -> list[WorkflowDefinition]:
        return [w for w in self._definitions.values() if tag in w.tags]


class StepHandlerRegistry:
    """Registry of available step handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, StepHandler] = {}

    @property
    def handlers(self) -> dict[str, StepHandler]:
        return dict(self._handlers)

    def register(self, handler: StepHandler) -> None:
        self._handlers[handler.handler_name] = handler

    def unregister(self, name: str) -> None:
        self._handlers.pop(name, None)

    def get(self, name: str) -> StepHandler | None:
        return self._handlers.get(name)

    def find_handler(self, step: WorkflowStep) -> StepHandler | None:
        return self._handlers.get(step.handler) or self._find_matching(step)

    def _find_matching(self, step: WorkflowStep) -> StepHandler | None:
        for handler in self._handlers.values():
            if handler.can_handle(step):
                return handler
        return None
