"""Tests for EventBus."""

import pytest

from app.orchestrator.event_bus import EventBus


class TestEventBus:
    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.mark.asyncio
    async def test_emit_fires_sync_listener(self, bus):
        received = []

        def listener(event_type, data):
            received.append((event_type, data))

        bus.on("task.created", listener)
        await bus.emit("task.created", {"task_id": "123"})

        assert len(received) == 1
        assert received[0] == ("task.created", {"task_id": "123"})

    @pytest.mark.asyncio
    async def test_emit_fires_async_listener(self, bus):
        received = []

        async def listener(event_type, data):
            received.append((event_type, data))

        bus.on("task.completed", listener)
        await bus.emit("task.completed", {"task_id": "456"})

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_emit_no_listeners_does_not_crash(self, bus):
        await bus.emit("task.none", {})

    @pytest.mark.asyncio
    async def test_off_removes_listener(self, bus):
        received = []

        def listener(event_type, data):
            received.append(data)

        bus.on("task.created", listener)
        bus.off("task.created", listener)
        await bus.emit("task.created", {"task_id": "123"})

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_multiple_listeners_same_event(self, bus):
        results = []

        async def a(et, d):
            results.append("a")

        async def b(et, d):
            results.append("b")

        bus.on("task.x", a)
        bus.on("task.x", b)
        await bus.emit("task.x", {})

        assert sorted(results) == ["a", "b"]

    @pytest.mark.asyncio
    async def test_listener_error_does_not_crash_bus(self, bus):
        results = []

        async def broken(et, d):
            raise ValueError("oops")

        async def good(et, d):
            results.append("ok")

        bus.on("task.x", broken)
        bus.on("task.x", good)
        await bus.emit("task.x", {})

        assert results == ["ok"]
