"""WorkflowEngine — orchestrates workflow definition, execution, and lifecycle."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.workflows.base import ConditionEvaluator, RollbackHandler, StepHandler
from app.workflows.conditions import DefaultConditionEvaluator
from app.workflows.events import WorkflowEventBus
from app.workflows.executor import SequentialExecutor
from app.workflows.history import WorkflowHistory
from app.workflows.models import (
    WorkflowDefinition,
    WorkflowEventType,
    WorkflowExecution,
    WorkflowStatus,
)
from app.workflows.registry import StepHandlerRegistry, WorkflowRegistry
from app.workflows.scheduler import RetryManager, TimeoutManager
from app.workflows.state_machine import WorkflowStateMachine

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Orchestrates the full workflow lifecycle:
    define -> execute -> monitor -> pause/resume -> rollback.
    """

    def __init__(
        self,
        workflow_registry: WorkflowRegistry | None = None,
        step_handler_registry: StepHandlerRegistry | None = None,
        condition_evaluator: ConditionEvaluator | None = None,
        event_bus: WorkflowEventBus | None = None,
        history: WorkflowHistory | None = None,
        rollback_handler: RollbackHandler | None = None,
        retry_manager: RetryManager | None = None,
        timeout_manager: TimeoutManager | None = None,
    ) -> None:
        self._workflow_registry = workflow_registry or WorkflowRegistry()
        self._step_handler_registry = step_handler_registry or StepHandlerRegistry()
        self._condition_evaluator = condition_evaluator or DefaultConditionEvaluator()
        self._event_bus = event_bus or WorkflowEventBus()
        self._history = history or WorkflowHistory()
        self._rollback_handler = rollback_handler
        self._retry_manager = retry_manager or RetryManager()
        self._timeout_manager = timeout_manager or TimeoutManager()
        self._executor = SequentialExecutor(
            step_handlers=self._step_handler_registry.handlers,
            condition_evaluator=self._condition_evaluator,
        )

    @property
    def workflow_registry(self) -> WorkflowRegistry:
        return self._workflow_registry

    @property
    def step_handler_registry(self) -> StepHandlerRegistry:
        return self._step_handler_registry

    @property
    def event_bus(self) -> WorkflowEventBus:
        return self._event_bus

    @property
    def history(self) -> WorkflowHistory:
        return self._history

    # ------------------------------------------------------------------
    # Workflow definition management
    # ------------------------------------------------------------------

    def register_workflow(self, definition: WorkflowDefinition) -> None:
        self._workflow_registry.register(definition)

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        return self._workflow_registry.get(workflow_id)

    def list_workflows(self) -> list[WorkflowDefinition]:
        return self._workflow_registry.list()

    def register_step_handler(self, handler: StepHandler) -> None:
        self._step_handler_registry.register(handler)

    # ------------------------------------------------------------------
    # Execution lifecycle
    # ------------------------------------------------------------------

    async def create_execution(
        self,
        workflow_id: str,
        input_data: dict[str, Any] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        definition = self._workflow_registry.get(workflow_id)
        if definition is None:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        execution = WorkflowExecution(
            id=str(uuid4()),
            workflow_id=workflow_id,
            workflow_name=definition.name,
            status=WorkflowStatus.PENDING,
            input=input_data or {},
            user_id=user_id,
            session_id=session_id,
            tags=tags or [],
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._history.record(execution)
        self._event_bus.publish(
            WorkflowEventType.CREATED,
            execution.id,
            payload={"workflow_id": workflow_id},
        )
        return execution

    async def start_execution(self, execution_id: str) -> WorkflowExecution:
        execution = self._history.get(execution_id)
        if execution is None:
            raise ValueError(f"Execution '{execution_id}' not found")

        WorkflowStateMachine.assert_can_transition_workflow(
            execution.status, WorkflowStatus.RUNNING
        )
        execution.status = WorkflowStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc).isoformat()

        definition = self._workflow_registry.get(execution.workflow_id)
        if definition is None:
            raise ValueError(f"Workflow '{execution.workflow_id}' not found")

        self._event_bus.publish(
            WorkflowEventType.STARTED, execution.id,
            payload={"workflow_name": definition.name},
        )

        try:
            execution = await self._executor.execute(definition, execution)
            self._history.record(execution)

            if execution.error:
                execution.status = WorkflowStatus.FAILED
                self._event_bus.publish(
                    WorkflowEventType.FAILED, execution.id,
                    payload={"error": execution.error},
                )
            else:
                execution.status = WorkflowStatus.COMPLETED
                self._event_bus.publish(
                    WorkflowEventType.COMPLETED, execution.id,
                )
        except Exception as exc:
            logger.exception("Workflow execution %s failed: %s", execution_id, exc)
            execution.status = WorkflowStatus.FAILED
            execution.error = str(exc)
            self._event_bus.publish(
                WorkflowEventType.FAILED, execution.id,
                payload={"error": str(exc)},
            )

        execution.completed_at = datetime.now(timezone.utc).isoformat()
        self._history.record(execution)
        return execution

    async def pause_execution(self, execution_id: str) -> WorkflowExecution:
        execution = self._history.get(execution_id)
        if execution is None:
            raise ValueError(f"Execution '{execution_id}' not found")

        WorkflowStateMachine.assert_can_transition_workflow(
            execution.status, WorkflowStatus.PAUSED
        )
        execution.status = WorkflowStatus.PAUSED
        self._history.record(execution)
        self._event_bus.publish(WorkflowEventType.PAUSED, execution.id)
        return execution

    async def resume_execution(self, execution_id: str) -> WorkflowExecution:
        execution = self._history.get(execution_id)
        if execution is None:
            raise ValueError(f"Execution '{execution_id}' not found")

        WorkflowStateMachine.assert_can_transition_workflow(
            execution.status, WorkflowStatus.RUNNING
        )
        execution.status = WorkflowStatus.RUNNING
        self._history.record(execution)
        self._event_bus.publish(WorkflowEventType.RESUMED, execution.id)
        return execution

    async def cancel_execution(self, execution_id: str) -> WorkflowExecution:
        execution = self._history.get(execution_id)
        if execution is None:
            raise ValueError(f"Execution '{execution_id}' not found")

        WorkflowStateMachine.assert_can_transition_workflow(
            execution.status, WorkflowStatus.CANCELLED
        )
        execution.status = WorkflowStatus.CANCELLED
        execution.completed_at = datetime.now(timezone.utc).isoformat()
        self._history.record(execution)
        self._event_bus.publish(WorkflowEventType.CANCELLED, execution.id)
        return execution

    async def rollback_execution(self, execution_id: str) -> WorkflowExecution:
        execution = self._history.get(execution_id)
        if execution is None:
            raise ValueError(f"Execution '{execution_id}' not found")

        WorkflowStateMachine.assert_can_transition_workflow(
            execution.status, WorkflowStatus.ROLLING_BACK
        )
        execution.status = WorkflowStatus.ROLLING_BACK
        self._event_bus.publish(WorkflowEventType.ROLLING_BACK, execution.id)

        if self._rollback_handler:
            execution = await self._rollback_handler.rollback(
                execution,
                self._workflow_registry.get(execution.workflow_id),
            )

        execution.status = WorkflowStatus.ROLLED_BACK
        execution.completed_at = datetime.now(timezone.utc).isoformat()
        self._history.record(execution)
        self._event_bus.publish(WorkflowEventType.ROLLED_BACK, execution.id)
        return execution

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        return self._history.get(execution_id)

    def list_executions(
        self,
        workflow_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkflowExecution]:
        return self._history.list(
            workflow_id=workflow_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    def get_events(self, execution_id: str | None = None) -> list:
        return self._event_bus.get_events(execution_id)
