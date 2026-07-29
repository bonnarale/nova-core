"""Workflow factory — creates and wires all workflow components."""

from __future__ import annotations

import logging

from app.workflows.compiler import WorkflowCompiler
from app.workflows.dispatcher import WorkflowDispatcher
from app.workflows.lifecycle import WorkflowLifecycle
from app.workflows.metrics import WorkflowMetrics, get_workflow_metrics
from app.workflows.orchestrator import WorkflowOrchestrator
from app.workflows.persistence import InMemoryWorkflowPersistence
from app.workflows.tracing import WorkflowTracer
from app.workflows.validation import WorkflowValidator

logger = logging.getLogger(__name__)


class WorkflowFactory:
    """Factory that creates all workflow components and wires them together."""

    @staticmethod
    def create_orchestrator() -> WorkflowOrchestrator:
        """Create a fully wired WorkflowOrchestrator instance."""
        persistence = InMemoryWorkflowPersistence()
        compiler = WorkflowCompiler()
        validator = WorkflowValidator()
        dispatcher = WorkflowDispatcher()
        metrics = get_workflow_metrics()
        tracer = WorkflowTracer()
        lifecycle = WorkflowLifecycle()

        orchestrator = WorkflowOrchestrator(
            persistence=persistence,
            compiler=compiler,
            validator=validator,
            dispatcher=dispatcher,
            metrics=metrics,
            tracer=tracer,
            lifecycle=lifecycle,
        )
        logger.info("WorkflowFactory created orchestrator")
        return orchestrator

    @staticmethod
    def create_orchestrator_with_components() -> dict[str, Any]:
        """Create orchestrator and return all components."""
        orchestrator = WorkflowFactory.create_orchestrator()
        return {
            "orchestrator": orchestrator,
            "persistence": orchestrator.persistence,
            "compiler": orchestrator._compiler,
            "validator": orchestrator._validator,
            "dispatcher": orchestrator.dispatcher,
            "metrics": orchestrator.metrics,
            "tracer": orchestrator.tracer,
            "lifecycle": orchestrator.lifecycle,
        }


from typing import Any
