"""Approval system — automatic, human, policy, and threshold-based approvals."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from app.autonomy.enums import ApprovalType, RecommendationStatus


class ApprovalRecord:
    """A single approval record."""

    __slots__ = ("id", "recommendation_id", "approval_type", "status", "approver", "reason", "timestamp")

    def __init__(
        self,
        recommendation_id: str,
        approval_type: ApprovalType = ApprovalType.AUTOMATIC,
        status: RecommendationStatus = RecommendationStatus.PENDING,
        approver: str = "",
        reason: str = "",
    ) -> None:
        self.id = str(uuid.uuid4())[:12]
        self.recommendation_id = recommendation_id
        self.approval_type = approval_type
        self.status = status
        self.approver = approver
        self.reason = reason
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "recommendation_id": self.recommendation_id,
            "approval_type": self.approval_type.value,
            "status": self.status.value,
            "approver": self.approver,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


class ApprovalManager:
    """Manages approval workflows for autonomous recommendations."""

    def __init__(self, auto_approve_threshold: float = 0.7) -> None:
        self._auto_approve_threshold = auto_approve_threshold
        self._records: dict[str, ApprovalRecord] = {}
        self._approval_count = 0
        self._rejection_count = 0
        self._lock = threading.RLock()

    async def request_approval(self, recommendation: dict[str, Any]) -> dict[str, Any]:
        rec_id = recommendation.get("id", str(uuid.uuid4())[:12])
        confidence = recommendation.get("confidence", 0.0)
        risk = recommendation.get("risk_level", "low")
        if confidence >= self._auto_approve_threshold and risk == "low":
            record = ApprovalRecord(
                recommendation_id=rec_id,
                approval_type=ApprovalType.AUTOMATIC,
                status=RecommendationStatus.APPROVED,
                approver="system",
                reason="auto_approved",
            )
            with self._lock:
                self._records[record.id] = record
                self._approval_count += 1
            return record.to_dict()
        record = ApprovalRecord(
            recommendation_id=rec_id,
            approval_type=ApprovalType.HUMAN,
            status=RecommendationStatus.PENDING,
        )
        with self._lock:
            self._records[record.id] = record
        return record.to_dict()

    def is_auto_approved(self, recommendation: dict[str, Any]) -> bool:
        confidence = recommendation.get("confidence", 0.0)
        risk = recommendation.get("risk_level", "low")
        return confidence >= self._auto_approve_threshold and risk == "low"

    def approve(self, approval_id: str, approver: str = "system") -> bool:
        with self._lock:
            for record in self._records.values():
                if record.id == approval_id or record.recommendation_id == approval_id:
                    if record.status == RecommendationStatus.PENDING:
                        record.status = RecommendationStatus.APPROVED
                        record.approver = approver
                        self._approval_count += 1
                        return True
            return False

    def reject(self, approval_id: str, reason: str = "") -> bool:
        with self._lock:
            for record in self._records.values():
                if record.id == approval_id or record.recommendation_id == approval_id:
                    if record.status == RecommendationStatus.PENDING:
                        record.status = RecommendationStatus.REJECTED
                        record.reason = reason
                        self._rejection_count += 1
                        return True
            return False

    def get_record(self, record_id: str) -> ApprovalRecord | None:
        with self._lock:
            return self._records.get(record_id)

    def get_records(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            records = list(self._records.values())[-limit:]
            return [r.to_dict() for r in records]

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total": len(self._records),
                "approved": self._approval_count,
                "rejected": self._rejection_count,
                "pending": sum(1 for r in self._records.values() if r.status == RecommendationStatus.PENDING),
            }

    def set_auto_approve_threshold(self, threshold: float) -> None:
        with self._lock:
            self._auto_approve_threshold = max(0.0, min(1.0, threshold))
