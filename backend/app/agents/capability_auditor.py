"""CapabilityAuditor — cross-references IntentType enum with registered agents.

Discovers uncovered intents (no agent handles them) and low-performing
agents (success_rate < threshold) from SuccessTracker telemetry.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.cognitive.context import IntentType

logger = logging.getLogger(__name__)

# Default threshold for low-performing agent detection
DEFAULT_SUCCESS_RATE_THRESHOLD = 0.6


@dataclass
class AgentPerformance:
    """Performance metrics for a single agent."""

    agent_id: str
    success_rate: float
    execution_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "success_rate": self.success_rate,
            "execution_count": self.execution_count,
        }


@dataclass
class AuditReport:
    """Structured report from a capability audit."""

    uncovered_intents: list[str] = field(default_factory=list)
    low_performing_agents: list[AgentPerformance] = field(default_factory=list)
    total_agents: int = 0
    coverage_ratio: float = 0.0
    all_intents: list[str] = field(default_factory=list)
    registered_agents: list[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "uncovered_intents": self.uncovered_intents,
            "low_performing_agents": [a.to_dict() for a in self.low_performing_agents],
            "total_agents": self.total_agents,
            "coverage_ratio": self.coverage_ratio,
            "all_intents": self.all_intents,
            "registered_agents": self.registered_agents,
            "timestamp": self.timestamp,
        }


class CapabilityAuditor:
    """Audits NOVA CORE's agent capabilities against the IntentType enum.

    Identifies:
    - Intents with no registered agent (coverage gaps)
    - Agents with low success rates (performance gaps)
    """

    def __init__(
        self,
        agent_manager: Any,
        success_tracker: Any,
        success_rate_threshold: float = DEFAULT_SUCCESS_RATE_THRESHOLD,
    ) -> None:
        self._agent_manager = agent_manager
        self._success_tracker = success_tracker
        self._success_rate_threshold = success_rate_threshold

    async def audit(self) -> AuditReport:
        """Run a full capability audit.

        Cross-references IntentType enum values against registered agents
        to find uncovered intents, and queries SuccessTracker for
        low-performing agents.
        """
        # 1. Get all registered agents
        runtime_agents = self._agent_manager.list_runtime_agents()
        registered_agent_ids = [a.agent_id for a in runtime_agents]

        # 2. Get all IntentType values
        all_intents = [intent.value for intent in IntentType]

        # 3. Cross-reference: find intents with no agent
        covered_intents = set()
        for agent in runtime_agents:
            # Check agent definition for supported intents
            definition = agent.definition
            if hasattr(definition, "role"):
                covered_intents.add(definition.role.lower())
            # Also check capability tags if available
            if hasattr(definition, "allowed_tools"):
                for tool in (definition.allowed_tools or []):
                    covered_intents.add(tool.lower())

        # Map intent values to lowercase for comparison
        covered_lower = {c.lower() for c in covered_intents}
        uncovered_intents = [
            intent for intent in all_intents
            if intent.lower() not in covered_lower
        ]

        # 4. Get success rates from SuccessTracker
        low_performing: list[AgentPerformance] = []
        try:
            strategy_effectiveness = await self._success_tracker.compute_strategy_effectiveness()
            for strategy_name, success_rate in strategy_effectiveness.items():
                if success_rate < self._success_rate_threshold:
                    # Try to find matching agent by strategy name
                    agent_id = strategy_name  # strategy_used maps to agent_id
                    low_performing.append(
                        AgentPerformance(
                            agent_id=agent_id,
                            success_rate=success_rate,
                            execution_count=0,  # Would need additional tracking for count
                        )
                    )
        except Exception as exc:
            logger.debug("Failed to compute strategy effectiveness: %s", exc)

        # 5. Compute coverage ratio
        total_intents = len(all_intents)
        covered_count = total_intents - len(uncovered_intents)
        coverage_ratio = covered_count / total_intents if total_intents > 0 else 0.0

        return AuditReport(
            uncovered_intents=uncovered_intents,
            low_performing_agents=low_performing,
            total_agents=len(registered_agent_ids),
            coverage_ratio=coverage_ratio,
            all_intents=all_intents,
            registered_agents=registered_agent_ids,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
