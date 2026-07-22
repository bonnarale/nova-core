"""PlanDecompositionStrategy — converts an objective into a Plan with Steps.

Strategy Pattern so the decomposition can be rule-based, LLM-driven,
or hybrid without changing the Planner orchestrator.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.planner.plan import Plan, PlanStatus, RetryPolicy, Step, StepStatus, ToolCall

logger = logging.getLogger(__name__)


class PlanDecompositionStrategy(ABC):
    """Abstract strategy for decomposing an objective into a Plan."""

    @abstractmethod
    async def decompose(self, objective: str, user_id: str | None = None) -> Plan:
        """Return a Plan with ordered Steps for *objective*."""
        ...


class RuleBasedDecompositionStrategy(PlanDecompositionStrategy):
    """Rule-based decomposition using heuristics and keyword matching.

    Useful for known patterns; can be replaced by an LLM-based strategy
    for complex or novel objectives.
    """

    _DOMAIN_PATTERNS: dict[str, list[dict[str, Any]]] = {
        "landing_page": [
            {"title": "Define requirements", "description": "Gather requirements for the landing page", "agent": "planner"},
            {"title": "Design layout mockup", "description": "Create a wireframe or mockup of the layout", "agent": "planner"},
            {"title": "Build HTML/CSS structure", "description": "Implement the landing page with HTML, CSS, and JS", "agent": "coder"},
            {"title": "Review and refine", "description": "Review the page for quality and consistency", "agent": "reviewer"},
            {"title": "Deploy landing page", "description": "Deploy the page to the hosting environment", "agent": "executor"},
        ],
        "backend": [
            {"title": "Define API specification", "description": "Define endpoints, data models, and routes", "agent": "planner"},
            {"title": "Set up project structure", "description": "Initialize the backend project with dependencies", "agent": "coder"},
            {"title": "Implement data models", "description": "Create database models and migrations", "agent": "coder"},
            {"title": "Implement API endpoints", "description": "Build the REST/GraphQL API endpoints", "agent": "coder"},
            {"title": "Write unit tests", "description": "Add test coverage for the backend", "agent": "reviewer"},
            {"title": "Review and deploy", "description": "Review the backend and deploy to staging", "agent": "executor"},
        ],
        "research": [
            {"title": "Define research questions", "description": "Formulate key questions to investigate", "agent": "planner"},
            {"title": "Gather information", "description": "Search for relevant data, articles, and sources", "agent": "researcher"},
            {"title": "Analyze findings", "description": "Synthesize and analyze gathered information", "agent": "researcher"},
            {"title": "Compile report", "description": "Create a structured report of findings", "agent": "coder"},
        ],
        "project": [
            {"title": "Define project scope", "description": "Clarify objectives, deliverables, and timeline", "agent": "planner"},
            {"title": "Create project plan", "description": "Break the project into milestones and tasks", "agent": "planner"},
            {"title": "Execute milestone 1", "description": "Complete the first set of deliverables", "agent": "executor"},
            {"title": "Review milestone 1", "description": "Evaluate progress and adjust plan", "agent": "reviewer"},
            {"title": "Execute remaining milestones", "description": "Complete remaining deliverables iteratively", "agent": "executor"},
            {"title": "Final review and report", "description": "Summarize outcomes and lessons learned", "agent": "reviewer"},
        ],
    }

    _FALLBACK_STEPS: list[dict[str, Any]] = [
        {"title": "Analyze objective", "description": "Understand the objective and identify key actions", "agent": "planner"},
        {"title": "Execute primary actions", "description": "Carry out the main work for this objective", "agent": "executor"},
        {"title": "Review results", "description": "Verify that the objective has been met", "agent": "reviewer"},
    ]

    async def decompose(self, objective: str, user_id: str | None = None) -> Plan:
        text = objective.lower()
        domain = self._detect_domain(text)
        templates = self._DOMAIN_PATTERNS.get(domain, self._FALLBACK_STEPS)

        steps: list[Step] = []
        for i, tpl in enumerate(templates):
            step = Step(
                title=tpl["title"],
                description=tpl["description"],
                assigned_agent=tpl.get("agent"),
                dependencies=[steps[j].id for j in range(i)],
                retry_policy=RetryPolicy(max_retries=1, delay_seconds=1.0),
                metadata={"source": "rule_based", "domain": domain},
            )
            steps.append(step)

        plan = Plan(
            objective=objective,
            status=PlanStatus.DRAFT,
            steps=steps,
            user_id=user_id,
            metadata={"strategy": "rule_based", "domain": domain},
        )

        logger.info(
            "Decomposed objective '%s' into domain='%s' with %d steps",
            objective[:60], domain, len(steps),
        )
        return plan

    def _detect_domain(self, text: str) -> str:
        if any(w in text for w in ("landing", "landing page", "pagina", "web", "sitio", "site")):
            return "landing_page"
        if any(w in text for w in ("backend", "api", "servidor", "server", "database", "base de datos")):
            return "backend"
        if any(w in text for w in ("research", "investig", "investigación", "investigate", "analyze", "analizar")):
            return "research"
        if any(w in text for w in ("proyecto", "project", "organiz", "organizar", "manage", "gestion")):
            return "project"
        return "unknown"
