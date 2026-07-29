"""Comprehensive tests for Chapter 26 — Database Architecture."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import pytest

# ─── Enums ────────────────────────────────────────────────────────────────
from app.db.enums import (
    DatabaseDialect,
    LifecycleState,
    MigrationStatus,
    PoolStatus,
    QueryOperation,
    SessionScope,
    TransactionState,
)


class TestEnums:
    def test_lifecycle_state_values(self) -> None:
        assert LifecycleState.REGISTERED.value == "registered"
        assert LifecycleState.RUNNING.value == "running"
        assert LifecycleState.SHUTDOWN.value == "shutdown"

    def test_transaction_state_values(self) -> None:
        assert TransactionState.PENDING.value == "pending"
        assert TransactionState.COMMITTED.value == "committed"

    def test_session_scope_values(self) -> None:
        assert SessionScope.FUNCTION.value == "function"

    def test_migration_status_values(self) -> None:
        assert MigrationStatus.CURRENT.value == "current"
        assert MigrationStatus.OUTDATED.value == "outdated"

    def test_query_operation_values(self) -> None:
        assert QueryOperation.SELECT.value == "select"
        assert QueryOperation.INSERT.value == "insert"

    def test_pool_status_values(self) -> None:
        assert PoolStatus.HEALTHY.value == "healthy"
        assert PoolStatus.EXHAUSTED.value == "exhausted"

    def test_database_dialect_values(self) -> None:
        assert DatabaseDialect.POSTGRESQL.value == "postgresql"

    def test_all_lifecycle_states(self) -> None:
        states = list(LifecycleState)
        assert len(states) == 7


# ─── Base ABCs ─────────────────────────────────────────────────────────────
from app.db.base import (
    DatabaseHealthProvider,
    MigrationProvider,
    RepositoryProvider,
    SessionProvider,
    TransactionManager,
    UnitOfWork,
)


class TestBaseABCs:
    def test_cannot_instantiate_repository_provider(self) -> None:
        with pytest.raises(TypeError):
            RepositoryProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_unit_of_work(self) -> None:
        with pytest.raises(TypeError):
            UnitOfWork()  # type: ignore[abstract]

    def test_cannot_instantiate_transaction_manager(self) -> None:
        with pytest.raises(TypeError):
            TransactionManager()  # type: ignore[abstract]

    def test_cannot_instantiate_session_provider(self) -> None:
        with pytest.raises(TypeError):
            SessionProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_migration_provider(self) -> None:
        with pytest.raises(TypeError):
            MigrationProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_health_provider(self) -> None:
        with pytest.raises(TypeError):
            DatabaseHealthProvider()  # type: ignore[abstract]


# ─── Models ────────────────────────────────────────────────────────────────
from app.db.models import (
    ConnectionPoolStats,
    DatabaseHealth,
    DatabaseMetrics,
    DatabaseStatistics,
    MigrationInfo,
    QueryTrace,
    TransactionRecord,
)


class TestModels:
    def test_database_metrics_defaults(self) -> None:
        m = DatabaseMetrics()
        assert m.total_queries == 0
        assert m.total_inserts == 0

    def test_database_metrics_to_dict(self) -> None:
        m = DatabaseMetrics(total_queries=10, commit_count=5)
        d = m.to_dict()
        assert d["total_queries"] == 10
        assert d["commit_count"] == 5

    def test_database_health_defaults(self) -> None:
        h = DatabaseHealth()
        assert h.connected is False
        assert h.last_check > 0

    def test_database_health_to_dict(self) -> None:
        h = DatabaseHealth(connected=True, latency_ms=1.5)
        d = h.to_dict()
        assert d["connected"] is True
        assert d["latency_ms"] == 1.5

    def test_transaction_record(self) -> None:
        r = TransactionRecord()
        assert r.state == TransactionState.PENDING.value
        r.finish(TransactionState.COMMITTED)
        assert r.state == TransactionState.COMMITTED.value
        assert r.duration_ms >= 0

    def test_transaction_record_to_dict(self) -> None:
        r = TransactionRecord(state=TransactionState.ACTIVE.value)
        d = r.to_dict()
        assert d["state"] == "active"

    def test_query_trace(self) -> None:
        t = QueryTrace(table="users")
        t.finish(rows_affected=5)
        assert t.rows_affected == 5
        assert t.duration_ms >= 0

    def test_query_trace_to_dict(self) -> None:
        t = QueryTrace(operation="insert", table="users")
        d = t.to_dict()
        assert d["operation"] == "insert"

    def test_migration_info(self) -> None:
        m = MigrationInfo(revision="001", description="init")
        d = m.to_dict()
        assert d["revision"] == "001"

    def test_connection_pool_stats(self) -> None:
        s = ConnectionPoolStats(pool_size=5, active_connections=3)
        d = s.to_dict()
        assert d["pool_size"] == 5
        assert d["active_connections"] == 3

    def test_database_statistics(self) -> None:
        s = DatabaseStatistics(total_queries=100)
        d = s.to_dict()
        assert d["total_queries"] == 100


# ─── Repositories ──────────────────────────────────────────────────────────
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


class TestRepositories:
    def setup_method(self) -> None:
        self.repo = InMemoryRepository(name="test")

    @pytest.mark.asyncio
    async def test_create_and_get(self) -> None:
        created = await self.repo.create({"id": "1", "name": "alice"})
        assert created["name"] == "alice"
        got = await self.repo.get("1")
        assert got is not None
        assert got["name"] == "alice"

    @pytest.mark.asyncio
    async def test_get_not_found(self) -> None:
        assert await self.repo.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_list(self) -> None:
        await self.repo.create({"id": "1", "name": "alice"})
        await self.repo.create({"id": "2", "name": "bob"})
        items = await self.repo.list()
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_list_with_filters(self) -> None:
        await self.repo.create({"id": "1", "role": "admin"})
        await self.repo.create({"id": "2", "role": "user"})
        items = await self.repo.list(filters={"role": "admin"})
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_list_with_pagination(self) -> None:
        for i in range(5):
            await self.repo.create({"id": str(i)})
        items = await self.repo.list(offset=1, limit=2)
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_update(self) -> None:
        await self.repo.create({"id": "1", "name": "old"})
        updated = await self.repo.update("1", {"name": "new"})
        assert updated is not None
        assert updated["name"] == "new"

    @pytest.mark.asyncio
    async def test_update_not_found(self) -> None:
        result = await self.repo.update("nonexistent", {"name": "x"})
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        await self.repo.create({"id": "1"})
        assert await self.repo.delete("1") is True
        assert await self.repo.get("1") is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self) -> None:
        assert await self.repo.delete("nonexistent") is False

    @pytest.mark.asyncio
    async def test_count(self) -> None:
        await self.repo.create({"id": "1"})
        await self.repo.create({"id": "2"})
        assert await self.repo.count() == 2

    @pytest.mark.asyncio
    async def test_count_with_filters(self) -> None:
        await self.repo.create({"id": "1", "role": "admin"})
        await self.repo.create({"id": "2", "role": "user"})
        assert await self.repo.count(filters={"role": "admin"}) == 1

    @pytest.mark.asyncio
    async def test_create_generates_id(self) -> None:
        created = await self.repo.create({"name": "no-id"})
        assert "id" in created
        assert len(created["id"]) > 0

    def test_operation_count(self) -> None:
        assert self.repo.get_operation_count() == 0

    def test_specialized_repositories(self) -> None:
        repos = [
            ConversationMemoryRepository(),
            UserProfileRepository(),
            KnowledgeRepository(),
            LearningRepository(),
            GoalRepository(),
            TaskRepository(),
            PlanRepository(),
            ExecutionRepository(),
            AgentRepository(),
            WorkflowRepository(),
            SchedulerJobRepository(),
            EventRepository(),
            PluginRepository(),
            SecurityRepository(),
            VectorMemoryMetadataRepository(),
            RAGMetadataRepository(),
            APIMetadataRepository(),
            ObservabilityMetadataRepository(),
        ]
        names = {r.name for r in repos}
        assert len(names) == 18
        assert "conversation_memory" in names
        assert "goals" in names
        assert "tasks" in names


# ─── Unit of Work ──────────────────────────────────────────────────────────
from app.db.unit_of_work import InMemoryUnitOfWork


class TestUnitOfWork:
    def setup_method(self) -> None:
        self.uow = InMemoryUnitOfWork()

    @pytest.mark.asyncio
    async def test_begin(self) -> None:
        await self.uow.begin()
        assert self.uow.is_active() is True

    @pytest.mark.asyncio
    async def test_commit(self) -> None:
        await self.uow.begin()
        await self.uow.commit()
        assert self.uow.is_active() is False

    @pytest.mark.asyncio
    async def test_rollback(self) -> None:
        await self.uow.begin()
        await self.uow.rollback()
        assert self.uow.is_active() is False

    @pytest.mark.asyncio
    async def test_begin_twice_raises(self) -> None:
        await self.uow.begin()
        with pytest.raises(RuntimeError):
            await self.uow.begin()

    @pytest.mark.asyncio
    async def test_commit_without_begin_raises(self) -> None:
        with pytest.raises(RuntimeError):
            await self.uow.commit()

    @pytest.mark.asyncio
    async def test_rollback_without_begin_raises(self) -> None:
        with pytest.raises(RuntimeError):
            await self.uow.rollback()

    @pytest.mark.asyncio
    async def test_flush_without_begin_raises(self) -> None:
        with pytest.raises(RuntimeError):
            await self.uow.flush()

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        await self.uow.begin()
        await self.uow.close()
        assert self.uow.is_active() is False

    @pytest.mark.asyncio
    async def test_add_change(self) -> None:
        await self.uow.begin()
        self.uow.add_change({"type": "insert", "table": "users"})
        assert len(self.uow.get_changes()) == 1

    @pytest.mark.asyncio
    async def test_add_change_without_begin_raises(self) -> None:
        with pytest.raises(RuntimeError):
            self.uow.add_change({"type": "insert"})


# ─── Transaction Manager ───────────────────────────────────────────────────
from app.db.transaction import InMemoryTransactionManager


class TestTransactionManager:
    def setup_method(self) -> None:
        self.tm = InMemoryTransactionManager()

    @pytest.mark.asyncio
    async def test_begin(self) -> None:
        await self.tm.begin()
        assert self.tm.is_active() is True

    @pytest.mark.asyncio
    async def test_commit(self) -> None:
        await self.tm.begin()
        await self.tm.commit()
        assert self.tm.is_active() is False

    @pytest.mark.asyncio
    async def test_rollback(self) -> None:
        await self.tm.begin()
        await self.tm.rollback()
        assert self.tm.is_active() is False

    @pytest.mark.asyncio
    async def test_begin_twice_raises(self) -> None:
        await self.tm.begin()
        with pytest.raises(RuntimeError):
            await self.tm.begin()

    @pytest.mark.asyncio
    async def test_savepoint(self) -> None:
        await self.tm.begin()
        sp = await self.tm.savepoint()
        assert sp.startswith("sp-")
        assert len(self.tm.get_current_record().savepoints) == 1

    @pytest.mark.asyncio
    async def test_release_savepoint(self) -> None:
        await self.tm.begin()
        sp = await self.tm.savepoint()
        await self.tm.release_savepoint(sp)

    @pytest.mark.asyncio
    async def test_rollback_to_savepoint(self) -> None:
        await self.tm.begin()
        sp = await self.tm.savepoint()
        await self.tm.rollback_to_savepoint(sp)

    @pytest.mark.asyncio
    async def test_get_statistics(self) -> None:
        stats = self.tm.get_statistics()
        assert stats["total"] == 0
        assert stats["active"] is False


# ─── Session Manager ───────────────────────────────────────────────────────
from app.db.session_manager import AsyncSessionFactory, InMemorySessionProvider


class TestSessionManager:
    def setup_method(self) -> None:
        self.provider = InMemorySessionProvider()

    @pytest.mark.asyncio
    async def test_get_session(self) -> None:
        session = await self.provider.get_session()
        assert session is not None
        assert session["active"] is True

    @pytest.mark.asyncio
    async def test_close_session(self) -> None:
        session = await self.provider.get_session()
        await self.provider.close_session(session)
        assert session["active"] is False

    @pytest.mark.asyncio
    async def test_dispose(self) -> None:
        await self.provider.dispose()
        assert self.provider.is_disposed() is True

    @pytest.mark.asyncio
    async def test_disposed_raises(self) -> None:
        await self.provider.dispose()
        with pytest.raises(RuntimeError):
            await self.provider.get_session()

    @pytest.mark.asyncio
    async def test_active_count(self) -> None:
        await self.provider.get_session()
        await self.provider.get_session()
        assert self.provider.get_active_count() == 2

    @pytest.mark.asyncio
    async def test_factory(self) -> None:
        factory = AsyncSessionFactory(self.provider)
        session = await factory()
        assert session is not None


# ─── Connection Pool ───────────────────────────────────────────────────────
from app.db.connection_pool import ConnectionPool


class TestConnectionPool:
    def setup_method(self) -> None:
        self.pool = ConnectionPool(pool_size=3, max_overflow=2)

    @pytest.mark.asyncio
    async def test_checkout(self) -> None:
        conn = await self.pool.checkout()
        assert conn is not None
        stats = self.pool.get_stats()
        assert stats.active_connections == 1

    @pytest.mark.asyncio
    async def test_checkin(self) -> None:
        conn = await self.pool.checkout()
        await self.pool.checkin(conn)
        stats = self.pool.get_stats()
        assert stats.active_connections == 0

    @pytest.mark.asyncio
    async def test_exhaustion(self) -> None:
        conns = []
        for _ in range(5):
            conns.append(await self.pool.checkout())
        with pytest.raises(ConnectionError):
            await self.pool.checkout()

    @pytest.mark.asyncio
    async def test_dispose(self) -> None:
        await self.pool.dispose()
        assert self.pool.status == PoolStatus.CLOSED

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        assert await self.pool.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_after_dispose(self) -> None:
        await self.pool.dispose()
        assert await self.pool.health_check() is False

    def test_stats(self) -> None:
        stats = self.pool.get_stats()
        assert stats.pool_size == 3
        assert stats.max_overflow == 2

    def test_to_dict(self) -> None:
        d = self.pool.to_dict()
        assert d["pool_size"] == 3


# ─── Migrations ────────────────────────────────────────────────────────────
from app.db.migrations import InMemoryMigrationProvider


class TestMigrations:
    def setup_method(self) -> None:
        self.mp = InMemoryMigrationProvider()

    @pytest.mark.asyncio
    async def test_get_current_revision(self) -> None:
        rev = await self.mp.get_current_revision()
        assert rev == "001"

    @pytest.mark.asyncio
    async def test_get_head_revision(self) -> None:
        rev = await self.mp.get_head_revision()
        assert rev == "001"

    @pytest.mark.asyncio
    async def test_get_migration_status(self) -> None:
        status = await self.mp.get_migration_status()
        assert status["status"] == MigrationStatus.CURRENT.value
        assert status["total_migrations"] >= 1

    @pytest.mark.asyncio
    async def test_validate_migrations(self) -> None:
        assert await self.mp.validate_migrations() is True

    @pytest.mark.asyncio
    async def test_add_migration(self) -> None:
        from app.db.models import MigrationInfo
        self.mp.add_migration(MigrationInfo(revision="002", description="add index"))
        head = await self.mp.get_head_revision()
        assert head == "002"

    @pytest.mark.asyncio
    async def test_set_current_revision(self) -> None:
        self.mp.set_current_revision("002")
        rev = await self.mp.get_current_revision()
        assert rev == "002"


# ─── Health ────────────────────────────────────────────────────────────────
from app.db.health import DatabaseHealthChecker


class TestHealth:
    def setup_method(self) -> None:
        self.hc = DatabaseHealthChecker()

    @pytest.mark.asyncio
    async def test_check_connectivity(self) -> None:
        connected = await self.hc.check_connectivity()
        assert connected is True

    @pytest.mark.asyncio
    async def test_get_pool_status(self) -> None:
        status = await self.hc.get_pool_status()
        assert "pool_size" in status

    @pytest.mark.asyncio
    async def test_get_health(self) -> None:
        health = await self.hc.get_health()
        assert health["connected"] is True
        assert health["pool_status"] == PoolStatus.HEALTHY.value

    @pytest.mark.asyncio
    async def test_latency(self) -> None:
        await self.hc.check_connectivity()
        latency = await self.hc.get_latency_ms()
        assert latency >= 0


# ─── Lifecycle ─────────────────────────────────────────────────────────────
from app.db.lifecycle import DatabaseLifecycle


class TestLifecycle:
    def setup_method(self) -> None:
        self.lc = DatabaseLifecycle()

    def test_initial_state(self) -> None:
        assert self.lc.state == LifecycleState.REGISTERED

    def test_transition_to_initialized(self) -> None:
        assert self.lc.transition(LifecycleState.INITIALIZED) is True
        assert self.lc.state == LifecycleState.INITIALIZED

    def test_transition_to_running(self) -> None:
        self.lc.transition(LifecycleState.INITIALIZED)
        self.lc.transition(LifecycleState.READY)
        self.lc.transition(LifecycleState.RUNNING)
        assert self.lc.state == LifecycleState.RUNNING

    def test_invalid_transition(self) -> None:
        assert self.lc.transition(LifecycleState.RUNNING) is False

    def test_can_accept_operations(self) -> None:
        self.lc.transition(LifecycleState.INITIALIZED)
        self.lc.transition(LifecycleState.READY)
        assert self.lc.can_accept_operations() is True

    def test_get_history(self) -> None:
        self.lc.transition(LifecycleState.INITIALIZED)
        h = self.lc.get_history()
        assert len(h) == 1

    def test_get_status(self) -> None:
        s = self.lc.get_status()
        assert s["state"] == "registered"


# ─── Metrics ───────────────────────────────────────────────────────────────
from app.db.metrics import DatabaseMetricsCollector


class TestMetrics:
    def setup_method(self) -> None:
        self.m = DatabaseMetricsCollector()

    def test_record_query_select(self) -> None:
        self.m.record_query("select", 1.5)
        stats = self.m.get_statistics()
        assert stats["total_queries"] == 1
        assert stats["total_selects"] == 1

    def test_record_query_insert(self) -> None:
        self.m.record_query("insert", 2.0)
        stats = self.m.get_statistics()
        assert stats["total_inserts"] == 1

    def test_record_query_update(self) -> None:
        self.m.record_query("update")
        stats = self.m.get_statistics()
        assert stats["total_updates"] == 1

    def test_record_query_delete(self) -> None:
        self.m.record_query("delete")
        stats = self.m.get_statistics()
        assert stats["total_deletes"] == 1

    def test_record_transaction(self) -> None:
        self.m.record_transaction(committed=True)
        stats = self.m.get_statistics()
        assert stats["transaction_count"] == 1
        assert stats["commit_count"] == 1

    def test_record_rollback(self) -> None:
        self.m.record_rollback()
        stats = self.m.get_statistics()
        assert stats["rollback_count"] == 1

    def test_average_latency(self) -> None:
        self.m.record_query("select", 10.0)
        self.m.record_query("select", 20.0)
        stats = self.m.get_statistics()
        assert stats["average_query_latency_ms"] == 15.0

    def test_reset(self) -> None:
        self.m.record_query("select")
        self.m.reset()
        stats = self.m.get_statistics()
        assert stats["total_queries"] == 0


# ─── Tracing ───────────────────────────────────────────────────────────────
from app.db.tracing import DatabaseTracer


class TestTracing:
    def setup_method(self) -> None:
        self.tracer = DatabaseTracer()

    def test_start_trace(self) -> None:
        tid = self.tracer.start_trace("test_query")
        assert tid != ""

    def test_add_span(self) -> None:
        tid = self.tracer.start_trace("test")
        self.tracer.add_span(tid, "execute")
        trace = self.tracer.get_trace(tid)
        assert trace is not None
        assert len(trace["spans"]) == 1

    def test_end_span(self) -> None:
        tid = self.tracer.start_trace("test")
        self.tracer.add_span(tid, "execute")
        self.tracer.end_span(tid, "execute")
        trace = self.tracer.get_trace(tid)
        assert trace is not None
        assert trace["spans"][0]["duration_ms"] >= 0

    def test_finish_trace(self) -> None:
        tid = self.tracer.start_trace("test")
        self.tracer.finish_trace(tid, "ok")
        trace = self.tracer.get_trace(tid)
        assert trace is not None
        assert trace["status"] == "ok"

    def test_get_trace_not_found(self) -> None:
        assert self.tracer.get_trace("nonexistent") is None

    def test_get_recent_traces(self) -> None:
        self.tracer.start_trace("a")
        self.tracer.start_trace("b")
        recent = self.tracer.get_recent_traces(10)
        assert len(recent) == 2

    def test_statistics(self) -> None:
        self.tracer.start_trace("a")
        self.tracer.start_trace("b")
        stats = self.tracer.get_statistics()
        assert stats["total_traces"] == 2

    def test_clear(self) -> None:
        self.tracer.start_trace("a")
        self.tracer.clear()
        assert self.tracer.get_statistics()["total_traces"] == 0


# ─── Registry ──────────────────────────────────────────────────────────────
from app.db.registry import RepositoryRegistry


class TestRegistry:
    def setup_method(self) -> None:
        self.reg = RepositoryRegistry()

    def test_register(self) -> None:
        self.reg.register("users", InMemoryRepository(), domain="core")
        assert self.reg.has("users")

    def test_get(self) -> None:
        repo = InMemoryRepository()
        self.reg.register("users", repo)
        assert self.reg.get("users") is repo

    def test_list_all(self) -> None:
        self.reg.register("a", InMemoryRepository(), domain="x")
        self.reg.register("b", InMemoryRepository(), domain="y")
        assert len(self.reg.list_all()) == 2

    def test_list_by_domain(self) -> None:
        self.reg.register("a", InMemoryRepository(), domain="core")
        self.reg.register("b", InMemoryRepository(), domain="core")
        self.reg.register("c", InMemoryRepository(), domain="ext")
        assert len(self.reg.list_by_domain("core")) == 2

    def test_unregister(self) -> None:
        self.reg.register("a", InMemoryRepository())
        assert self.reg.unregister("a") is True
        assert self.reg.has("a") is False

    def test_unregister_nonexistent(self) -> None:
        assert self.reg.unregister("nope") is False

    def test_count(self) -> None:
        self.reg.register("a", InMemoryRepository())
        assert self.reg.count() == 1

    def test_get_statistics(self) -> None:
        self.reg.register("a", InMemoryRepository(), domain="core")
        stats = self.reg.get_statistics()
        assert stats["total"] == 1


# ─── Factory ───────────────────────────────────────────────────────────────
from app.db.factory import DatabaseFactory


class TestFactory:
    def test_create_all(self) -> None:
        components = DatabaseFactory.create_all()
        assert "architecture" in components
        assert "registry" in components
        assert "pool" in components
        assert "migration_provider" in components
        assert "session_provider" in components
        assert "health_checker" in components
        assert "lifecycle" in components
        assert "metrics" in components
        assert "tracer" in components
        assert "repositories" in components

    def test_create_repository(self) -> None:
        repo = DatabaseFactory.create_repository("test")
        assert repo.name == "test"

    def test_create_unit_of_work(self) -> None:
        uow = DatabaseFactory.create_unit_of_work()
        assert uow.is_active() is False

    def test_create_transaction_manager(self) -> None:
        tm = DatabaseFactory.create_transaction_manager()
        assert tm.is_active() is False

    def test_create_session_provider(self) -> None:
        sp = DatabaseFactory.create_session_provider()
        assert sp.is_disposed() is False

    def test_create_connection_pool(self) -> None:
        pool = DatabaseFactory.create_connection_pool(pool_size=10)
        assert pool.pool_size == 10

    def test_create_health_checker(self) -> None:
        hc = DatabaseFactory.create_health_checker()
        assert hc is not None

    def test_create_metrics(self) -> None:
        m = DatabaseFactory.create_metrics()
        m.record_query("select")
        assert m.get_statistics()["total_queries"] == 1

    def test_create_tracer(self) -> None:
        t = DatabaseFactory.create_tracer()
        tid = t.start_trace()
        assert tid != ""


# ─── Architecture ──────────────────────────────────────────────────────────
from app.db.architecture import DatabaseArchitecture


class TestArchitecture:
    def setup_method(self) -> None:
        self.arch = DatabaseArchitecture()

    @pytest.mark.asyncio
    async def test_start_shutdown(self) -> None:
        await self.arch.start()
        assert self.arch.is_running()
        await self.arch.shutdown()

    def test_health(self) -> None:
        health = self.arch.health()
        assert "status" in health

    def test_register_repository(self) -> None:
        self.arch.register_repository("users", InMemoryRepository())
        assert self.arch.get_repository("users") is not None
        assert "users" in self.arch.list_repositories()

    def test_get_repository_not_found(self) -> None:
        assert self.arch.get_repository("nonexistent") is None

    def test_get_statistics(self) -> None:
        stats = self.arch.get_statistics()
        assert "repositories" in stats

    def test_get_history(self) -> None:
        h = self.arch.get_history()
        assert isinstance(h, list)


# ─── Concurrency ───────────────────────────────────────────────────────────
class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_repositories(self) -> None:
        repo = InMemoryRepository(name="concurrent")

        async def _write() -> None:
            for i in range(20):
                await repo.create({"id": str(uuid.uuid4()), "val": i})

        repo2 = InMemoryRepository(name="concurrent2")

        async def _write2() -> None:
            for i in range(20):
                await repo2.create({"id": str(uuid.uuid4()), "val": i})

        await asyncio.gather(*[_write(), _write2()])
        assert repo2.get_operation_count() == 20

    @pytest.mark.asyncio
    async def test_concurrent_tracing(self) -> None:
        t = DatabaseTracer()

        async def _trace() -> None:
            for _ in range(50):
                tid = t.start_trace(name="/concurrent")
                t.finish_trace(tid)

        await asyncio.gather(*[_trace() for _ in range(10)])
        stats = t.get_statistics()
        assert stats["total_traces"] == 500

    @pytest.mark.asyncio
    async def test_concurrent_uow(self) -> None:
        uow = InMemoryUnitOfWork()

        async def _tx() -> None:
            await uow.begin()
            uow.add_change({"type": "test"})
            await uow.commit()

        await asyncio.gather(*[_tx() for _ in range(10)])


# ─── Rollback ──────────────────────────────────────────────────────────────
class TestRollback:
    @pytest.mark.asyncio
    async def test_uow_rollback(self) -> None:
        uow = InMemoryUnitOfWork()
        await uow.begin()
        uow.add_change({"type": "insert"})
        assert uow.is_active() is True
        await uow.rollback()
        assert uow.is_active() is False
        assert len(uow.get_changes()) == 0

    @pytest.mark.asyncio
    async def test_tm_rollback(self) -> None:
        tm = InMemoryTransactionManager()
        await tm.begin()
        await tm.rollback()
        assert tm.is_active() is False
        stats = tm.get_statistics()
        assert stats["rolled_back"] == 1


# ─── Edge Cases ────────────────────────────────────────────────────────────
class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_repository(self) -> None:
        repo = InMemoryRepository()
        assert await repo.count() == 0
        assert await repo.list() == []

    @pytest.mark.asyncio
    async def test_pool_checkout_after_dispose(self) -> None:
        pool = ConnectionPool(pool_size=1)
        await pool.dispose()
        assert await pool.health_check() is False

    @pytest.mark.asyncio
    async def test_lifecycle_invalid_transitions(self) -> None:
        lc = DatabaseLifecycle()
        assert lc.transition(LifecycleState.RUNNING) is False
        assert lc.transition(LifecycleState.SHUTDOWN) is False

    @pytest.mark.asyncio
    async def test_metrics_empty_latency(self) -> None:
        m = DatabaseMetricsCollector()
        stats = m.get_statistics()
        assert stats["average_query_latency_ms"] == 0.0

    @pytest.mark.asyncio
    async def test_tracer_empty(self) -> None:
        t = DatabaseTracer()
        stats = t.get_statistics()
        assert stats["total_traces"] == 0
