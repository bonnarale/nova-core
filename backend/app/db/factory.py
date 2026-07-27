"""Factory for creating Database Architecture components."""

from __future__ import annotations

import logging
from typing import Any

from app.db.architecture import DatabaseArchitecture
from app.db.connection_pool import ConnectionPool
from app.db.health import DatabaseHealthChecker
from app.db.lifecycle import DatabaseLifecycle
from app.db.metrics import DatabaseMetricsCollector
from app.db.migrations import InMemoryMigrationProvider
from app.db.registry import RepositoryRegistry
from app.db.repositories import (
    AgentRepository,
    APIMetadataRepository,
    ConversationMemoryRepository,
    EventRepository,
    ExecutionRepository,
    GoalRepository,
    InMemoryRepository,
    KnowledgeRepository,
    LearningRepository,
    ObservabilityMetadataRepository,
    PlanRepository,
    PluginRepository,
    RAGMetadataRepository,
    SchedulerJobRepository,
    SecurityRepository,
    TaskRepository,
    UserProfileRepository,
    VectorMemoryMetadataRepository,
    WorkflowRepository,
)
from app.db.session_manager import InMemorySessionProvider
from app.db.tracing import DatabaseTracer
from app.db.unit_of_work import InMemoryUnitOfWork

logger = logging.getLogger(__name__)


class DatabaseFactory:
    """Creates all Database Architecture components."""

    @staticmethod
    def create_all() -> dict[str, Any]:
        architecture = DatabaseArchitecture()
        registry = RepositoryRegistry()
        pool = ConnectionPool()
        migration_provider = InMemoryMigrationProvider()
        session_provider = InMemorySessionProvider()
        health_checker = DatabaseHealthChecker(pool, migration_provider)
        lifecycle = DatabaseLifecycle()
        metrics = DatabaseMetricsCollector()
        tracer = DatabaseTracer()

        repos = {
            "conversation_memory": ConversationMemoryRepository(),
            "user_profiles": UserProfileRepository(),
            "knowledge": KnowledgeRepository(),
            "learning": LearningRepository(),
            "goals": GoalRepository(),
            "tasks": TaskRepository(),
            "plans": PlanRepository(),
            "executions": ExecutionRepository(),
            "agents": AgentRepository(),
            "workflows": WorkflowRepository(),
            "scheduler_jobs": SchedulerJobRepository(),
            "events": EventRepository(),
            "plugins": PluginRepository(),
            "security": SecurityRepository(),
            "vector_memory_metadata": VectorMemoryMetadataRepository(),
            "rag_metadata": RAGMetadataRepository(),
            "api_metadata": APIMetadataRepository(),
            "observability_metadata": ObservabilityMetadataRepository(),
        }
        for name, repo in repos.items():
            domain = name.split("_")[0] if "_" in name else name
            registry.register(name, repo, domain=domain)

        return {
            "architecture": architecture,
            "registry": registry,
            "pool": pool,
            "migration_provider": migration_provider,
            "session_provider": session_provider,
            "health_checker": health_checker,
            "lifecycle": lifecycle,
            "metrics": metrics,
            "tracer": tracer,
            "repositories": repos,
        }

    @staticmethod
    def create_repository(name: str = "") -> InMemoryRepository:
        return InMemoryRepository(name=name)

    @staticmethod
    def create_unit_of_work() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork()

    @staticmethod
    def create_transaction_manager() -> "Any":
        from app.db.transaction import InMemoryTransactionManager
        return InMemoryTransactionManager()

    @staticmethod
    def create_session_provider() -> InMemorySessionProvider:
        return InMemorySessionProvider()

    @staticmethod
    def create_connection_pool(
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> ConnectionPool:
        return ConnectionPool(pool_size=pool_size, max_overflow=max_overflow)

    @staticmethod
    def create_health_checker(
        pool: ConnectionPool | None = None,
    ) -> DatabaseHealthChecker:
        return DatabaseHealthChecker(pool=pool)

    @staticmethod
    def create_metrics() -> DatabaseMetricsCollector:
        return DatabaseMetricsCollector()

    @staticmethod
    def create_tracer() -> DatabaseTracer:
        return DatabaseTracer()
