"""Cron expression parser — lightweight cron support without external deps."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional


class CronExpression:
    """Parses and evaluates 5-field cron expressions (minute hour day month weekday)."""

    def __init__(self, expression: str) -> None:
        self._raw = expression.strip()
        self._parts = self._raw.split()
        if len(self._parts) != 5:
            raise ValueError(f"Invalid cron expression (expected 5 fields): {self._raw}")
        self._minutes = self._parse_field(self._parts[0], 0, 59)
        self._hours = self._parse_field(self._parts[1], 0, 23)
        self._days = self._parse_field(self._parts[2], 1, 31)
        self._months = self._parse_field(self._parts[3], 1, 12)
        self._weekdays = self._parse_field(self._parts[4], 0, 6)

    def matches(self, dt: datetime) -> bool:
        cron_weekday = (dt.weekday() + 1) % 7
        return (
            dt.minute in self._minutes
            and dt.hour in self._hours
            and dt.day in self._days
            and dt.month in self._months
            and cron_weekday in self._weekdays
        )

    def next_run(self, after: datetime | None = None) -> Optional[datetime]:
        start = after or datetime.now(timezone.utc)
        candidate = start.replace(second=0, microsecond=0)
        for _ in range(525600):
            candidate = candidate.replace(minute=candidate.minute + 1) if candidate.minute < 59 else candidate.replace(minute=0, hour=candidate.hour + 1) if candidate.hour < 23 else candidate.replace(minute=0, hour=0, day=candidate.day + 1)
            if self.matches(candidate):
                return candidate
        return None

    @property
    def raw(self) -> str:
        return self._raw

    @staticmethod
    def _parse_field(field_str: str, min_val: int, max_val: int) -> set[int]:
        values: set[int] = set()
        for part in field_str.split(","):
            if "/" in part:
                base, step_str = part.split("/", 1)
                step = int(step_str)
                start = min_val if base == "*" else int(base)
                values.update(range(start, max_val + 1, step))
            elif "-" in part:
                lo, hi = part.split("-", 1)
                values.update(range(int(lo), int(hi) + 1))
            elif part == "*":
                values.update(range(min_val, max_val + 1))
            else:
                values.add(int(part))
        return values
