"""Knowledge extractor — extracts reusable knowledge from completed executions.

Analyzes task goals, step artifacts, and execution results to produce
KnowledgeArtifacts tagged by type (procedure, pattern, fact, etc.).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.learning.base import KnowledgeExtractor
from app.learning.models import ArtifactType, ExtractedKnowledge, KnowledgeArtifact

logger = logging.getLogger(__name__)

_ERROR_KEYWORDS = frozenset({
    "error", "exception", "traceback", "failed", "failure",
    "timeout", "refused", "denied", "crash", "bug",
})

_OPTIMIZATION_KEYWORDS = frozenset({
    "optimize", "speed", "performance", "cache", "faster",
    "improve", "refactor", "efficient", "bottleneck",
})

_STRATEGY_KEYWORDS = frozenset({
    "strategy", "approach", "method", "technique", "pattern",
    "best practice", "convention", "workflow",
})


class DefaultKnowledgeExtractor(KnowledgeExtractor):
    """Rule-based extractor that produces knowledge artifacts from execution data.

    The extractor inspects:
      - ``goal`` / ``description`` from the task
      - ``steps`` and their ``artifacts``
      - ``events`` emitted during execution
      - ``status`` to determine success/failure

    Each produced artifact is tagged and scored for importance.
    """

    async def extract(
        self,
        execution_data: dict[str, Any],
        task_data: dict[str, Any] | None = None,
    ) -> ExtractedKnowledge:
        artifacts: list[KnowledgeArtifact] = []
        task = task_data or {}
        execution_id = execution_data.get("id", "")
        task_id = task.get("id", "")
        user_id = task.get("user_id") or execution_data.get("user_id")
        agent_id = task.get("assigned_agent") or execution_data.get("agent_id")
        goal = task.get("goal", "")
        status = execution_data.get("status", task.get("status", ""))
        step_artifacts = task.get("artifacts", {})
        events = task.get("events", [])

        if goal:
            proc = self._extract_procedure(goal, step_artifacts, status)
            if proc:
                artifacts.append(proc)

        if events:
            error_art = self._extract_error_handling(events, goal)
            if error_art:
                artifacts.append(error_art)

        if goal:
            pattern = self._extract_pattern(goal, step_artifacts)
            if pattern:
                artifacts.append(pattern)

        optimization = self._extract_optimization(goal, step_artifacts)
        if optimization:
            artifacts.append(optimization)

        if goal:
            strategy = self._extract_strategy(goal, status, agent_id)
            if strategy:
                artifacts.append(strategy)

        for art in artifacts:
            art.source_execution_id = execution_id
            art.source_task_id = task_id
            art.user_id = user_id
            art.agent_id = agent_id

        confidence = self._compute_confidence(artifacts, status)

        logger.debug(
            "Extracted %d artifacts from execution %s (status=%s)",
            len(artifacts), execution_id, status,
        )

        return ExtractedKnowledge(
            artifacts=artifacts,
            execution_id=execution_id,
            task_id=task_id,
            extraction_method="default_rule_based",
            confidence=confidence,
        )

    def _extract_procedure(
        self,
        goal: str,
        step_artifacts: dict[str, Any],
        status: str,
    ) -> KnowledgeArtifact | None:
        if not goal:
            return None

        parts: list[str] = [f"Procedure for: {goal}"]
        if step_artifacts:
            parts.append("Steps executed successfully.")
        if status in ("COMPLETED", "DONE", "SUCCEEDED"):
            parts.append(f"Result: Goal achieved (status={status}).")

        content = " ".join(parts)
        tags = self._extract_tags(goal)

        return KnowledgeArtifact(
            id=KnowledgeArtifact.new_id(),
            artifact_type=ArtifactType.PROCEDURE.value,
            content=content,
            summary=f"Procedure to achieve: {goal[:100]}",
            tags=tags,
            confidence=0.7,
            importance_score=self._score_importance(goal, status, ArtifactType.PROCEDURE),
        )

    def _extract_error_handling(
        self,
        events: list[dict[str, Any]],
        goal: str,
    ) -> KnowledgeArtifact | None:
        error_events = [
            e for e in events
            if any(
                kw in str(e.get("type", "")).lower()
                for kw in ("error", "failed", "failure")
            )
        ]
        if not error_events:
            return None

        error_types = [e.get("type", "unknown") for e in error_events]
        content = (
            f"Errors encountered during task: {goal}. "
            f"Error types: {', '.join(error_types)}. "
            f"Count: {len(error_events)}."
        )
        tags = self._extract_tags(goal) + ["error", "debugging"]

        return KnowledgeArtifact(
            id=KnowledgeArtifact.new_id(),
            artifact_type=ArtifactType.ERROR_HANDLING.value,
            content=content,
            summary=f"Errors during: {goal[:80]}",
            tags=tags,
            confidence=0.6,
            importance_score=self._score_importance(goal, "FAILED", ArtifactType.ERROR_HANDLING),
        )

    def _extract_pattern(
        self,
        goal: str,
        step_artifacts: dict[str, Any],
    ) -> KnowledgeArtifact | None:
        if not goal:
            return None

        lower_goal = goal.lower()
        is_pattern = any(kw in lower_goal for kw in _STRATEGY_KEYWORDS)
        if not is_pattern and len(step_artifacts) < 2:
            return None

        content = f"Pattern identified in task: {goal}."
        if step_artifacts:
            content += f" Involved {len(step_artifacts)} artifact(s)."

        tags = self._extract_tags(goal) + ["pattern"]
        return KnowledgeArtifact(
            id=KnowledgeArtifact.new_id(),
            artifact_type=ArtifactType.PATTERN.value,
            content=content,
            summary=f"Pattern from: {goal[:80]}",
            tags=tags,
            confidence=0.5,
            importance_score=self._score_importance(goal, "COMPLETED", ArtifactType.PATTERN),
        )

    def _extract_optimization(
        self,
        goal: str,
        step_artifacts: dict[str, Any],
    ) -> KnowledgeArtifact | None:
        lower_goal = goal.lower()
        if not any(kw in lower_goal for kw in _OPTIMIZATION_KEYWORDS):
            return None

        content = f"Optimization opportunity identified: {goal}."
        tags = self._extract_tags(goal) + ["optimization"]
        return KnowledgeArtifact(
            id=KnowledgeArtifact.new_id(),
            artifact_type=ArtifactType.OPTIMIZATION.value,
            content=content,
            summary=f"Optimization: {goal[:80]}",
            tags=tags,
            confidence=0.55,
            importance_score=self._score_importance(goal, "COMPLETED", ArtifactType.OPTIMIZATION),
        )

    def _extract_strategy(
        self,
        goal: str,
        status: str,
        agent_id: str | None,
    ) -> KnowledgeArtifact | None:
        if not goal:
            return None

        lower_goal = goal.lower()
        if not any(kw in lower_goal for kw in _STRATEGY_KEYWORDS):
            return None

        content = f"Strategy applied: {goal}"
        if agent_id:
            content += f" (agent={agent_id})"
        content += f". Outcome: {status}."

        tags = self._extract_tags(goal) + ["strategy"]
        return KnowledgeArtifact(
            id=KnowledgeArtifact.new_id(),
            artifact_type=ArtifactType.STRATEGY.value,
            content=content,
            summary=f"Strategy: {goal[:80]}",
            tags=tags,
            confidence=0.65,
            importance_score=self._score_importance(goal, status, ArtifactType.STRATEGY),
        )

    @staticmethod
    def _extract_tags(goal: str) -> list[str]:
        words = re.findall(r"[a-zA-Z]{3,}", goal.lower())
        stopwords = {
            "the", "and", "for", "that", "this", "with", "from",
            "are", "was", "were", "been", "being", "have", "has",
            "had", "does", "did", "will", "would", "could", "should",
            "may", "might", "can", "shall", "not", "but", "also",
            "into", "over", "such", "than", "then", "when", "where",
        }
        return sorted({w for w in words if w not in stopwords})[:10]

    @staticmethod
    def _score_importance(
        goal: str,
        status: str,
        artifact_type: ArtifactType,
    ) -> float:
        base = 0.3
        if status in ("COMPLETED", "DONE", "SUCCEEDED"):
            base += 0.2
        type_bonus = {
            ArtifactType.PROCEDURE: 0.15,
            ArtifactType.STRATEGY: 0.15,
            ArtifactType.ERROR_HANDLING: 0.1,
            ArtifactType.OPTIMIZATION: 0.1,
            ArtifactType.PATTERN: 0.05,
            ArtifactType.FACT: 0.05,
        }
        base += type_bonus.get(artifact_type, 0.0)
        length_bonus = min(len(goal) / 200, 0.15)
        base += length_bonus
        return round(min(base, 1.0), 3)

    @staticmethod
    def _compute_confidence(
        artifacts: list[KnowledgeArtifact],
        status: str,
    ) -> float:
        if not artifacts:
            return 0.0
        avg = sum(a.confidence for a in artifacts) / len(artifacts)
        if status in ("COMPLETED", "DONE", "SUCCEEDED"):
            avg = min(avg + 0.05, 1.0)
        return round(avg, 3)
