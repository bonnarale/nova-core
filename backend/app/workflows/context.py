"""Workflow execution context — shared state during workflow execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.workflows.variables import VariableScope, VariableStore


@dataclass
class Checkpoint:
    checkpoint_id: str = ""
    step_id: str = ""
    timestamp: str = ""
    state: dict[str, Any] = field(default_factory=dict)


class WorkflowContext:
    """Execution context carrying variables, state, and checkpoints."""

    def __init__(
        self,
        workflow_id: str = "",
        execution_id: str = "",
        input_data: dict[str, Any] | None = None,
    ) -> None:
        self.workflow_id = workflow_id
        self.execution_id = execution_id
        self._variables = VariableStore()
        self._state: dict[str, Any] = {}
        self._checkpoints: list[Checkpoint] = []
        self._output: dict[str, Any] = {}
        self._errors: list[dict[str, Any]] = []
        self._started_at = datetime.now(timezone.utc)

        if input_data:
            for key, val in input_data.items():
                self._variables.set_execution(key, val)

    @property
    def variables(self) -> VariableStore:
        return self._variables

    @property
    def output(self) -> dict[str, Any]:
        return self._output

    @property
    def state(self) -> dict[str, Any]:
        return self._state

    @property
    def errors(self) -> list[dict[str, Any]]:
        return list(self._errors)

    def set_variable(self, name: str, value: Any, scope: VariableScope = VariableScope.EXECUTION) -> None:
        self._variables.set(name, value, scope)

    def get_variable(self, name: str, default: Any = None) -> Any:
        return self._variables.get(name, default)

    def set_output(self, key: str, value: Any) -> None:
        self._output[key] = value

    def set_state(self, key: str, value: Any) -> None:
        self._state[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def record_error(self, step_id: str, error: str) -> None:
        self._errors.append({
            "step_id": step_id,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def save_checkpoint(self, step_id: str) -> Checkpoint:
        checkpoint = Checkpoint(
            checkpoint_id=f"cp-{len(self._checkpoints)}",
            step_id=step_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            state=dict(self._state),
        )
        self._checkpoints.append(checkpoint)
        return checkpoint

    def get_last_checkpoint(self) -> Checkpoint | None:
        return self._checkpoints[-1] if self._checkpoints else None

    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        for cp in self._checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                self._state = dict(cp.state)
                return True
        return False

    def get_all_checkpoints(self) -> list[Checkpoint]:
        return list(self._checkpoints)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "variables": {
                "global": self._variables.get_all_global(),
                "workflow": self._variables.get_all_workflow(),
                "execution": self._variables.get_all_execution(),
            },
            "state": self._state,
            "output": self._output,
            "errors": self._errors,
            "checkpoints": len(self._checkpoints),
        }
