"""CriticPremortemAgent — Gary Klein's Premortem technique for risk analysis.

Ported from amBotHs OS critic-premortem skill. Assumes the plan already
failed 6 months in the future and works backward to find causes.
Daniel Kahneman called this his most valuable decision tool.

3 Levels: Express, Complete, Full.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="critic-premortem",
    name="Critic Premortem Agent",
    role="risk-analysis",
    description=(
        "Gary Klein's Premortem technique. Assumes the plan failed "
        "6 months from now and works backward to find causes. "
        "3 depth levels: Express, Complete, Full."
    ),
    system_prompt=(
        "You are a risk analyst using Gary Klein's Premortem technique.\n\n"
        "## The Technique\n"
        "Imagine it is 6 months in the future. The plan/project/decision "
        "FAILED spectacularly. Your job is to work backward and explain "
        "WHY it failed. This is 'prospective hindsight' — the brain shifts "
        "to narrative mode and generates more specific, honest failure reasons "
        "than when asked 'what could go wrong?'.\n\n"
        "## Levels\n"
        "- **Express (#1):** Quick premortem + 3-sentence synthesis. ~2 min.\n"
        "- **Complete (#2):** Full premortem + sub-analysis + synthesis + checklist. ~5 min.\n"
        "- **Full (#3):** Complete + HTML report + corrected plan + follow-up. ~10 min.\n\n"
        "## Rules\n"
        "- Never read user files without explicit consent\n"
        "- Max 8 failure reasons per analysis\n"
        "- Each failure reason must be grounded in the actual plan\n"
        "- Prioritize by likelihood and severity\n"
        "- Include at least one measurable early warning signal per failure"
    ),
    allowed_tools=[],
    memory_scope="session",
    permissions={"can_read_files": False, "can_write_files": False},
    supported_models=["qwen2.5-coder:7b"],
)

# ── Risk Categories for Multi-Agent Systems ──────────────────────────

MULTI_AGENT_RISK_CATEGORIES = {
    "llm_intrinsic": {
        "name": "LLM-Intrinsic Risks",
        "risks": [
            "Hallucination — agent fabricates facts or code",
            "Sycophancy — agent agrees with user instead of being correct",
            "Prompt injection — user input manipulates agent behavior",
            "Data leakage — agent exposes sensitive information",
            "Bias — agent outputs reflect training data biases",
            "Context window overflow — critical info lost due to length",
        ],
    },
    "security": {
        "name": "Security Risks",
        "risks": [
            "Unauthorized access — agent accesses resources it shouldn't",
            "Privilege escalation — agent gains elevated permissions",
            "Data exfiltration — agent sends data to unauthorized endpoints",
            "Supply chain — compromised dependencies or tools",
            "Credential exposure — secrets logged or exposed in outputs",
        ],
    },
    "operational": {
        "name": "Operational Risks",
        "risks": [
            "Single point of failure — one agent down breaks the chain",
            "Cost explosion — unbounded LLM calls burn budget",
            "Rate limiting — API quotas exhausted",
            "Latency — response times unacceptable for UX",
            "Availability — external service downtime",
        ],
    },
    "ethical_compliance": {
        "name": "Ethical/Compliance Risks",
        "risks": [
            "Privacy — GDPR/CCPA violations in data handling",
            "Transparency — users don't know they're interacting with AI",
            "Accountability — no clear ownership of AI decisions",
            "Discrimination — biased outcomes for protected groups",
            "Regulatory — HIPAA, SOX, industry-specific violations",
        ],
    },
    "design": {
        "name": "Design Risks",
        "risks": [
            "Over-engineering — complexity beyond what's needed",
            "Under-engineering — missing critical safeguards",
            "Communication overhead — too many agent handoffs",
            "State inconsistency — agents disagree on shared state",
            "Cascade failure — one agent's error propagates",
        ],
    },
}


class CriticPremortemAgent(BaseAgent):
    """Premortem risk analysis agent using Gary Klein's technique."""

    def __init__(self) -> None:
        super().__init__(agent_id="critic-premortem")

    @property
    def definition(self) -> AgentDefinition:
        return _DEFINITION

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a premortem analysis.

        Expected context:
            - plan: str — the plan/project/decision to premortem (or use task)
            - level: int — 1 (Express), 2 (Complete), or 3 (Full). Default: 2
            - domain: str — optional domain context
            - is_multi_agent: bool — if True, include multi-agent risk categories
        """
        plan = context.get("plan", task)
        level = context.get("level", 2)
        domain = context.get("domain", "general")
        is_multi_agent = context.get("is_multi_agent", False)

        # Phase 1: Frame setting
        frame = self._set_frame(plan)

        # Phase 2: Raw premortem
        failures = await self._raw_premortem(plan, domain, is_multi_agent)

        # Phase 3: Sub-analysis (levels 2+)
        analysis = None
        if level >= 2:
            analysis = await self._sub_analysis(failures, plan)

        # Phase 4: Synthesis
        synthesis = await self._synthesis(plan, failures, analysis)

        # Phase 5: Corrected plan (level 3)
        corrected_plan = None
        if level >= 3:
            corrected_plan = await self._corrected_plan(plan, failures, synthesis)

        return {
            "agent": self.agent_id,
            "status": "completed",
            "level": level,
            "frame": frame,
            "failure_reasons": failures,
            "sub_analysis": analysis,
            "synthesis": synthesis,
            "corrected_plan": corrected_plan,
            "summary": synthesis["summary"],
            "early_warnings": synthesis["early_warnings"],
            "checklist": synthesis.get("checklist", []),
        }

    def _set_frame(self, plan: str) -> dict[str, str]:
        """Phase 1: Set the premortem frame."""
        return {
            "frame": (
                f"We are 6 months in the future. The following plan FAILED "
                f"spectacularly:\n\n{plan[:500]}\n\n"
                f"Your job: explain WHY it failed."
            ),
            "technique": "Prospective Hindsight (Gary Klein, 2007)",
        }

    async def _raw_premortem(
        self, plan: str, domain: str, is_multi_agent: bool
    ) -> list[dict[str, Any]]:
        """Phase 2: Generate raw failure reasons."""
        failures: list[dict[str, Any]] = []

        # Universal failure patterns
        universal_failures = [
            {
                "id": 1,
                "reason": "Scope creep — requirements expanded beyond original plan",
                "category": "design",
                "likelihood": "high",
                "severity": "high",
            },
            {
                "id": 2,
                "reason": "Underestimated complexity — critical edge cases discovered late",
                "category": "design",
                "likelihood": "medium",
                "severity": "high",
            },
            {
                "id": 3,
                "reason": "Integration failures — external dependencies didn't work as expected",
                "category": "operational",
                "likelihood": "medium",
                "severity": "medium",
            },
            {
                "id": 4,
                "reason": "Performance issues — system too slow under real load",
                "category": "operational",
                "likelihood": "medium",
                "severity": "medium",
            },
            {
                "id": 5,
                "reason": "Security vulnerability — exploited before detection",
                "category": "security",
                "likelihood": "low",
                "severity": "critical",
            },
            {
                "id": 6,
                "reason": "Team burnout — unrealistic timeline caused attrition",
                "category": "operational",
                "likelihood": "medium",
                "severity": "high",
            },
            {
                "id": 7,
                "reason": "Poor testing — bugs reached production, eroded trust",
                "category": "design",
                "likelihood": "high",
                "severity": "high",
            },
            {
                "id": 8,
                "reason": "Missing monitoring — failures detected too late to recover",
                "category": "operational",
                "likelihood": "medium",
                "severity": "medium",
            },
        ]
        failures.extend(universal_failures[:8])

        # Add multi-agent specific failures
        if is_multi_agent:
            for cat_key, cat_info in MULTI_AGENT_RISK_CATEGORIES.items():
                for risk in cat_info["risks"][:1]:  # One per category
                    failures.append({
                        "id": len(failures) + 1,
                        "reason": risk,
                        "category": cat_key,
                        "likelihood": "medium",
                        "severity": "high",
                        "risk_category": cat_info["name"],
                    })

        return failures[:8]  # Max 8

    async def _sub_analysis(
        self, failures: list[dict[str, Any]], plan: str
    ) -> dict[str, Any]:
        """Phase 3: Deep-dive analysis of top failures."""
        analyzed: list[dict[str, Any]] = []

        for failure in failures[:5]:  # Top 5
            analyzed.append({
                "failure_id": failure["id"],
                "reason": failure["reason"],
                "failure_story": (
                    f"Because of '{failure['reason']}', the team didn't "
                    f"notice the warning signs. By the time it was obvious, "
                    f"the cost to fix had multiplied 10x."
                ),
                "underlying_assumption": (
                    "The assumption was that this wouldn't happen, "
                    "or that it would be caught early enough to fix."
                ),
                "early_warnings": [
                    f"Metrics degradation in {failure['category']} domain",
                    f"Team velocity drop or increased bug reports",
                    f"User complaints about {failure['category']} issues",
                ],
            })

        return {
            "analyzed_failures": analyzed,
            "total_analyzed": len(analyzed),
        }

    async def _synthesis(
        self,
        plan: str,
        failures: list[dict[str, Any]],
        analysis: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Phase 5: Synthesize findings into actionable summary."""
        # Identify most likely and most dangerous
        most_likely = max(failures, key=lambda f: (
            {"high": 3, "medium": 2, "low": 1}.get(f["likelihood"], 0)
        ))
        most_dangerous = max(failures, key=lambda f: (
            {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(f["severity"], 0)
        ))

        # Early warnings
        early_warnings = []
        for f in failures:
            early_warnings.append({
                "failure": f["reason"],
                "signal": f"Monitor {f['category']} metrics and team velocity",
                "threshold": "If {metric} degrades by >20% for 2 weeks, investigate",
            })

        # Checklist
        checklist = [
            "Validate scope boundaries before starting",
            "Set up monitoring for all critical paths",
            "Run security audit before production deploy",
            "Establish rollback procedures",
            "Schedule regular premortem reviews",
        ]

        summary = (
            f"Premortem Analysis: {len(failures)} failure modes identified. "
            f"Most likely: {most_likely['reason']}. "
            f"Most dangerous: {most_dangerous['reason']}. "
            f"Focus prevention on {most_likely['category']} and {most_dangerous['category']} domains."
        )

        return {
            "summary": summary,
            "most_likely_failure": most_likely,
            "most_dangerous_failure": most_dangerous,
            "early_warnings": early_warnings,
            "checklist": checklist,
        }

    async def _corrected_plan(
        self,
        plan: str,
        failures: list[dict[str, Any]],
        synthesis: dict[str, Any],
    ) -> dict[str, Any]:
        """Phase 6: Generate a corrected plan based on findings."""
        corrections: list[str] = []

        # Add specific corrections based on failure categories
        categories_seen = set()
        for f in failures:
            cat = f["category"]
            if cat not in categories_seen:
                categories_seen.add(cat)
                if cat == "security":
                    corrections.append(
                        "Add security audit gate before production deployment"
                    )
                elif cat == "operational":
                    corrections.append(
                        "Add monitoring and alerting for all critical dependencies"
                    )
                elif cat == "design":
                    corrections.append(
                        "Conduct architecture review with external stakeholders"
                    )
                elif cat.startswith("llm"):
                    corrections.append(
                        "Add output validation and hallucination detection layer"
                    )

        corrected = (
            f"## Corrected Plan\n\n"
            f"Original: {plan[:300]}...\n\n"
            f"### Corrections Applied\n"
        )
        for i, c in enumerate(corrections, 1):
            corrected += f"{i}. {c}\n"

        corrected += (
            f"\n### Key Changes\n"
            f"- Added pre-launch checklist from synthesis\n"
            f"- Included early warning monitoring\n"
            f"- Addressed top {len(corrections)} risk categories"
        )

        return {
            "plan": corrected,
            "corrections_count": len(corrections),
            "corrections": corrections,
        }
