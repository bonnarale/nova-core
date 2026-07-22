"""Intelligent agent dispatcher with capability-based routing."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.capabilities import AgentCapability, CapabilityRegistry
from app.agents.context import AgentExecutionContext
from app.agents.lifecycle import AgentLifecycle
from app.agents.policies import ExecutionPolicy, get_policy

logger = logging.getLogger(__name__)


class DispatchResult:
    """Result of a dispatch decision."""

    __slots__ = ("agent_id", "confidence", "reason", "score")

    def __init__(
        self,
        agent_id: str = "",
        confidence: float = 0.0,
        reason: str = "",
        score: float = 0.0,
    ) -> None:
        self.agent_id = agent_id
        self.confidence = confidence
        self.reason = reason
        self.score = score

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
            "score": round(self.score, 4),
        }


class AgentDispatcher:
    """Routes tasks to the best available agent based on capabilities,
    workload, availability, priority, execution policy, and confidence.
    """

    def __init__(self, capability_registry: CapabilityRegistry) -> None:
        self._capabilities = capability_registry
        self._workloads: dict[str, int] = {}
        self._histories: dict[str, list[float]] = {}

    def score_agents(
        self,
        candidates: list[tuple[str, AgentCapability]],
        context: AgentExecutionContext,
        lifecycles: dict[str, AgentLifecycle] | None = None,
    ) -> list[DispatchResult]:
        """Score and rank candidate agents for a task."""
        results: list[DispatchResult] = []

        for agent_id, cap in candidates:
            score = 0.0
            reasons: list[str] = []

            # Priority score (lower number = higher priority)
            priority_score = 1.0 - (cap.priority / 10.0)
            score += priority_score * 0.3
            reasons.append(f"priority={cap.priority}")

            # Workload score (lower workload = better)
            workload = self._workloads.get(agent_id, 0)
            capacity = max(cap.concurrency_limit, 1)
            workload_ratio = workload / capacity
            workload_score = max(0, 1.0 - workload_ratio)
            score += workload_score * 0.25
            reasons.append(f"workload={workload}/{capacity}")

            # Availability score
            if lifecycles:
                lc = lifecycles.get(agent_id)
                if lc and lc.state.value in ("READY", "COMPLETED"):
                    score += 0.2
                    reasons.append("available=yes")
                else:
                    score += 0.0
                    reasons.append("available=no")
            else:
                score += 0.15
                reasons.append("available=unknown")

            # Policy score
            policy = get_policy(cap.execution_policy)
            if policy.can_run_concurrently():
                score += 0.1
            if context.priority <= 2 and policy.should_run_in_background():
                score -= 0.1
            reasons.append(f"policy={cap.execution_policy}")

            # Confidence score from context
            confidence = 0.5
            if context.metadata.get("intent"):
                intent = context.metadata["intent"]
                if cap.matches_intent(intent):
                    confidence = 0.9
                    reasons.append("intent_match=yes")
                else:
                    confidence = 0.3
                    reasons.append("intent_match=no")
            score += confidence * 0.15

            results.append(DispatchResult(
                agent_id=agent_id,
                confidence=confidence,
                reason="; ".join(reasons),
                score=score,
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def dispatch(
        self,
        context: AgentExecutionContext,
        lifecycles: dict[str, AgentLifecycle] | None = None,
    ) -> DispatchResult | None:
        """Find the best agent for the given context."""
        intent = context.metadata.get("intent")
        task_type = context.metadata.get("task_type")
        tags = context.metadata.get("tags")

        candidates = self._capabilities.find_capable(
            intent=intent,
            task_type=task_type,
            tags=tags,
        )

        if not candidates:
            logger.warning("Dispatcher: no capable agents found for task %s", context.task_id)
            return None

        scored = self.score_agents(candidates, context, lifecycles)
        if not scored:
            return None

        best = scored[0]
        self._workloads[best.agent_id] = self._workloads.get(best.agent_id, 0) + 1
        self._histories.setdefault(best.agent_id, []).append(time.time())

        logger.info(
            "Dispatcher: routed %s -> %s (score=%.3f)",
            context.task_id, best.agent_id, best.score,
        )
        return best

    def release(self, agent_id: str) -> None:
        self._workloads[agent_id] = max(0, self._workloads.get(agent_id, 0) - 1)

    def get_workload(self, agent_id: str) -> int:
        return self._workloads.get(agent_id, 0)

    def get_all_workloads(self) -> dict[str, int]:
        return dict(self._workloads)

    def get_history(self, agent_id: str) -> list[float]:
        return list(self._histories.get(agent_id, []))

    def to_dict(self) -> dict[str, Any]:
        return {
            "workloads": dict(self._workloads),
            "dispatch_count": sum(self._histories.get(aid, [0]) and len(self._histories.get(aid, [])) for aid in self._histories),
        }
