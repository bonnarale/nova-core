"""Event serialization — JSON and bytes serialization for events."""

from __future__ import annotations

import json
from typing import Any

from app.events.base import EventSerializer
from app.events.schemas import Event


class JSONEventSerializer(EventSerializer):
    """JSON-based event serializer."""

    def serialize(self, event: Event) -> str:
        return event.model_dump_json()

    def deserialize(self, data: str) -> Event:
        return Event.model_validate_json(data)

    def serialize_bytes(self, event: Event) -> bytes:
        return self.serialize(event).encode("utf-8")

    def deserialize_bytes(self, data: bytes) -> Event:
        return self.deserialize(data.decode("utf-8"))

    def serialize_dict(self, event: Event) -> dict[str, Any]:
        return event.model_dump()

    def deserialize_dict(self, data: dict[str, Any]) -> Event:
        return Event.model_validate(data)
