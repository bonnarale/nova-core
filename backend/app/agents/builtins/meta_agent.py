"""MetaAgent — orchestrates self-evolution cycles for NOVA CORE.

Runs CapabilityAuditor → identifies gaps → creates ImprovementGoals →
delegates implementation to OpenCodeAgent → tests → measures results.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent
from app.learning.models import ImprovementGoal

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="meta",
    name="Meta Agent",
    role="meta",
    description="Orchestrates self-evolution cycles — audits capabilities, creates goals, delegates implementation, and measures results.",
    system_prompt="You are the Meta Agent. You analyze and improve the NOVA CORE agent system itself.",
    allowed_tools=["capability_audit", "improvement_planning", "agent_creation"],
    memory_scope="session",
    permissions={"can_modify_agents": True, "requires_approval": True},
    supported_models=[],
)


class MetaAgent(BaseAgent):
    """Agent that orchestrates self-evolution cycles.

    Flow: audit → identify gaps → create goals → delegate to OpenCodeAgent → test → measure
    """

    def __init__(
        self,
        auditor: Any = None,
        opencode_agent: Any = None,
        agent_manager: Any = None,
    ) -> None:
        super().__init__(agent_id="meta")
        self._auditor = auditor
        self._opencode_agent = opencode_agent
        self._agent_manager = agent_manager

    @property
    def definition(self) -> AgentDefinition:
        return _DEFINITION

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a self-evolution cycle.

        Args:
            task: The evolution task description (natural language or "run_evolution_cycle")
            context: Runtime context with optional overrides

        Returns:
            Dict with targets, improvements, and summary.
        """
        # Accept both explicit command and natural language
        task_lower = task.lower().strip()
        if task == "run_evolution_cycle" or any(keyword in task_lower for keyword in [
            "self-improvement", "improve", "evolve", "audit", "evolution cycle",
            "self-evolve", "capability", "meta"
        ]):
            return await self._run_evolution_cycle(context)
        return {
            "agent": self.agent_id,
            "status": "error",
            "error": f"Unknown task: {task}",
        }

    async def _run_evolution_cycle(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run a full self-evolution cycle."""
        if self._auditor is None:
            return {
                "agent": self.agent_id,
                "status": "error",
                "error": "CapabilityAuditor not available",
            }

        # 1. Run audit
        audit_report = await self._auditor.audit()

        # 2. Rank gaps by impact
        targets = self._rank_gaps(audit_report)

        # 3. Select top 3 improvement targets
        top_targets = targets[:3]

        # 4. Create ImprovementGoal per target
        goals_created = []
        for target in top_targets:
            goal = ImprovementGoal(
                id=ImprovementGoal.new_id(),
                target_strategy=target["agent_id"],
                proposed_change=target["description"],
                confidence=target.get("confidence", 0.7),
                evidence={"audit_report": audit_report.to_dict()},
                status="evolving",
            )
            goals_created.append(goal.to_dict())

        # 5. Delegate to OpenCodeAgent (if available)
        improvements = []
        if self._opencode_agent is not None and top_targets:
            for target in top_targets:
                try:
                    result = await self._opencode_agent.execute(
                        task=f"Improve agent capability: {target['description']}",
                        context={
                            "target": target,
                            "audit_report": audit_report.to_dict(),
                            "user_id": context.get("user_id"),
                        },
                    )
                    improvements.append({
                        "target": target,
                        "result": result,
                    })
                except Exception as exc:
                    logger.debug("OpenCodeAgent delegation failed: %s", exc)
                    improvements.append({
                        "target": target,
                        "result": {"status": "error", "error": str(exc)},
                    })

        # 6. Build summary
        summary = (
            f"Audit found {len(audit_report.uncovered_intents)} uncovered intents, "
            f"{len(audit_report.low_performing_agents)} low-performing agents. "
            f"Created {len(goals_created)} improvement goals. "
            f"Delegated {len(improvements)} improvements."
        )

        return {
            "agent": self.agent_id,
            "status": "completed",
            "targets": top_targets,
            "goals_created": goals_created,
            "improvements": improvements,
            "audit_report": audit_report.to_dict(),
            "summary": summary,
        }

    def _rank_gaps(self, audit_report: Any) -> list[dict[str, Any]]:
        """Rank audit gaps by impact for prioritization.

        Uncovered intents rank higher than low-performing agents.
        Low-performing agents with very low success rates rank higher.
        """
        targets = []

        # Uncovered intents are high-priority gaps
        for intent in audit_report.uncovered_intents:
            targets.append({
                "type": "uncovered_intent",
                "agent_id": intent,
                "description": f"No agent registered for intent '{intent}'",
                "priority": 1,
                "confidence": 0.8,
            })

        # Low-performing agents are medium-priority
        for perf in audit_report.low_performing_agents:
            priority = 2 if perf.success_rate < 0.3 else 3
            targets.append({
                "type": "low_performing",
                "agent_id": perf.agent_id,
                "description": (
                    f"Agent '{perf.agent_id}' has low success rate "
                    f"({perf.success_rate:.1%}). Needs improvement."
                ),
                "priority": priority,
                "confidence": 0.7,
                "success_rate": perf.success_rate,
            })

        # Sort by priority (lower = higher priority)
        targets.sort(key=lambda t: (t["priority"], -t.get("confidence", 0)))
        return targets
