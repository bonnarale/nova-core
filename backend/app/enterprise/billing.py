"""Billing — subscription metadata, usage tracking, quotas, invoices, external provider integration."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.enterprise.enums import BillingStatus


class Subscription:
    """Represents a billing subscription."""

    __slots__ = (
        "id", "org_id", "plan", "status",
        "started_at", "current_period_end", "metadata",
    )

    def __init__(
        self,
        org_id: str,
        plan: str = "community",
        status: BillingStatus = BillingStatus.ACTIVE,
        current_period_end: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.org_id = org_id
        self.plan = plan
        self.status = status
        self.started_at = time.time()
        self.current_period_end = current_period_end
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "plan": self.plan,
            "status": self.status.value,
            "started_at": self.started_at,
            "current_period_end": self.current_period_end,
            "metadata": self.metadata,
        }


class UsageRecord:
    """Represents a usage record."""

    __slots__ = ("id", "org_id", "metric", "quantity", "timestamp")

    def __init__(self, org_id: str, metric: str, quantity: float) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.org_id = org_id
        self.metric = metric
        self.quantity = quantity
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "metric": self.metric,
            "quantity": self.quantity,
            "timestamp": self.timestamp,
        }


class Invoice:
    """Represents an invoice (metadata only)."""

    __slots__ = ("id", "org_id", "amount", "currency", "status", "issued_at", "metadata")

    def __init__(
        self,
        org_id: str,
        amount: float = 0.0,
        currency: str = "USD",
        status: str = "pending",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.org_id = org_id
        self.amount = amount
        self.currency = currency
        self.status = status
        self.issued_at = time.time()
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "issued_at": self.issued_at,
            "metadata": self.metadata,
        }


class BillingManager:
    """Manages billing operations with thread-safe in-memory storage."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, Subscription] = {}
        self._usage: list[UsageRecord] = []
        self._invoices: list[Invoice] = []
        self._lock = threading.RLock()

    async def get_subscription(self, org_id: str) -> Subscription | None:
        with self._lock:
            return self._subscriptions.get(org_id)

    async def create_subscription(
        self,
        org_id: str,
        plan: str = "community",
        status: BillingStatus = BillingStatus.ACTIVE,
    ) -> Subscription:
        sub = Subscription(org_id=org_id, plan=plan, status=status)
        with self._lock:
            self._subscriptions[org_id] = sub
        return sub

    async def record_usage(self, org_id: str, metric: str, quantity: float) -> UsageRecord:
        record = UsageRecord(org_id=org_id, metric=metric, quantity=quantity)
        with self._lock:
            self._usage.append(record)
        return record

    async def get_usage(self, org_id: str, period: str = "current") -> dict[str, Any]:
        with self._lock:
            org_usage = [u for u in self._usage if u.org_id == org_id]
            totals: dict[str, float] = {}
            for u in org_usage:
                totals[u.metric] = totals.get(u.metric, 0.0) + u.quantity
            return {"org_id": org_id, "period": period, "totals": totals, "record_count": len(org_usage)}

    async def list_invoices(self, org_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [i.to_dict() for i in self._invoices if i.org_id == org_id]

    async def create_invoice(
        self,
        org_id: str,
        amount: float = 0.0,
        currency: str = "USD",
    ) -> Invoice:
        invoice = Invoice(org_id=org_id, amount=amount, currency=currency, status="pending")
        with self._lock:
            self._invoices.append(invoice)
        return invoice

    def get_subscription_sync(self, org_id: str) -> Subscription | None:
        with self._lock:
            return self._subscriptions.get(org_id)

    def count_subscriptions(self) -> int:
        with self._lock:
            return len(self._subscriptions)

    def count_usage_records(self) -> int:
        with self._lock:
            return len(self._usage)
