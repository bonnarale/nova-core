"""Comprehensive tests for Chapter 28 — Scaling."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

# ─── Enums ────────────────────────────────────────────────────────────────
from app.scaling.enums import (
    AutoscaleMetric,
    CacheStrategy,
    LoadBalanceStrategy,
    LockState,
    QueuePriority,
    QueueState,
    ScalingState,
    ShardKey,
    WorkerState,
)


class TestEnums:
    def test_scaling_state_values(self) -> None:
        assert ScalingState.REGISTERED.value == "registered"
        assert ScalingState.RUNNING.value == "running"
        assert ScalingState.SCALING_UP.value == "scaling_up"
        assert ScalingState.SCALING_DOWN.value == "scaling_down"
        assert ScalingState.SHUTDOWN.value == "shutdown"

    def test_load_balance_strategy_values(self) -> None:
        assert LoadBalanceStrategy.ROUND_ROBIN.value == "round_robin"
        assert LoadBalanceStrategy.LEAST_CONNECTIONS.value == "least_connections"
        assert LoadBalanceStrategy.WEIGHTED.value == "weighted"
        assert LoadBalanceStrategy.HEALTH_AWARE.value == "health_aware"

    def test_queue_priority_values(self) -> None:
        assert QueuePriority.LOW.value == "low"
        assert QueuePriority.NORMAL.value == "normal"
        assert QueuePriority.HIGH.value == "high"
        assert QueuePriority.CRITICAL.value == "critical"

    def test_queue_state_values(self) -> None:
        assert QueueState.ACTIVE.value == "active"
        assert QueueState.PAUSED.value == "paused"

    def test_cache_strategy_values(self) -> None:
        assert CacheStrategy.LRU.value == "lru"
        assert CacheStrategy.TTL.value == "ttl"

    def test_shard_key_values(self) -> None:
        assert ShardKey.CONVERSATION.value == "conversation"
        assert ShardKey.EVENTS.value == "events"

    def test_autoscale_metric_values(self) -> None:
        assert AutoscaleMetric.CPU.value == "cpu"
        assert AutoscaleMetric.QUEUE_DEPTH.value == "queue_depth"

    def test_lock_state_values(self) -> None:
        assert LockState.AVAILABLE.value == "available"
        assert LockState.HELD.value == "held"

    def test_worker_state_values(self) -> None:
        assert WorkerState.IDLE.value == "idle"
        assert WorkerState.BUSY.value == "busy"

    def test_all_scaling_states(self) -> None:
        assert len(list(ScalingState)) == 9


# ─── Base ABCs ─────────────────────────────────────────────────────────────
from app.scaling.base import (
    AutoscalerProvider,
    CacheProvider,
    DistributedLockProvider,
    LoadBalancerProvider,
    ScalingProvider,
    WorkerPoolProvider,
)


class TestBaseABCs:
    def test_cannot_instantiate_scaling_provider(self) -> None:
        with pytest.raises(TypeError):
            ScalingProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_load_balancer_provider(self) -> None:
        with pytest.raises(TypeError):
            LoadBalancerProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_worker_pool_provider(self) -> None:
        with pytest.raises(TypeError):
            WorkerPoolProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_cache_provider(self) -> None:
        with pytest.raises(TypeError):
            CacheProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_distributed_lock_provider(self) -> None:
        with pytest.raises(TypeError):
            DistributedLockProvider()  # type: ignore[abstract]

    def test_cannot_instantiate_autoscaler_provider(self) -> None:
        with pytest.raises(TypeError):
            AutoscalerProvider()  # type: ignore[abstract]


# ─── Models ────────────────────────────────────────────────────────────────
from app.scaling.models import (
    CacheStats,
    QueueInfo,
    ResourceSnapshot,
    ScalingHealth,
    ScalingMetrics,
    ScalingStatistics,
    WorkerInfo,
)


class TestModels:
    def test_scaling_metrics(self) -> None:
        m = ScalingMetrics()
        assert m.active_workers == 0
        d = m.to_dict()
        assert "requests_per_second" in d

    def test_scaling_health(self) -> None:
        h = ScalingHealth()
        assert h.status == "healthy"
        d = h.to_dict()
        assert d["workers_total"] == 0

    def test_scaling_statistics(self) -> None:
        s = ScalingStatistics()
        assert s.state == ScalingState.REGISTERED.value
        d = s.to_dict()
        assert "uptime_seconds" in d

    def test_worker_info(self) -> None:
        w = WorkerInfo()
        assert w.state == WorkerState.IDLE.value
        d = w.to_dict()
        assert "worker_id" in d

    def test_queue_info(self) -> None:
        q = QueueInfo(name="test")
        assert q.state == QueueState.ACTIVE.value
        d = q.to_dict()
        assert d["name"] == "test"

    def test_cache_stats(self) -> None:
        cs = CacheStats()
        assert cs.hits == 0
        d = cs.to_dict()
        assert "hit_ratio" in d

    def test_resource_snapshot(self) -> None:
        rs = ResourceSnapshot()
        assert rs.cpu_percent == 0.0
        d = rs.to_dict()
        assert "timestamp" in d


# ─── Load Balancer ─────────────────────────────────────────────────────────
from app.scaling.load_balancer import LoadBalancer


class TestLoadBalancer:
    @pytest.mark.asyncio
    async def test_add_and_remove(self) -> None:
        lb = LoadBalancer()
        await lb.add_backend("b1")
        await lb.add_backend("b2")
        info = await lb.get_backends()
        assert info["total"] == 2
        assert await lb.remove_backend("b1") is True
        assert await lb.remove_backend("missing") is False

    @pytest.mark.asyncio
    async def test_round_robin(self) -> None:
        lb = LoadBalancer(LoadBalanceStrategy.ROUND_ROBIN)
        await lb.add_backend("b1")
        await lb.add_backend("b2")
        b1 = await lb.next_backend()
        b2 = await lb.next_backend()
        assert b1 != b2

    @pytest.mark.asyncio
    async def test_least_connections(self) -> None:
        lb = LoadBalancer(LoadBalanceStrategy.LEAST_CONNECTIONS)
        await lb.add_backend("b1")
        await lb.add_backend("b2")
        b = await lb.next_backend()
        assert b in ("b1", "b2")

    @pytest.mark.asyncio
    async def test_weighted(self) -> None:
        lb = LoadBalancer(LoadBalanceStrategy.WEIGHTED)
        await lb.add_backend("b1", weight=10)
        await lb.add_backend("b2", weight=1)
        b = await lb.next_backend()
        assert b in ("b1", "b2")

    @pytest.mark.asyncio
    async def test_health_aware(self) -> None:
        lb = LoadBalancer(LoadBalanceStrategy.HEALTH_AWARE)
        await lb.add_backend("b1")
        await lb.add_backend("b2")
        await lb.report_health("b1", False)
        b = await lb.next_backend()
        assert b == "b2"

    @pytest.mark.asyncio
    async def test_no_backends(self) -> None:
        lb = LoadBalancer()
        assert await lb.next_backend() is None

    @pytest.mark.asyncio
    async def test_release_connection(self) -> None:
        lb = LoadBalancer()
        await lb.add_backend("b1")
        await lb.next_backend()
        await lb.release_connection("b1")
        info = await lb.get_backends()
        assert info["backends"]["b1"]["connections"] == 0


# ─── Worker Pool ───────────────────────────────────────────────────────────
from app.scaling.worker_pool import WorkerPool


class TestWorkerPool:
    @pytest.mark.asyncio
    async def test_start_and_stop(self) -> None:
        wp = WorkerPool(pool_size=2)
        await wp.start()
        status = await wp.get_status()
        assert status["pool_size"] == 2
        assert status["running"] is True
        await wp.stop()
        status = await wp.get_status()
        assert status["running"] is False

    @pytest.mark.asyncio
    async def test_add_and_remove_worker(self) -> None:
        wp = WorkerPool(pool_size=1)
        await wp.start()
        status_before = await wp.get_status()
        assert status_before["pool_size"] == 1
        wid = await wp.add_worker()
        assert wid
        status = await wp.get_status()
        assert status["pool_size"] == 2
        assert await wp.remove_worker(wid) is True
        assert await wp.remove_worker("nonexistent") is False

    @pytest.mark.asyncio
    async def test_submit_task(self) -> None:
        wp = WorkerPool(pool_size=2)
        await wp.start()
        tid = await wp.submit_task({"action": "test"})
        assert tid

    @pytest.mark.asyncio
    async def test_process_next(self) -> None:
        wp = WorkerPool(pool_size=2)
        await wp.start()
        await wp.submit_task({"id": "t1", "action": "test"})
        task = await wp.process_next()
        assert task is not None
        assert task["id"] == "t1"

    @pytest.mark.asyncio
    async def test_process_empty(self) -> None:
        wp = WorkerPool(pool_size=2)
        await wp.start()
        task = await wp.process_next()
        assert task is None

    def test_get_stats(self) -> None:
        wp = WorkerPool()
        stats = wp.get_stats()
        assert "pool_size" in stats

    def test_get_workers(self) -> None:
        wp = WorkerPool()
        workers = wp.get_workers()
        assert isinstance(workers, list)


# ─── Queue Manager ─────────────────────────────────────────────────────────
from app.scaling.queue_manager import QueueManager


class TestQueueManager:
    @pytest.mark.asyncio
    async def test_create_queue(self) -> None:
        qm = QueueManager()
        info = qm.create_queue("tasks")
        assert info.name == "tasks"

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self) -> None:
        qm = QueueManager()
        await qm.enqueue("tasks", {"id": "t1", "action": "test"})
        task = await qm.dequeue("tasks")
        assert task is not None
        assert task["id"] == "t1"

    @pytest.mark.asyncio
    async def test_priority_order(self) -> None:
        qm = QueueManager()
        await qm.enqueue("q", {"id": "low"}, priority="low")
        await qm.enqueue("q", {"id": "critical"}, priority="critical")
        await qm.enqueue("q", {"id": "normal"}, priority="normal")
        task = await qm.dequeue("q")
        assert task is not None
        assert task["id"] == "critical"

    @pytest.mark.asyncio
    async def test_delay_queue(self) -> None:
        qm = QueueManager()
        await qm.enqueue("q", {"id": "delayed"}, delay=0.01)
        await asyncio.sleep(0.02)
        task = await qm.dequeue("q")
        assert task is not None

    @pytest.mark.asyncio
    async def test_dequeue_empty(self) -> None:
        qm = QueueManager()
        assert await qm.dequeue("nonexistent") is None

    @pytest.mark.asyncio
    async def test_dead_letter(self) -> None:
        qm = QueueManager()
        qm.create_queue("q")
        await qm.send_to_dead_letter("q", {"id": "failed"})
        dl = await qm.get_dead_letters("q")
        assert len(dl) == 1

    @pytest.mark.asyncio
    async def test_statistics(self) -> None:
        qm = QueueManager()
        await qm.enqueue("q1", {"id": "t1"})
        stats = qm.get_statistics()
        assert stats["total_queues"] >= 1

    def test_list_queues(self) -> None:
        qm = QueueManager()
        qm.create_queue("q1")
        queues = qm.list_queues()
        assert len(queues) >= 1


# ─── Cache ─────────────────────────────────────────────────────────────────
from app.scaling.cache import InMemoryCache, LRUCache, TTLCache


class TestCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self) -> None:
        c = InMemoryCache()
        await c.set("key", "value")
        assert await c.get("key") == "value"

    @pytest.mark.asyncio
    async def test_get_missing(self) -> None:
        c = InMemoryCache()
        assert await c.get("missing") is None

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        c = InMemoryCache()
        await c.set("k", "v")
        assert await c.delete("k") is True
        assert await c.delete("k") is False

    @pytest.mark.asyncio
    async def test_exists(self) -> None:
        c = InMemoryCache()
        await c.set("k", "v")
        assert await c.exists("k") is True
        assert await c.exists("x") is False

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        c = InMemoryCache()
        await c.set("a", 1)
        await c.set("b", 2)
        count = await c.clear()
        assert count == 2
        assert await c.size() == 0

    @pytest.mark.asyncio
    async def test_ttl_expiration(self) -> None:
        c = InMemoryCache()
        await c.set("k", "v", ttl=0.01)
        await asyncio.sleep(0.02)
        assert await c.get("k") is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self) -> None:
        c = InMemoryCache(max_size=2)
        await c.set("a", 1)
        await c.set("b", 2)
        await c.set("c", 3)
        assert await c.size() == 2
        assert await c.get("a") is None

    def test_stats(self) -> None:
        c = InMemoryCache()
        stats = c.get_stats()
        assert stats.hits == 0

    @pytest.mark.asyncio
    async def test_lru_cache(self) -> None:
        c = LRUCache(max_size=5)
        await c.set("k", "v")
        assert await c.get("k") == "v"

    @pytest.mark.asyncio
    async def test_ttl_cache(self) -> None:
        c = TTLCache(max_size=5, default_ttl=0.01)
        await c.set("k", "v")
        await asyncio.sleep(0.02)
        assert await c.get("k") is None

    @pytest.mark.asyncio
    async def test_hit_miss_tracking(self) -> None:
        c = InMemoryCache()
        await c.set("k", "v")
        await c.get("k")
        await c.get("miss")
        stats = c.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1


# ─── Distributed Lock ──────────────────────────────────────────────────────
from app.scaling.distributed_lock import InMemoryDistributedLock


class TestDistributedLock:
    @pytest.mark.asyncio
    async def test_acquire_and_release(self) -> None:
        dl = InMemoryDistributedLock()
        assert await dl.acquire("lock1") is True
        assert await dl.is_locked("lock1") is True
        assert await dl.release("lock1") is True
        assert await dl.is_locked("lock1") is False

    @pytest.mark.asyncio
    async def test_release_nonexistent(self) -> None:
        dl = InMemoryDistributedLock()
        assert await dl.release("nope") is False

    @pytest.mark.asyncio
    async def test_extend(self) -> None:
        dl = InMemoryDistributedLock()
        await dl.acquire("lock1", lease=1.0)
        assert await dl.extend("lock1", lease=2.0) is True
        assert await dl.extend("nonexistent") is False

    @pytest.mark.asyncio
    async def test_is_not_locked(self) -> None:
        dl = InMemoryDistributedLock()
        assert await dl.is_locked("nope") is False

    def test_get_lock_info(self) -> None:
        dl = InMemoryDistributedLock()
        assert dl.get_lock_info("nope") is None


# ─── Autoscaler ────────────────────────────────────────────────────────────
from app.scaling.autoscaler import Autoscaler


class TestAutoscaler:
    @pytest.mark.asyncio
    async def test_evaluate_no_action(self) -> None:
        a = Autoscaler(min_workers=1, max_workers=10, cooldown_seconds=0)
        await a.record_metric("cpu", 50.0)
        result = await a.evaluate()
        assert result["action"] == "none"

    @pytest.mark.asyncio
    async def test_scale_up(self) -> None:
        a = Autoscaler(min_workers=1, max_workers=10, scale_up_threshold=80.0, cooldown_seconds=0)
        await a.record_metric("cpu", 90.0)
        result = await a.evaluate()
        assert result["action"] == "scale_up"
        assert a.current_workers == 2

    @pytest.mark.asyncio
    async def test_scale_down(self) -> None:
        a = Autoscaler(min_workers=1, max_workers=10, scale_down_threshold=20.0, cooldown_seconds=0)
        a.set_current_workers(5)
        await a.record_metric("cpu", 10.0)
        await a.record_metric("queue_depth", 0.0)
        result = await a.evaluate()
        assert result["action"] == "scale_down"
        assert a.current_workers == 4

    @pytest.mark.asyncio
    async def test_respects_min_max(self) -> None:
        a = Autoscaler(min_workers=2, max_workers=5, cooldown_seconds=0)
        a.set_current_workers(5)
        await a.record_metric("cpu", 95.0)
        result = await a.evaluate()
        assert a.current_workers <= 5
        a.set_current_workers(2)
        await a.record_metric("cpu", 5.0)
        await a.record_metric("queue_depth", 0.0)
        result = await a.evaluate()
        assert a.current_workers >= 2

    @pytest.mark.asyncio
    async def test_disabled(self) -> None:
        a = Autoscaler()
        a.set_enabled(False)
        result = await a.evaluate()
        assert result["action"] == "none"

    def test_get_config(self) -> None:
        a = Autoscaler()
        config = a.get_config()
        assert "min_workers" in config

    def test_get_events(self) -> None:
        a = Autoscaler()
        events = a.get_events()
        assert isinstance(events, list)


# ─── Resource Manager ──────────────────────────────────────────────────────
from app.scaling.resource_manager import ResourceManager


class TestResourceManager:
    def test_record_snapshot(self) -> None:
        rm = ResourceManager()
        rm.record_snapshot(cpu_percent=50.0, memory_percent=60.0, active_workers=4)
        current = rm.get_current()
        assert current.cpu_percent == 50.0

    def test_get_history(self) -> None:
        rm = ResourceManager()
        rm.record_snapshot()
        rm.record_snapshot()
        history = rm.get_history()
        assert len(history) == 2

    def test_get_statistics(self) -> None:
        rm = ResourceManager()
        rm.record_snapshot(cpu_percent=10.0)
        rm.record_snapshot(cpu_percent=20.0)
        stats = rm.get_statistics()
        assert stats["avg_cpu"] == 15.0

    def test_custom_metric(self) -> None:
        rm = ResourceManager()
        rm.set_metric("custom", 42.0)
        assert rm.get_metric("custom") == 42.0
        assert rm.get_metric("missing") == 0.0

    def test_clear(self) -> None:
        rm = ResourceManager()
        rm.record_snapshot()
        assert rm.clear() == 1


# ─── Sharding ──────────────────────────────────────────────────────────────
from app.scaling.sharding import DomainSharding, ShardingStrategy


class TestSharding:
    def test_get_shard(self) -> None:
        s = ShardingStrategy(num_shards=8)
        shard = s.get_shard("test_key")
        assert 0 <= shard < 8

    def test_consistent_routing(self) -> None:
        s = ShardingStrategy(num_shards=8)
        s1 = s.get_shard("key1")
        s2 = s.get_shard("key1")
        assert s1 == s2

    def test_statistics(self) -> None:
        s = ShardingStrategy(num_shards=4)
        s.get_shard("a")
        stats = s.get_statistics()
        assert stats["num_shards"] == 4

    def test_domain_sharding(self) -> None:
        ds = DomainSharding()
        shard = ds.get_shard("conversation", "key1")
        assert isinstance(shard, int)

    def test_add_domain(self) -> None:
        ds = DomainSharding()
        ds.add_domain("custom", 16)
        stats = ds.get_domain_statistics()
        assert "custom" in stats


# ─── Partitioning ──────────────────────────────────────────────────────────
from app.scaling.partitioning import HashPartitioning, TimePartitioning


class TestPartitioning:
    def test_hash_partitioning(self) -> None:
        hp = HashPartitioning(num_partitions=8)
        p = hp.get_partition("test")
        assert 0 <= p < 8

    def test_time_partitioning(self) -> None:
        tp = TimePartitioning(interval="daily")
        key = tp.get_partition_key()
        assert len(key) == 8

    def test_time_partitioning_hourly(self) -> None:
        tp = TimePartitioning(interval="hourly")
        key = tp.get_partition_key()
        assert len(key) == 10

    def test_add_item(self) -> None:
        hp = HashPartitioning(num_partitions=4)
        pid = hp.add_item("test")
        assert 0 <= pid < 4


# ─── Replication ───────────────────────────────────────────────────────────
from app.scaling.replication import ReplicationManager


class TestReplication:
    def test_add_remove_replica(self) -> None:
        rm = ReplicationManager()
        rm.add_replica("r1", host="localhost")
        stats = rm.get_statistics()
        assert stats["total_replicas"] == 1
        assert rm.remove_replica("r1") is True

    def test_report_health(self) -> None:
        rm = ReplicationManager()
        rm.add_replica("r1")
        rm.report_health("r1", False, lag_ms=100.0)
        stats = rm.get_statistics()
        assert stats["failover_count"] == 1

    def test_select_replica(self) -> None:
        rm = ReplicationManager()
        rm.add_replica("r1")
        rm.add_replica("r2")
        r = rm.select_replica()
        assert r is not None

    def test_no_healthy_replicas(self) -> None:
        rm = ReplicationManager()
        rm.add_replica("r1")
        rm.report_health("r1", False)
        assert rm.select_replica() is None

    def test_record_sync(self) -> None:
        rm = ReplicationManager()
        rm.record_sync("r1", True, 10.0)
        stats = rm.get_statistics()
        assert stats["sync_events"] == 1


# ─── Lifecycle ─────────────────────────────────────────────────────────────
from app.scaling.lifecycle import ScalingLifecycle


class TestLifecycle:
    def test_initial_state(self) -> None:
        lc = ScalingLifecycle()
        assert lc.state == ScalingState.REGISTERED

    def test_valid_transitions(self) -> None:
        lc = ScalingLifecycle()
        lc.transition(ScalingState.INITIALIZED)
        lc.transition(ScalingState.READY)
        lc.transition(ScalingState.RUNNING)
        assert lc.is_running() is True

    def test_invalid_transition(self) -> None:
        lc = ScalingLifecycle()
        assert lc.transition(ScalingState.RUNNING) is False

    def test_scaling_up(self) -> None:
        lc = ScalingLifecycle()
        lc.transition(ScalingState.INITIALIZED)
        lc.transition(ScalingState.READY)
        lc.transition(ScalingState.RUNNING)
        lc.transition(ScalingState.SCALING_UP)
        assert lc.is_scaling() is True

    def test_can_operate(self) -> None:
        lc = ScalingLifecycle()
        lc.transition(ScalingState.INITIALIZED)
        lc.transition(ScalingState.READY)
        lc.transition(ScalingState.RUNNING)
        assert lc.can_operate() is True

    def test_history(self) -> None:
        lc = ScalingLifecycle()
        lc.transition(ScalingState.INITIALIZED)
        assert len(lc.get_history()) == 1

    def test_get_status(self) -> None:
        lc = ScalingLifecycle()
        status = lc.get_status()
        assert "state" in status


# ─── Health ────────────────────────────────────────────────────────────────
from app.scaling.health import ScalingHealthChecker


class TestHealth:
    @pytest.mark.asyncio
    async def test_check_healthy(self) -> None:
        hc = ScalingHealthChecker()
        health = await hc.check(workers_healthy=4, workers_total=4)
        assert health.status == "healthy"

    @pytest.mark.asyncio
    async def test_check_degraded(self) -> None:
        hc = ScalingHealthChecker()
        health = await hc.check(workers_healthy=1, workers_total=4)
        assert health.status == "degraded"

    def test_register_check(self) -> None:
        hc = ScalingHealthChecker()
        hc.register_check("db", True)
        assert "db" in hc.get_checks()

    def test_remove_check(self) -> None:
        hc = ScalingHealthChecker()
        hc.register_check("db", True)
        assert hc.remove_check("db") is True
        assert hc.remove_check("x") is False


# ─── Metrics ───────────────────────────────────────────────────────────────
from app.scaling.metrics import ScalingMetricsCollector


class TestMetrics:
    def test_record_request(self) -> None:
        m = ScalingMetricsCollector()
        m.record_request()
        stats = m.get_statistics()
        assert stats["requests_per_second"] >= 1.0

    def test_set_active_workers(self) -> None:
        m = ScalingMetricsCollector()
        m.set_active_workers(4)
        stats = m.get_statistics()
        assert stats["active_workers"] == 4

    def test_cache_tracking(self) -> None:
        m = ScalingMetricsCollector()
        m.record_cache_hit()
        m.record_cache_hit()
        m.record_cache_miss()
        stats = m.get_statistics()
        assert stats["cache_hit_ratio"] > 0

    def test_scaling_event(self) -> None:
        m = ScalingMetricsCollector()
        m.record_scaling_event()
        stats = m.get_statistics()
        assert stats["scaling_events"] == 1

    def test_to_model(self) -> None:
        m = ScalingMetricsCollector()
        model = m.to_model()
        assert model.active_workers == 0

    def test_reset(self) -> None:
        m = ScalingMetricsCollector()
        m.record_request()
        m.reset()
        stats = m.get_statistics()
        assert stats["requests_per_second"] == 0.0


# ─── Tracing ───────────────────────────────────────────────────────────────
from app.scaling.tracing import ScalingTracer


class TestTracing:
    def test_start_and_finish(self) -> None:
        t = ScalingTracer()
        tid = t.start_trace("test")
        t.finish_trace(tid, "ok")
        trace = t.get_trace(tid)
        assert trace is not None
        assert trace["status"] == "ok"

    def test_add_and_end_span(self) -> None:
        t = ScalingTracer()
        tid = t.start_trace("root")
        t.add_span(tid, "child")
        t.end_span(tid, "child")
        t.finish_trace(tid)
        trace = t.get_trace(tid)
        assert len(trace["spans"]) == 1

    def test_get_statistics(self) -> None:
        t = ScalingTracer()
        tid = t.start_trace("ok")
        t.finish_trace(tid, "ok")
        stats = t.get_statistics()
        assert stats["total_traces"] == 1

    def test_clear(self) -> None:
        t = ScalingTracer()
        t.start_trace("x")
        t.clear()
        assert t.get_statistics()["total_traces"] == 0


# ─── Factory ───────────────────────────────────────────────────────────────
from app.scaling.factory import ScalingFactory


class TestFactory:
    def test_create_all(self) -> None:
        components = ScalingFactory.create_all()
        assert "engine" in components
        assert "load_balancer" in components
        assert "worker_pool" in components
        assert "cache" in components

    def test_create_engine(self) -> None:
        e = ScalingFactory.create_engine()
        assert e is not None

    def test_create_load_balancer(self) -> None:
        lb = ScalingFactory.create_load_balancer(LoadBalanceStrategy.LEAST_CONNECTIONS)
        assert lb.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS

    def test_create_worker_pool(self) -> None:
        wp = ScalingFactory.create_worker_pool(pool_size=8)
        assert wp.pool_size == 8

    def test_create_cache(self) -> None:
        c = ScalingFactory.create_cache(max_size=100)
        assert c is not None

    def test_create_lru_cache(self) -> None:
        c = ScalingFactory.create_lru_cache(max_size=50)
        assert c is not None

    def test_create_ttl_cache(self) -> None:
        c = ScalingFactory.create_ttl_cache(max_size=50, default_ttl=60.0)
        assert c is not None

    def test_create_autoscaler(self) -> None:
        a = ScalingFactory.create_autoscaler(min_workers=2, max_workers=20)
        assert a.get_config()["min_workers"] == 2

    def test_create_replication(self) -> None:
        r = ScalingFactory.create_replication("primary")
        assert r.primary_id == "primary"

    def test_create_metrics(self) -> None:
        m = ScalingFactory.create_metrics()
        assert m is not None

    def test_create_tracer(self) -> None:
        t = ScalingFactory.create_tracer()
        assert t is not None


# ─── Engine ────────────────────────────────────────────────────────────────
from app.scaling.engine import ScalingEngine


class TestEngine:
    @pytest.mark.asyncio
    async def test_start_and_health(self) -> None:
        e = ScalingEngine()
        await e.start()
        health = await e.health()
        assert health.status == "healthy"

    @pytest.mark.asyncio
    async def test_start_and_shutdown(self) -> None:
        e = ScalingEngine()
        await e.start()
        await e.shutdown()
        assert e.is_running() is False

    @pytest.mark.asyncio
    async def test_scale_up(self) -> None:
        e = ScalingEngine()
        await e.start()
        result = await e.scale_up(2)
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_scale_down(self) -> None:
        e = ScalingEngine()
        await e.start()
        await e.scale_up(3)
        result = await e.scale_down(1)
        assert result["total"] <= 1

    @pytest.mark.asyncio
    async def test_statistics(self) -> None:
        e = ScalingEngine()
        await e.start()
        stats = await e.statistics()
        assert stats.state == ScalingState.RUNNING.value

    @pytest.mark.asyncio
    async def test_components_accessible(self) -> None:
        e = ScalingEngine()
        assert e.load_balancer is not None
        assert e.worker_pool is not None
        assert e.queue_manager is not None
        assert e.cache is not None
        assert e.distributed_lock is not None
        assert e.autoscaler is not None
        assert e.resource_manager is not None
        assert e.sharding is not None
        assert e.replication is not None


# ─── Schemas ───────────────────────────────────────────────────────────────
from app.scaling.schemas import (
    CacheClearResponse,
    CacheResponse,
    QueuesResponse,
    ResourcesResponse,
    ScalingHealthResponse,
    ScalingMetricsResponse,
    ScalingStatisticsResponse,
    ScaleDownRequest,
    ScaleUpRequest,
    WorkersResponse,
)


class TestSchemas:
    def test_health_response(self) -> None:
        r = ScalingHealthResponse()
        assert r.status == "healthy"

    def test_metrics_response(self) -> None:
        r = ScalingMetricsResponse()
        assert r.uptime_seconds == 0.0

    def test_statistics_response(self) -> None:
        r = ScalingStatisticsResponse()
        assert r.state == "registered"

    def test_workers_response(self) -> None:
        r = WorkersResponse()
        assert r.pool_size == 0

    def test_queues_response(self) -> None:
        r = QueuesResponse()
        assert r.total_queues == 0

    def test_cache_response(self) -> None:
        r = CacheResponse()
        assert r.hits == 0

    def test_resources_response(self) -> None:
        r = ResourcesResponse()
        assert r.cpu_percent == 0.0

    def test_scale_up_request(self) -> None:
        r = ScaleUpRequest(amount=3)
        assert r.amount == 3

    def test_scale_down_request(self) -> None:
        r = ScaleDownRequest(amount=2)
        assert r.amount == 2

    def test_cache_clear_response(self) -> None:
        r = CacheClearResponse()
        assert r.success is True


# ─── Integration ───────────────────────────────────────────────────────────
class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_lifecycle(self) -> None:
        engine = ScalingEngine()
        await engine.start()
        await engine.scale_up(2)
        health = await engine.health()
        assert health.status == "healthy"
        stats = await engine.statistics()
        assert stats.total_workers >= 2
        await engine.scale_down(1)
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_cache_and_lock_integration(self) -> None:
        engine = ScalingEngine()
        await engine.cache.set("k", "v")
        assert await engine.cache.get("k") == "v"
        assert await engine.distributed_lock.acquire("lock1") is True
        assert await engine.distributed_lock.release("lock1") is True

    @pytest.mark.asyncio
    async def test_queue_and_worker_integration(self) -> None:
        engine = ScalingEngine()
        await engine.start()
        engine.queue_manager.create_queue("tasks")
        await engine.queue_manager.enqueue("tasks", {"id": "t1"})
        task = await engine.queue_manager.dequeue("tasks")
        assert task is not None
        processed = await engine.worker_pool.process_next()
        # Worker pool has its own queue, may be None if empty

    @pytest.mark.asyncio
    async def test_load_balancer_integration(self) -> None:
        engine = ScalingEngine()
        await engine.load_balancer.add_backend("b1")
        await engine.load_balancer.add_backend("b2")
        b = await engine.load_balancer.next_backend()
        assert b in ("b1", "b2")

    @pytest.mark.asyncio
    async def test_autoscaler_integration(self) -> None:
        engine = ScalingEngine()
        await engine.autoscaler.record_metric("cpu", 90.0)
        rec = await engine.autoscaler.evaluate()
        assert rec["action"] == "scale_up"

    @pytest.mark.asyncio
    async def test_sharding_integration(self) -> None:
        engine = ScalingEngine()
        shard = engine.sharding.get_shard("conversation", "user-123")
        assert isinstance(shard, int)

    @pytest.mark.asyncio
    async def test_replication_integration(self) -> None:
        engine = ScalingEngine()
        engine.replication.add_replica("r1")
        engine.replication.add_replica("r2")
        r = engine.replication.select_replica()
        assert r is not None

    @pytest.mark.asyncio
    async def test_resource_tracking(self) -> None:
        engine = ScalingEngine()
        engine.resource_manager.record_snapshot(cpu_percent=50.0, memory_percent=60.0)
        current = engine.resource_manager.get_current()
        assert current.cpu_percent == 50.0


# ─── Concurrency ───────────────────────────────────────────────────────────
class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self) -> None:
        c = InMemoryCache(max_size=100)

        async def writer(n: int) -> None:
            for i in range(10):
                await c.set(f"key-{n}-{i}", i)

        await asyncio.gather(*[writer(n) for n in range(5)])
        assert await c.size() > 0

    @pytest.mark.asyncio
    async def test_concurrent_lock_acquisition(self) -> None:
        dl = InMemoryDistributedLock()
        results: list[bool] = []

        async def try_lock() -> None:
            r = await dl.acquire("shared", timeout=0.1, lease=60.0)
            results.append(r)
            if r:
                await dl.release("shared")

        await asyncio.gather(*[try_lock() for _ in range(5)])
        assert any(results)

    @pytest.mark.asyncio
    async def test_concurrent_queue_operations(self) -> None:
        qm = QueueManager()

        async def enqueue_items(prefix: str) -> None:
            for i in range(5):
                await qm.enqueue("q", {"id": f"{prefix}-{i}"})

        await asyncio.gather(*[enqueue_items(f"t{n}") for n in range(3)])
        stats = qm.get_statistics()
        assert stats["total_enqueued"] >= 15


# ─── Fault Tolerance ───────────────────────────────────────────────────────
class TestFaultTolerance:
    @pytest.mark.asyncio
    async def test_queue_full(self) -> None:
        wp = WorkerPool(pool_size=1, max_queue_size=1)
        await wp.start()
        await wp.submit_task({"id": "t1"})
        with pytest.raises(RuntimeError):
            await wp.submit_task({"id": "t2"})

    @pytest.mark.asyncio
    async def test_cache_max_size(self) -> None:
        c = InMemoryCache(max_size=1)
        await c.set("a", 1)
        await c.set("b", 2)
        assert await c.size() == 1


# ─── Edge Cases ────────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_empty_load_balancer(self) -> None:
        lb = LoadBalancer()
        assert lb.strategy == LoadBalanceStrategy.ROUND_ROBIN

    def test_worker_pool_default(self) -> None:
        wp = WorkerPool()
        assert wp.pool_size == 4

    def test_empty_queue_manager(self) -> None:
        qm = QueueManager()
        stats = qm.get_statistics()
        assert stats["total_queues"] == 0

    def test_empty_cache(self) -> None:
        c = InMemoryCache()
        assert c.get_stats().hits == 0

    def test_autoscaler_default_config(self) -> None:
        a = Autoscaler()
        config = a.get_config()
        assert config["min_workers"] == 1
        assert config["max_workers"] == 10

    def test_empty_sharding(self) -> None:
        ds = DomainSharding()
        stats = ds.get_domain_statistics()
        assert len(stats) >= 4
