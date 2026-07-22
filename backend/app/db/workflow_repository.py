"""SQLAlchemy-based repository for Workflow ORM models."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import WorkflowDefinitionModel, WorkflowEventModel, WorkflowExecutionModel
from app.workflows.models import (
    WorkflowDefinition,
    WorkflowEvent,
    WorkflowEventType,
    WorkflowExecution,
    WorkflowStatus,
)


class WorkflowDbRepository:
    """Postgres-backed persistence for workflow definitions and executions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # --- Definitions ---

    async def save_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        async with self._session_factory() as session:
            model = WorkflowDefinitionModel(
                id=UUID(definition.id) if isinstance(definition.id, str) else definition.id,
                name=definition.name,
                description=definition.description,
                version=definition.version,
                steps=[s.to_dict() for s in definition.steps],
                input_schema=definition.input_schema,
                output_schema=definition.output_schema,
                tags=definition.tags,
                metadata_=definition.metadata,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._definition_from_orm(model)

    async def get_definition(self, workflow_id: str) -> WorkflowDefinition | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(WorkflowDefinitionModel).where(
                    WorkflowDefinitionModel.id == UUID(workflow_id)
                )
            )
            model = result.scalar_one_or_none()
            return self._definition_from_orm(model) if model else None

    async def list_definitions(
        self,
        tag: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkflowDefinition]:
        async with self._session_factory() as session:
            query = select(WorkflowDefinitionModel).order_by(
                WorkflowDefinitionModel.created_at.desc()
            )
            if tag:
                query = query.where(
                    WorkflowDefinitionModel.tags.contains([tag])
                )
            query = query.offset(offset).limit(limit)
            result = await session.execute(query)
            return [self._definition_from_orm(m) for m in result.scalars().all()]

    async def delete_definition(self, workflow_id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                select(WorkflowDefinitionModel).where(
                    WorkflowDefinitionModel.id == UUID(workflow_id)
                )
            )
            model = result.scalar_one_or_none()
            if model is None:
                return False
            await session.delete(model)
            await session.commit()
            return True

    # --- Executions ---

    async def save_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        async with self._session_factory() as session:
            existing = await session.execute(
                select(WorkflowExecutionModel).where(
                    WorkflowExecutionModel.id == UUID(execution.id)
                )
            )
            model = existing.scalar_one_or_none()

            if model:
                model.status = execution.status.value
                model.output_ = execution.output
                model.error = execution.error
                model.current_step_id = execution.current_step_id
                model.step_executions = [s.to_dict() for s in execution.step_executions]
                model.context = execution.context
            else:
                model = WorkflowExecutionModel(
                    id=UUID(execution.id),
                    workflow_id=UUID(execution.workflow_id) if execution.workflow_id else None,
                    workflow_name=execution.workflow_name,
                    status=execution.status.value,
                    input_=execution.input,
                    output_=execution.output,
                    error=execution.error,
                    current_step_id=execution.current_step_id,
                    step_executions=[s.to_dict() for s in execution.step_executions],
                    context=execution.context,
                    user_id=UUID(execution.user_id) if execution.user_id else None,
                    session_id=execution.session_id,
                    tags=execution.tags,
                    metadata_=execution.metadata,
                )
                session.add(model)

            await session.commit()
            await session.refresh(model)
            return self._execution_from_orm(model)

    async def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(WorkflowExecutionModel).where(
                    WorkflowExecutionModel.id == UUID(execution_id)
                )
            )
            model = result.scalar_one_or_none()
            return self._execution_from_orm(model) if model else None

    async def list_executions(
        self,
        workflow_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkflowExecution]:
        async with self._session_factory() as session:
            query = select(WorkflowExecutionModel).order_by(
                WorkflowExecutionModel.created_at.desc()
            )
            if workflow_id:
                query = query.where(
                    WorkflowExecutionModel.workflow_id == UUID(workflow_id)
                )
            if status:
                query = query.where(WorkflowExecutionModel.status == status)
            query = query.offset(offset).limit(limit)
            result = await session.execute(query)
            return [self._execution_from_orm(m) for m in result.scalars().all()]

    async def delete_execution(self, execution_id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                select(WorkflowExecutionModel).where(
                    WorkflowExecutionModel.id == UUID(execution_id)
                )
            )
            model = result.scalar_one_or_none()
            if model is None:
                return False
            await session.delete(model)
            await session.commit()
            return True

    # --- Events ---

    async def save_event(self, event: WorkflowEvent) -> WorkflowEvent:
        async with self._session_factory() as session:
            model = WorkflowEventModel(
                id=UUID(event.id) if isinstance(event.id, str) else event.id,
                execution_id=UUID(event.execution_id) if isinstance(event.execution_id, str) else event.execution_id,
                event_type=event.event_type.value,
                step_id=event.step_id,
                payload=event.payload,
            )
            session.add(model)
            await session.commit()
            return event

    async def get_events(
        self, execution_id: str | None = None, limit: int = 100
    ) -> list[WorkflowEvent]:
        async with self._session_factory() as session:
            query = select(WorkflowEventModel).order_by(
                WorkflowEventModel.timestamp.desc()
            )
            if execution_id:
                query = query.where(
                    WorkflowEventModel.execution_id == UUID(execution_id)
                )
            query = query.limit(limit)
            result = await session.execute(query)
            return [self._event_from_orm(m) for m in result.scalars().all()]

    # --- ORM mapping helpers ---

    @staticmethod
    def _definition_from_orm(model: WorkflowDefinitionModel) -> WorkflowDefinition:
        return WorkflowDefinition(
            id=str(model.id),
            name=model.name,
            description=model.description or "",
            version=model.version,
            steps=list(model.steps or []),
            input_schema=dict(model.input_schema or {}),
            output_schema=dict(model.output_schema or {}),
            tags=list(model.tags or []),
            metadata=dict(model.metadata_ or {}),
        )

    @staticmethod
    def _execution_from_orm(model: WorkflowExecutionModel) -> WorkflowExecution:
        return WorkflowExecution(
            id=str(model.id),
            workflow_id=str(model.workflow_id) if model.workflow_id else "",
            workflow_name=model.workflow_name,
            status=WorkflowStatus(model.status),
            input=dict(model.input_ or {}),
            output=dict(model.output_ or {}),
            error=model.error,
            current_step_id=model.current_step_id,
            step_executions=list(model.step_executions or []),
            context=dict(model.context or {}),
            user_id=str(model.user_id) if model.user_id else None,
            session_id=model.session_id,
            tags=list(model.tags or []),
            metadata=dict(model.metadata_ or {}),
        )

    @staticmethod
    def _event_from_orm(model: WorkflowEventModel) -> WorkflowEvent:
        return WorkflowEvent(
            id=str(model.id),
            execution_id=str(model.execution_id),
            event_type=WorkflowEventType(model.event_type),
            step_id=model.step_id,
            payload=dict(model.payload or {}),
        )
