"""NOVA CORE Custom Assertions — Chapter 29."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any


def assert_valid_event(event: Any) -> None:
    """Assert that an event has required fields."""
    assert hasattr(event, "id"), "Event must have an id"
    assert hasattr(event, "type"), "Event must have a type"
    assert hasattr(event, "timestamp"), "Event must have a timestamp"
    assert isinstance(event.timestamp, datetime), "Event timestamp must be datetime"


def assert_valid_workflow_state(state: Any) -> None:
    """Assert that a workflow state is valid."""
    valid_states = {"draft", "ready", "running", "completed", "failed", "paused", "cancelled"}
    state_val = state.value if hasattr(state, "value") else str(state)
    assert state_val in valid_states, f"Invalid workflow state: {state_val}"


def assert_valid_agent_execution(result: Any) -> None:
    """Assert that an agent execution result is valid."""
    assert result is not None, "Agent execution result must not be None"
    if isinstance(result, dict):
        assert "status" in result, "Agent result must have status"
    elif hasattr(result, "status"):
        assert result.status is not None


def assert_event_emitted(events: list[Any], event_type: str) -> None:
    """Assert that at least one event of the given type was emitted."""
    found = False
    for event in events:
        actual_type = event.type.value if hasattr(event.type, "value") else str(event.type)
        if event_type in actual_type:
            found = True
            break
    assert found, f"Expected event type '{event_type}' not found in {len(events)} events"


def assert_no_events_emitted(events: list[Any]) -> None:
    """Assert that no events were emitted."""
    assert len(events) == 0, f"Expected no events, but found {len(events)}"


def assert_valid_memory_retrieval(results: list[Any]) -> None:
    """Assert that memory retrieval results are valid."""
    assert isinstance(results, list), "Memory retrieval must return a list"


def assert_vector_similarity(vec1: list[float], vec2: list[float], threshold: float = 0.9) -> None:
    """Assert that two vectors are similar (cosine similarity above threshold)."""
    assert len(vec1) == len(vec2), f"Vectors must have same length: {len(vec1)} != {len(vec2)}"
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        similarity = 0.0
    else:
        similarity = dot_product / (norm1 * norm2)
    assert similarity >= threshold, f"Vector similarity {similarity:.4f} < threshold {threshold}"


def assert_vector_orthogonal(vec1: list[float], vec2: list[float], threshold: float = 0.1) -> None:
    """Assert that two vectors are approximately orthogonal."""
    assert len(vec1) == len(vec2), f"Vectors must have same length: {len(vec1)} != {len(vec2)}"
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        similarity = 0.0
    else:
        similarity = abs(dot_product / (norm1 * norm2))
    assert similarity <= threshold, f"Vector similarity {similarity:.4f} > orthogonal threshold {threshold}"


def assert_valid_api_response(response: Any, expected_status: int = 200) -> None:
    """Assert that an API response is valid."""
    assert hasattr(response, "status_code"), "Response must have status_code"
    if isinstance(expected_status, int):
        assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"


def assert_api_response_json(response: Any, expected_keys: list[str] | None = None) -> dict[str, Any]:
    """Assert API response has valid JSON and optionally check keys."""
    assert hasattr(response, "json"), "Response must have json() method"
    data = response.json()
    if expected_keys:
        for key in expected_keys:
            assert key in data, f"Response JSON missing key: {key}"
    return data


def assert_valid_pagination(data: dict[str, Any]) -> None:
    """Assert that paginated response data has valid structure."""
    assert "total" in data, "Paginated response must have 'total'"
    assert "items" in data or "results" in data, "Paginated response must have 'items' or 'results'"
    assert isinstance(data["total"], int), "Total must be integer"


def assert_valid_health_response(data: dict[str, Any]) -> None:
    """Assert that a health check response is valid."""
    assert "status" in data, "Health response must have 'status'"
    assert data["status"] in ("healthy", "degraded", "unhealthy"), f"Invalid health status: {data['status']}"


def assert_datetime_is_recent(dt: datetime, max_age_seconds: float = 60.0) -> None:
    """Assert that a datetime is recent (within max_age_seconds of now)."""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age = abs((now - dt).total_seconds())
    assert age <= max_age_seconds, f"Datetime is {age:.1f}s old, max allowed is {max_age_seconds}s"


def assert_dict_contains(data: dict[str, Any], expected: dict[str, Any]) -> None:
    """Assert that data dict contains all expected key-value pairs."""
    for key, value in expected.items():
        assert key in data, f"Key '{key}' not found in data"
        assert data[key] == value, f"Key '{key}': expected {value!r}, got {data[key]!r}"


def assert_exception_type(exc: BaseException, exc_type: type) -> None:
    """Assert that an exception is of the expected type."""
    assert isinstance(exc, exc_type), f"Expected {exc_type.__name__}, got {type(exc).__name__}"
