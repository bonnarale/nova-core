"""Tests for EventBusAdapter — bridges InMemoryEventBus to orchestrator interface."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.events.schemas import Event


class TestEventBusAdapter:
    """Tests for EventBusAdapter bridging functionality."""

    @pytest.fixture
    def mock_bus(self):
        """Mock InMemoryEventBus."""
        bus = AsyncMock()
        bus.subscribe = AsyncMock(return_value="sub-123")
        bus.unsubscribe = AsyncMock(return_value=True)
        bus.publish = AsyncMock()
        bus.publish_delayed = AsyncMock(return_value="delay-123")
        return bus

    @pytest.fixture
    def adapter(self, mock_bus):
        """Create adapter with mocked bus."""
        from app.orchestrator.adapter import EventBusAdapter
        return EventBusAdapter(mock_bus)

    @pytest.mark.asyncio
    async def test_emit_publishes_event(self, adapter, mock_bus):
        """emit() should create an Event and publish it via InMemoryEventBus."""
        await adapter.emit("task.failed", {"task_id": "abc-123", "error": "test"})

        mock_bus.publish.assert_awaited_once()
        event = mock_bus.publish.call_args[0][0]
        assert isinstance(event, Event)
        assert event.event_type == "task.failed"
        assert event.aggregate_id == "abc-123"
        assert event.payload["error"] == "test"

    @pytest.mark.asyncio
    async def test_emit_includes_task_id_from_aggregate(self, adapter, mock_bus):
        """emit() should set aggregate_id from task_id in data."""
        await adapter.emit("task.completed", {"task_id": "xyz-789"})

        event = mock_bus.publish.call_args[0][0]
        assert event.aggregate_id == "xyz-789"

    @pytest.mark.asyncio
    async def test_subscribe_delegates_to_bus(self, adapter, mock_bus):
        """subscribe() should delegate to InMemoryEventBus.subscribe."""
        handler = AsyncMock()
        sub_id = await adapter.subscribe("task.failed", handler)

        mock_bus.subscribe.assert_awaited_once_with("task.failed", handler)
        assert sub_id == "sub-123"

    @pytest.mark.asyncio
    async def test_publish_delayed_delegates(self, adapter, mock_bus):
        """publish_delayed() should delegate to InMemoryEventBus.publish_delayed."""
        event = Event(event_type="task.created", aggregate_id="123")
        delay_id = await adapter.publish_delayed(event, 30)

        mock_bus.publish_delayed.assert_awaited_once_with(event, 30)
        assert delay_id == "delay-123"

    @pytest.mark.asyncio
    async def test_on_registers_handler(self, adapter, mock_bus):
        """on() should subscribe an adapted handler to the bus."""
        handler = MagicMock()
        # Give the event loop a chance to process the subscription
        adapter.on("task.failed", handler)
        await asyncio.sleep(0.01)

        mock_bus.subscribe.assert_called()

    def test_off_removes_handler(self, adapter, mock_bus):
        """off() should unsubscribe a previously registered handler."""
        handler = MagicMock()
        adapter.on("task.failed", handler)
        # After on, handler should be in the subscriptions map
        adapter.off("task.failed", handler)

    @pytest.mark.asyncio
    async def test_adapted_handler_converts_event_to_tuple(self, adapter, mock_bus):
        """The adapted handler should convert Event to (event_type, data) tuple."""
        received = []

        def orchestrator_handler(event_type, data):
            received.append((event_type, data))

        # Manually register and invoke the adapted handler
        captured_handlers = []

        async def fake_subscribe(event_type, handler):
            captured_handlers.append(handler)
            return "sub-456"

        mock_bus.subscribe.side_effect = fake_subscribe

        adapter.on("task.failed", orchestrator_handler)
        await asyncio.sleep(0.01)

        assert len(captured_handlers) == 1
        adapted = captured_handlers[0]

        # Create a test event and invoke the adapted handler
        test_event = Event(
            event_type="task.failed",
            aggregate_id="task-abc",
            payload={"task_id": "task-abc", "error": "timeout"},
        )
        await adapted(test_event)

        assert len(received) == 1
        event_type, data = received[0]
        assert event_type == "task.failed"
        assert data["task_id"] == "task-abc"
        assert data["error"] == "timeout"
