"""Database metrics collection."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app.db.enums import QueryOperation
from app.db.models import DatabaseMetrics

logger = logging.getLogger(__name__)


class DatabaseMetricsCollector:
    """Collects queries, inserts, updates, deletes, transactions, and latency metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_queries = 0
        self._total_inserts = 0
        self._total_updates = 0
        self._total_deletes = 0
        self._total_selects = 0
        self._transaction_count = 0
        self._rollback_count = 0
        self._commit_count = 0
        self._latencies: list[float] = []
        self._start_time = time.time()

    def record_query(self, operation: str = "select", latency_ms: float = 0.0) -> None:
        with self._lock:
            self._total_queries += 1
            if operation == QueryOperation.SELECT.value:
                self._total_selects += 1
            elif operation == QueryOperation.INSERT.value:
                self._total_inserts += 1
            elif operation == QueryOperation.UPDATE.value:
                self._total_updates += 1
            elif operation == QueryOperation.DELETE.value:
                self._total_deletes += 1
            if latency_ms > 0:
                self._latencies.append(latency_ms)
                if len(self._latencies) > 10000:
                    self._latencies = self._latencies[-5000:]

    def record_transaction(self, committed: bool = True) -> None:
        with self._lock:
            self._transaction_count += 1
            if committed:
                self._commit_count += 1
            else:
                self._rollback_count += 1

    def record_rollback(self) -> None:
        with self._lock:
            self._rollback_count += 1

    def get_statistics(self) -> dict[str, Any]:
        with self._lock:
            avg_latency = (
                sum(self._latencies) / len(self._latencies)
                if self._latencies
                else 0.0
            )
            return {
                "total_queries": self._total_queries,
                "total_inserts": self._total_inserts,
                "total_updates": self._total_updates,
                "total_deletes": self._total_deletes,
                "total_selects": self._total_selects,
                "transaction_count": self._transaction_count,
                "rollback_count": self._rollback_count,
                "commit_count": self._commit_count,
                "average_query_latency_ms": round(avg_latency, 2),
                "uptime_seconds": round(time.time() - self._start_time, 2),
            }

    def reset(self) -> None:
        with self._lock:
            self._total_queries = 0
            self._total_inserts = 0
            self._total_updates = 0
            self._total_deletes = 0
            self._total_selects = 0
            self._transaction_count = 0
            self._rollback_count = 0
            self._commit_count = 0
            self._latencies.clear()
            self._start_time = time.time()
