"""Workflow orchestrator — high-level orchestration of workflow execution."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.workflows.compiler import WorkflowCompiler
from app.workflows.context import WorkflowContext
from app.workflows.dispatcher import WorkflowDispatcher
from app.workflows.graph import WorkflowGraph
from app.workflows.lifecycle import WorkflowLifecycle, WorkflowLifecycleState
from app.workflows.metrics import WorkflowMetrics, get_workflow_metrics
from app.workflows.models import WorkflowDefinition, WorkflowExecution, WorkflowStatus
from app.workflows.node import NodeType, NodeStatus, WorkflowNode
from app.workflows.persistence import InMemoryWorkflowPersistence
from app.workflows.tracing import WorkflowTracer
from app.workflows.validation import WorkflowValidator

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """High-level orchestrator for creating, validating, compiling, and executing workflows."""

    def __init__(
        self,
        persistence: InMemoryWorkflowPersistence | None = None,
        compiler: WorkflowCompiler | None = None,
        validator: WorkflowValidator | None = None,
        dispatcher: WorkflowDispatcher | None = None,
        metrics: WorkflowMetrics | None = None,
        tracer: WorkflowTracer | None = None,
        lifecycle: WorkflowLifecycle | None = None,
    ) -> None:
        self._lifecycle = lifecycle or WorkflowLifecycle()
        self._persistence = persistence or InMemoryWorkflowPersistence()
        self._compiler = compiler or WorkflowCompiler()
        self._validator = validator or WorkflowValidator()
        self._dispatcher = dispatcher or WorkflowDispatcher()
        self._metrics = metrics or get_workflow_metrics()
        self._tracer = tracer or WorkflowTracer()
        self._lifecycle.transition(WorkflowLifecycleState.INITIALIZED)

    @property
    def lifecycle(self) -> WorkflowLifecycle:
        return self._lifecycle

    @property
    def persistence(self) -> InMemoryWorkflowPersistence:
        return self._persistence

    @property
    def dispatcher(self) -> WorkflowDispatcher:
        return self._dispatcher

    @property
    def metrics(self) -> WorkflowMetrics:
        return self._metrics

    @property
    def tracer(self) -> WorkflowTracer:
        return self._tracer

    async def start(self) -> None:
        self._lifecycle.transition(WorkflowLifecycleState.READY)
        self._lifecycle.transition(WorkflowLifecycleState.RUNNING)
        await self._dispatcher.start()

    async def stop(self) -> None:
        await self._dispatcher.stop()
        self._lifecycle.transition(WorkflowLifecycleState.CANCELLED)

    async def shutdown(self) -> None:
        await self._dispatcher.stop()
        self._lifecycle.transition(WorkflowLifecycleState.SHUTDOWN)

    async def create_workflow(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        span = self._tracer.start_span("create_workflow")
        span.set_attribute("workflow_name", definition.name)
        try:
            if not definition.id:
                definition.id = str(uuid4())
            await self._persistence.store_definition(definition)
            self._metrics.record_created()
            self._tracer.end_span(span)
            return definition
        except Exception as e:
            span.set_error(str(e))
            self._tracer.end_span(span)
            raise

    async def update_workflow(self, workflow_id: str, updates: dict[str, Any]) -> WorkflowDefinition | None:
        definition = await self._persistence.get_definition(workflow_id)
        if definition is None:
            return None
        for key, val in updates.items():
            if hasattr(definition, key) and val is not None:
                setattr(definition, key, val)
        await self._persistence.update_definition(definition)
        self._compiler.invalidate(workflow_id)
        return definition

    async def delete_workflow(self, workflow_id: str) -> bool:
        self._compiler.invalidate(workflow_id)
        return await self._persistence.delete_definition(workflow_id)

    async def validate_workflow(self, definition: WorkflowDefinition) -> tuple[bool, list[str]]:
        return self._validator.validate_definition(definition.to_dict())

    async def compile_workflow(self, workflow_id: str) -> WorkflowGraph | None:
        definition = await self._persistence.get_definition(workflow_id)
        if definition is None:
            return None
        steps = []
        for s in definition.steps:
            if hasattr(s, "to_dict"):
                steps.append(s.to_dict())
            elif isinstance(s, dict):
                steps.append(s)
        return self._compiler.compile_from_steps(steps, workflow_id)

    async def execute_workflow(self, workflow_id: str, input_data: dict[str, Any] | None = None, user_id: str | None = None) -> WorkflowExecution:
        span = self._tracer.start_span("execute_workflow")
        span.set_attribute("workflow_id", workflow_id)
        definition = await self._persistence.get_definition(workflow_id)
        if definition is None:
            span.set_error("Workflow not found")
            self._tracer.end_span(span)
            raise ValueError(f"Workflow '{workflow_id}' not found")

        execution = WorkflowExecution(
            id=str(uuid4()),
            workflow_id=workflow_id,
            workflow_name=definition.name,
            status=WorkflowStatus.RUNNING,
            input=input_data or {},
            user_id=user_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        await self._persistence.store_execution(execution)

        context = WorkflowContext(workflow_id=workflow_id, execution_id=execution.id, input_data=input_data)

        start_time = __import__("time").monotonic()
        try:
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc).isoformat()
            elapsed = (__import__("time").monotonic() - start_time) * 1000
            execution.duration_ms = elapsed
            self._metrics.record_executed(elapsed)
            self._metrics.record_success()
            await self._persistence.update_execution(execution)
            self._tracer.end_span(span)
            return execution
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.now(timezone.utc).isoformat()
            self._metrics.record_failure()
            await self._persistence.update_execution(execution)
            span.set_error(str(e))
            self._tracer.end_span(span)
            raise

    async def pause_workflow(self, execution_id: str) -> WorkflowExecution | None:
        execution = await self._persistence.get_execution(execution_id)
        if execution is None:
            return None
        if execution.status != WorkflowStatus.RUNNING:
            return None
        execution.status = WorkflowStatus.PAUSED
        await self._persistence.update_execution(execution)
        return execution

    async def resume_workflow(self, execution_id: str) -> WorkflowExecution | None:
        execution = await self._persistence.get_execution(execution_id)
        if execution is None:
            return None
        if execution.status != WorkflowStatus.PAUSED:
            return None
        execution.status = WorkflowStatus.RUNNING
        await self._persistence.update_execution(execution)
        return execution

    async def cancel_workflow(self, execution_id: str) -> WorkflowExecution | None:
        execution = await self._persistence.get_execution(execution_id)
        if execution is None:
            return None
        execution.status = WorkflowStatus.CANCELLED
        execution.completed_at = datetime.now(timezone.utc).isoformat()
        await self._persistence.update_execution(execution)
        return execution

    async def replay_workflow(self, execution_id: str) -> WorkflowExecution | None:
        original = await self._persistence.get_execution(execution_id)
        if original is None:
            return None
        return await self.execute_workflow(original.workflow_id, original.input, original.user_id)

    async def clone_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        definition = await self._persistence.get_definition(workflow_id)
        if definition is None:
            return None
        import copy
        cloned = copy.deepcopy(definition)
        cloned.id = str(uuid4())
        cloned.name = f"{definition.name} (copy)"
        await self._persistence.store_definition(cloned)
        return cloned

    async def export_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        definition = await self._persistence.get_definition(workflow_id)
        if definition is None:
            return None
        return definition.to_dict()

    async def import_workflow(self, data: dict[str, Any]) -> WorkflowDefinition:
        definition = WorkflowDefinition(
            id=str(uuid4()),
            name=data.get("name", "Imported"),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )
        return await self.create_workflow(definition)

    async def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        return await self._persistence.get_definition(workflow_id)

    async def list_workflows(self, tag: str | None = None, limit: int = 100, offset: int = 0) -> list[WorkflowDefinition]:
        return await self._persistence.list_definitions(tag=tag, limit=limit, offset=offset)

    async def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        return await self._persistence.get_execution(execution_id)

    async def list_executions(self, workflow_id: str | None = None, status: str | None = None, limit: int = 100, offset: int = 0) -> list[WorkflowExecution]:
        return await self._persistence.list_executions(workflow_id=workflow_id, status=status, limit=limit, offset=offset)

    async def get_statistics(self) -> dict[str, Any]:
        def_count = await self._persistence.count_definitions()
        exec_count = await self._persistence.count_executions()
        return {
            "total_definitions": def_count,
            "total_executions": exec_count,
            "metrics": self._metrics.to_dict(),
        }

    def get_metrics_dict(self) -> dict[str, Any]:
        return self._metrics.to_dict()

    def get_traces_dict(self, limit: int = 100) -> dict[str, Any]:
        return self._tracer.to_dict(limit=limit)
