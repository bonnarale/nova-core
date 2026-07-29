"""Trigger strategies — cron, interval, datetime, event, dependency, custom, manual."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.scheduler.base import TriggerStrategy
from app.scheduler.cron import CronExpression
from app.scheduler.schemas import TriggerConfig, TriggerType

logger = logging.getLogger(__name__)


class CronTriggerStrategy(TriggerStrategy):
    @property
    def name(self) -> str:
        return "cron"

    async def next_run_time(self, config: TriggerConfig, last_run: Any = None) -> Optional[datetime]:
        if not config.cron_expression:
            return None
        expr = CronExpression(config.cron_expression)
        after = last_run or datetime.now(timezone.utc)
        return expr.next_run(after)

    async def should_run(self, config: TriggerConfig, last_run: Any = None) -> bool:
        if not config.cron_expression:
            return False
        expr = CronExpression(config.cron_expression)
        return expr.matches(datetime.now(timezone.utc))


class IntervalTriggerStrategy(TriggerStrategy):
    @property
    def name(self) -> str:
        return "interval"

    async def next_run_time(self, config: TriggerConfig, last_run: Any = None) -> Optional[datetime]:
        if not config.interval_seconds:
            return None
        base = last_run or datetime.now(timezone.utc)
        return base + timedelta(seconds=config.interval_seconds)

    async def should_run(self, config: TriggerConfig, last_run: Any = None) -> bool:
        if not config.interval_seconds:
            return False
        if last_run is None:
            return True
        now = datetime.now(timezone.utc)
        return (now - last_run).total_seconds() >= config.interval_seconds


class DateTimeTriggerStrategy(TriggerStrategy):
    @property
    def name(self) -> str:
        return "datetime"

    async def next_run_time(self, config: TriggerConfig, last_run: Any = None) -> Optional[datetime]:
        return config.run_at

    async def should_run(self, config: TriggerConfig, last_run: Any = None) -> bool:
        if not config.run_at:
            return False
        return datetime.now(timezone.utc) >= config.run_at


class EventTriggerStrategy(TriggerStrategy):
    @property
    def name(self) -> str:
        return "event"

    async def next_run_time(self, config: TriggerConfig, last_run: Any = None) -> Optional[datetime]:
        return None

    async def should_run(self, config: TriggerConfig, last_run: Any = None) -> bool:
        return False


class DependencyTriggerStrategy(TriggerStrategy):
    @property
    def name(self) -> str:
        return "dependency"

    async def next_run_time(self, config: TriggerConfig, last_run: Any = None) -> Optional[datetime]:
        return None

    async def should_run(self, config: TriggerConfig, last_run: Any = None) -> bool:
        return False


class CustomTriggerStrategy(TriggerStrategy):
    @property
    def name(self) -> str:
        return "custom"

    async def next_run_time(self, config: TriggerConfig, last_run: Any = None) -> Optional[datetime]:
        return None

    async def should_run(self, config: TriggerConfig, last_run: Any = None) -> bool:
        return config.custom_config.get("should_run", False)


class ManualTriggerStrategy(TriggerStrategy):
    @property
    def name(self) -> str:
        return "manual"

    async def next_run_time(self, config: TriggerConfig, last_run: Any = None) -> Optional[datetime]:
        return None

    async def should_run(self, config: TriggerConfig, last_run: Any = None) -> bool:
        return False


DEFAULT_STRATEGIES: dict[TriggerType, TriggerStrategy] = {
    TriggerType.CRON: CronTriggerStrategy(),
    TriggerType.INTERVAL: IntervalTriggerStrategy(),
    TriggerType.DATETIME: DateTimeTriggerStrategy(),
    TriggerType.EVENT: EventTriggerStrategy(),
    TriggerType.DEPENDENCY: DependencyTriggerStrategy(),
    TriggerType.CUSTOM: CustomTriggerStrategy(),
    TriggerType.MANUAL: ManualTriggerStrategy(),
}
