"""Governor — the strategic brain of NOVA Command Center.

Responsible for:
- Objective analysis with deep categorization
- Risk and opportunity detection
- Dependency analysis
- Complexity estimation
- Execution strategy recommendations
- Tool orchestration decisions
- Strategic recommendations
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from .schemas import GovernorDecision, _uuid, _utcnow

if TYPE_CHECKING:
    from .approvals import ApprovalsManager
    from .objectives import ObjectivesManager
    from .projects import ProjectsManager


# ── Keyword banks ──

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "business": ["business", "revenue", "customer", "market", "sales", "company",
                  "startup", "product", "launch", "profit", "growth", "strategy",
                  "investment", "partnership", "brand", "marketing"],
    "technology": ["code", "software", "api", "database", "system", "tech",
                   "application", "platform", "architecture", "infrastructure",
                   "deploy", "cloud", "microservice", "frontend", "backend"],
    "education": ["learn", "study", "course", "education", "training", "teach",
                  "tutorial", "skill", "certificate", "degree"],
    "research": ["research", "experiment", "analyze", "investigate", "explore",
                 "discover", "study", "survey", "literature"],
    "creative": ["creative", "design", "art", "write", "content", "video",
                "music", "brand", "ui", "ux", "visual"],
    "financial": ["budget", "invest", "financial", "cost", "profit", "portfolio",
                 "trading", "crypto", "fund", "asset"],
    "community": ["community", "social", "network", "group", "forum", "meetup",
                 "event", "membership"],
    "personal": ["personal", "life", "health", "fitness", "habit", "routine",
                "goal", "change", "improve", "run", "exercise", "wellness"],
}

_COMPLEXITY_KEYWORDS: dict[str, list[str]] = {
    "very_high": ["enterprise", "scale", "distributed", "machine learning", "ai",
                  "blockchain", "migration", "infrastructure", "multi-year",
                  "company", "ecosystem", "platform"],
    "high": ["integration", "architecture", "security", "performance", "real-time",
             "concurrent", "microservice", "pipeline", "automation"],
    "medium": ["api", "database", "frontend", "backend", "testing", "deploy",
               "workflow", "automation", "configuration"],
    "low": ["fix", "update", "rename", "configure", "document", "typo",
            "simple", "basic", "quick"],
}

_EXECUTION_STRATEGIES: dict[str, dict[str, Any]] = {
    "quick_win": {
        "description": "Execute immediately with minimal planning",
        "phases": ["Execute", "Validate"],
        "适合_complexity": ["low"],
    },
    "agile_iterative": {
        "description": "Agile approach with iterative delivery",
        "phases": ["Plan", "Sprint", "Review", "Repeat"],
        "适合_complexity": ["medium"],
    },
    "incremental": {
        "description": "Incremental development with frequent reviews",
        "phases": ["Design", "Build", "Integrate", "Review", "Deploy"],
        "适合_complexity": ["high"],
    },
    "phased": {
        "description": "Phased approach with milestone gates",
        "phases": ["Discovery", "Foundation", "Core", "Advanced", "Polish", "Launch"],
        "适合_complexity": ["very_high"],
    },
}


class Governor:
    """The strategic decision-maker for NOVA Command Center."""

    def __init__(
        self,
        objectives_manager: ObjectivesManager,
        projects_manager: ProjectsManager,
        approvals_manager: ApprovalsManager,
    ) -> None:
        self.objectives = objectives_manager
        self.projects = projects_manager
        self.approvals = approvals_manager
        self._decision_history: list[GovernorDecision] = []
        self._analysis_cache: dict[str, dict] = {}

    # ── Core Analysis ──

    async def analyze_objective(self, objective_text: str) -> dict[str, Any]:
        text_lower = objective_text.lower()
        category = self._categorize_objective(text_lower)
        complexity = self._assess_complexity(text_lower)
        duration = self._estimate_duration(complexity)
        risks = self._assess_risks(text_lower, category, complexity)
        opportunities = self._identify_opportunities(text_lower, category, complexity)
        dependencies = self._detect_dependencies(text_lower, category)
        milestones = self._generate_milestones(category, complexity)
        goals = self._generate_goals(category, complexity)
        tasks = self._generate_tasks(category, complexity)
        workflows = self._determine_workflows(category, complexity)
        tools = self._determine_tools(category, complexity)
        agents = self._determine_agents(category, complexity)
        strategy = self._recommend_strategy(complexity, category)
        execution_strategies = self._generate_execution_strategies(complexity, category)
        requires_approval = self._requires_human_approval(text_lower, category, complexity)
        requires_open_code = self._requires_open_code(text_lower, category)
        resource_needs = self._assess_resource_needs(complexity, category)

        analysis = {
            "text": objective_text,
            "category": category,
            "complexity": complexity,
            "estimated_duration": duration,
            "key_risks": risks,
            "opportunities": opportunities,
            "dependencies": dependencies,
            "recommended_approach": strategy,
            "execution_strategies": execution_strategies,
            "required_resources": resource_needs,
            "milestones": milestones,
            "goals": goals,
            "tasks": tasks,
            "workflows_needed": workflows,
            "tools_needed": tools,
            "agents_needed": agents,
            "requires_human_approval": requires_approval,
            "requires_open_code": requires_open_code,
            "timestamp": _utcnow(),
        }
        self._analysis_cache[objective_text] = analysis
        return analysis

    async def create_plan(self, analysis: dict) -> dict:
        milestones = analysis.get("milestones", [])
        tasks = analysis.get("tasks", [])
        goals = analysis.get("goals", [])
        workflows = analysis.get("workflows_needed", [])
        tools = analysis.get("tools_needed", [])
        agents = analysis.get("agents_needed", [])
        risks = analysis.get("key_risks", [])
        strategy = analysis.get("recommended_approach", "")

        phases = []
        if tasks:
            chunk = max(1, len(tasks) // 3)
            phase_names = ["Foundation", "Execution", "Completion"]
            for i, name in enumerate(phase_names):
                start = i * chunk
                end = start + chunk if i < 2 else len(tasks)
                phases.append({"name": name, "tasks": tasks[start:end]})

        dependencies_graph = self._build_dependency_graph(tasks, milestones)

        return {
            "id": _uuid(),
            "category": analysis.get("category", "general"),
            "complexity": analysis.get("complexity", "medium"),
            "estimated_duration": analysis.get("estimated_duration", "1-3 months"),
            "strategy": strategy,
            "phases": phases,
            "milestones": milestones,
            "goals": goals,
            "workflows_needed": workflows,
            "tools_needed": tools,
            "agents_needed": agents,
            "risks": risks,
            "dependencies_graph": dependencies_graph,
            "requires_human_approval": analysis.get("requires_human_approval", False),
            "requires_open_code": analysis.get("requires_open_code", False),
            "created_at": _utcnow(),
        }

    async def make_decision(
        self, decision_type: str, context: dict
    ) -> GovernorDecision:
        description = context.get("description", "")
        risk = context.get("risk", "low")
        requires_approval = risk in ("high", "critical")
        confidence = 0.7 if risk == "low" else 0.5 if risk == "medium" else 0.3
        action = "auto_execute" if not requires_approval else "pending_approval"

        reasoning_parts = [f"Decision type: {decision_type}"]
        if "analysis" in context:
            a = context["analysis"]
            reasoning_parts.append(f"Category: {a.get('category', 'unknown')}")
            reasoning_parts.append(f"Complexity: {a.get('complexity', 'unknown')}")
        reasoning_parts.append(f"Risk: {risk}")

        decision = GovernorDecision(
            decision_type=decision_type,
            description=description,
            reasoning=". ".join(reasoning_parts),
            confidence=confidence,
            action_taken=action,
            requires_approval=requires_approval,
        )
        self._decision_history.append(decision)

        if requires_approval:
            self.approvals.request(
                action_type=f"governor_{decision_type}",
                description=description,
                risk_level=risk,
                requester="governor",
            )
        return decision

    async def prioritize(self, objectives: list[dict]) -> list[dict]:
        def _score(obj: dict) -> float:
            priority = obj.get("priority", 3)
            urgency = obj.get("urgency", 3)
            impact = obj.get("impact", 3)
            complexity = obj.get("complexity", "medium")
            complexity_penalty = {"low": 0.0, "medium": 0.1, "high": 0.2, "very_high": 0.3}
            return (priority * 2 + urgency * 1.5 + impact * 2) - complexity_penalty.get(complexity, 0.1)
        return sorted(objectives, key=_score, reverse=True)

    async def recommend_next_action(self, context: dict) -> dict:
        active_objectives = context.get("active_objectives", 0)
        pending_approvals = context.get("pending_approvals", 0)
        backlog_count = context.get("backlog_count", 0)

        if pending_approvals > 0:
            return {
                "action": "review_approvals",
                "reason": f"{pending_approvals} approval(s) pending human review",
                "priority": "high",
                "suggestion": "Review and approve pending actions before proceeding",
            }
        if active_objectives == 0:
            if backlog_count > 0:
                return {
                    "action": "promote_from_backlog",
                    "reason": f"No active objectives but {backlog_count} items in backlog",
                    "priority": "high",
                    "suggestion": "Promote the highest priority backlog item to active",
                }
            return {
                "action": "create_objective",
                "reason": "No active objectives or backlog items",
                "priority": "high",
                "suggestion": "Define a new strategic objective to begin",
            }
        if backlog_count > 3:
            return {
                "action": "prioritize_backlog",
                "reason": f"{backlog_count} items in backlog need prioritization",
                "priority": "medium",
                "suggestion": "Review and prioritize backlog items",
            }
        return {
            "action": "continue_execution",
            "reason": "System operating normally",
            "priority": "low",
            "suggestion": "Continue executing current objectives",
        }

    def get_decision_history(self, limit: int = 50) -> list[GovernorDecision]:
        return self._decision_history[-limit:]

    # ── Categorization ──

    def _categorize_objective(self, text_lower: str) -> str:
        scores: dict[str, int] = {}
        for cat, keywords in _CATEGORY_KEYWORDS.items():
            scores[cat] = sum(1 for kw in keywords if kw in text_lower)
        if not scores or max(scores.values()) == 0:
            return "general"
        return max(scores, key=scores.get)

    def _assess_complexity(self, text_lower: str) -> str:
        word_count = len(text_lower.split())
        scores = {"very_high": 0, "high": 0, "medium": 0, "low": 0}
        for level, keywords in _COMPLEXITY_KEYWORDS.items():
            scores[level] = sum(1 for kw in keywords if kw in text_lower)
        if scores["very_high"] >= 2 or word_count > 40:
            return "very_high"
        if scores["high"] >= 2 or (scores["high"] >= 1 and word_count > 25):
            return "high"
        if scores["medium"] >= 2 or word_count > 15:
            return "medium"
        return "low"

    # ── Duration Estimation ──

    def _estimate_duration(self, complexity: str) -> str:
        return {
            "low": "1-2 weeks",
            "medium": "1-3 months",
            "high": "3-6 months",
            "very_high": "6-18 months",
        }.get(complexity, "1-3 months")

    # ── Risk Assessment ──

    def _assess_risks(self, text_lower: str, category: str, complexity: str) -> list[dict]:
        risks: list[dict] = []
        risks.append({"risk": "Scope creep", "severity": "medium",
                       "mitigation": "Define clear boundaries and acceptance criteria"})

        if complexity in ("high", "very_high"):
            risks.append({"risk": "Technical debt accumulation", "severity": "high",
                           "mitigation": "Regular refactoring and code reviews"})
            risks.append({"risk": "Integration failures", "severity": "high",
                           "mitigation": "Incremental integration with CI/CD"})
            risks.append({"risk": "Resource constraints", "severity": "medium",
                           "mitigation": "Resource planning and capacity management"})

        if category == "business":
            risks.append({"risk": "Market timing", "severity": "high",
                           "mitigation": "Continuous market validation"})
            risks.append({"risk": "Competitive pressure", "severity": "medium",
                           "mitigation": "Differentiation strategy"})

        if category == "technology":
            risks.append({"risk": "Technology obsolescence", "severity": "medium",
                           "mitigation": "Adopt proven, stable technologies"})
            risks.append({"risk": "Security vulnerabilities", "severity": "high",
                           "mitigation": "Security audits and penetration testing"})

        if category == "financial":
            risks.append({"risk": "Cash flow issues", "severity": "critical",
                           "mitigation": "Conservative financial planning"})
            risks.append({"risk": "Regulatory changes", "severity": "high",
                           "mitigation": "Compliance monitoring"})

        risks.append({"risk": "Timeline delays", "severity": "medium",
                       "mitigation": "Buffer time in milestones and regular check-ins"})
        return risks

    # ── Opportunity Detection ──

    def _identify_opportunities(self, text_lower: str, category: str, complexity: str) -> list[dict]:
        opportunities: list[dict] = []
        opportunities.append({"opportunity": "Automation potential", "impact": "high",
                              "description": "Identify repetitive tasks for automation"})

        if category == "business":
            opportunities.extend([
                {"opportunity": "Market expansion", "impact": "high",
                 "description": "Potential to reach new markets or segments"},
                {"opportunity": "Strategic partnerships", "impact": "medium",
                 "description": "Leverage partnerships for growth"},
            ])
        elif category == "technology":
            opportunities.extend([
                {"opportunity": "Technical innovation", "impact": "high",
                 "description": "Implement cutting-edge solutions"},
                {"opportunity": "Open source contribution", "impact": "medium",
                 "description": "Build reputation through open source"},
            ])
        elif category == "education":
            opportunities.extend([
                {"opportunity": "Knowledge sharing", "impact": "high",
                 "description": "Create educational content for others"},
                {"opportunity": "Certification pathway", "impact": "medium",
                 "description": "Pursue recognized certifications"},
            ])
        elif category == "research":
            opportunities.extend([
                {"opportunity": "Novel discovery", "impact": "high",
                 "description": "Potential for groundbreaking findings"},
                {"opportunity": "Academic publication", "impact": "medium",
                 "description": "Publish findings for peer review"},
            ])

        opportunities.append({"opportunity": "Knowledge accumulation", "impact": "medium",
                              "description": "Build reusable knowledge base"})
        return opportunities

    # ── Dependency Detection ──

    def _detect_dependencies(self, text_lower: str, category: str) -> list[dict]:
        deps: list[dict] = []
        if category == "technology":
            deps.extend([
                {"type": "infrastructure", "description": "Development environment setup", "critical": True},
                {"type": "tooling", "description": "Required development tools", "critical": False},
            ])
        if category == "business":
            deps.extend([
                {"type": "funding", "description": "Initial capital or investment", "critical": True},
                {"type": "team", "description": "Core team assembly", "critical": True},
            ])
        if category == "education":
            deps.append({"type": "prerequisites", "description": "Foundational knowledge", "critical": True})
        deps.append({"type": "resources", "description": "Compute and storage resources", "critical": False})
        return deps

    # ── Milestones ──

    def _generate_milestones(self, category: str, complexity: str) -> list[dict]:
        base = [
            {"title": "Discovery & Research", "phase": 1, "status": "pending",
             "description": "Investigate requirements and approach"},
            {"title": "Foundation & Setup", "phase": 2, "status": "pending",
             "description": "Establish base infrastructure and project structure"},
        ]
        if complexity in ("medium", "high", "very_high"):
            base.append({"title": "Core Implementation", "phase": 3, "status": "pending",
                          "description": "Build the primary components"})
        if complexity in ("high", "very_high"):
            base.append({"title": "Advanced Features", "phase": 4, "status": "pending",
                          "description": "Implement advanced capabilities"})
            base.append({"title": "Integration & Testing", "phase": 5, "status": "pending",
                          "description": "Integrate components and validate"})
        base.append({"title": "Review & Validation", "phase": len(base) + 1, "status": "pending",
                      "description": "Quality review and validation"})
        base.append({"title": "Deployment & Launch", "phase": len(base) + 1, "status": "pending",
                      "description": "Deploy and launch to production"})
        return base

    # ── Goals ──

    def _generate_goals(self, category: str, complexity: str) -> list[dict]:
        goals = [
            {"title": "Complete requirements analysis", "target": 1.0, "current": 0.0},
            {"title": "Implement core components", "target": 1.0, "current": 0.0},
        ]
        if complexity in ("medium", "high", "very_high"):
            goals.append({"title": "Achieve quality benchmarks", "target": 1.0, "current": 0.0})
        if complexity in ("high", "very_high"):
            goals.extend([
                {"title": "Pass security review", "target": 1.0, "current": 0.0},
                {"title": "Performance optimization", "target": 1.0, "current": 0.0},
            ])
        goals.append({"title": "Meet timeline targets", "target": 1.0, "current": 0.0})
        return goals

    # ── Tasks ──

    def _generate_tasks(self, category: str, complexity: str) -> list[dict]:
        tasks = [
            {"title": "Define requirements and scope", "status": "pending", "priority": 1},
            {"title": "Set up project structure", "status": "pending", "priority": 2},
        ]
        if complexity in ("medium", "high", "very_high"):
            tasks.append({"title": "Architecture design review", "status": "pending", "priority": 2})
        tasks.append({"title": f"Implement core {category} components", "status": "pending", "priority": 1})
        if complexity in ("high", "very_high"):
            tasks.append({"title": "Security review and hardening", "status": "pending", "priority": 2})
            tasks.append({"title": "Performance optimization", "status": "pending", "priority": 3})
        tasks.append({"title": "Write tests and validation", "status": "pending", "priority": 2})
        if complexity in ("high", "very_high"):
            tasks.append({"title": "Integration testing", "status": "pending", "priority": 2})
        tasks.append({"title": "Documentation and review", "status": "pending", "priority": 3})
        tasks.append({"title": "Deployment preparation", "status": "pending", "priority": 2})
        return tasks

    # ── Workflows ──

    def _determine_workflows(self, category: str, complexity: str) -> list[dict]:
        workflows = [
            {"name": "standard_execution", "description": "Standard execution workflow"},
            {"name": "review_approval", "description": "Review and approval process"},
        ]
        if category == "technology":
            workflows.append({"name": "ci_cd_pipeline", "description": "Continuous integration and deployment"})
        if complexity in ("high", "very_high"):
            workflows.append({"name": "quality_gate", "description": "Quality gate with review cycles"})
            workflows.append({"name": "risk_assessment", "description": "Risk assessment workflow"})
        if category == "business":
            workflows.append({"name": "stakeholder_review", "description": "Stakeholder review and sign-off"})
        return workflows

    # ── Tools ──

    def _determine_tools(self, category: str, complexity: str) -> list[str]:
        tools = ["version_control", "documentation"]
        if category == "technology":
            tools.extend(["compiler", "debugger", "profiler", "ci_cd"])
        if category == "creative":
            tools.extend(["design_software", "asset_pipeline"])
        if category == "research":
            tools.extend(["data_analyzer", "visualization", "reference_manager"])
        if category == "business":
            tools.extend(["project_management", "analytics", "reporting"])
        if complexity in ("high", "very_high"):
            tools.extend(["monitoring", "logging", "security_scanner"])
        return tools

    # ── Agents ──

    def _determine_agents(self, category: str, complexity: str) -> list[str]:
        agents = ["coordinator", "executor"]
        if complexity in ("medium", "high", "very_high"):
            agents.append("reviewer")
        if complexity in ("high", "very_high"):
            agents.extend(["tester", "security_analyst"])
        if category == "technology":
            agents.append("developer")
        if category == "business":
            agents.append("analyst")
        if category == "research":
            agents.append("researcher")
        return agents

    # ── Strategy Recommendation ──

    def _recommend_strategy(self, complexity: str, category: str) -> str:
        strategies = {
            "low": "Quick execution with standard workflow",
            "medium": "Agile approach with iterative delivery",
            "high": "Incremental development with frequent reviews and quality gates",
            "very_high": "Phased approach with milestone gates and stakeholder checkpoints",
        }
        return strategies.get(complexity, "Agile approach with iterative delivery")

    def _generate_execution_strategies(self, complexity: str, category: str) -> list[dict]:
        strategies = []
        for name, config in _EXECUTION_STRATEGIES.items():
            if complexity in config.get("适合_complexity", []):
                strategies.append({
                    "name": name,
                    "description": config["description"],
                    "phases": config["phases"],
                })
        if not strategies:
            strategies.append({
                "name": "agile_iterative",
                "description": "Agile approach with iterative delivery",
                "phases": ["Plan", "Sprint", "Review", "Repeat"],
            })
        return strategies

    # ── Approval Requirements ──

    def _requires_human_approval(self, text_lower: str, category: str, complexity: str) -> bool:
        high_risk_keywords = ["deploy", "production", "security", "delete", "migrate",
                              "financial", "legal", "compliance"]
        if any(kw in text_lower for kw in high_risk_keywords):
            return True
        if complexity in ("high", "very_high"):
            return True
        return False

    def _requires_open_code(self, text_lower: str, category: str) -> bool:
        code_keywords = ["code", "software", "application", "api", "database",
                         "build", "implement", "develop", "program"]
        if any(kw in text_lower for kw in code_keywords):
            return True
        if category == "technology":
            return True
        return False

    # ── Resources ──

    def _assess_resource_needs(self, complexity: str, category: str) -> list[dict]:
        resources = [{"type": "compute", "level": "standard", "critical": True}]
        if complexity in ("high", "very_high"):
            resources.append({"type": "storage", "level": "extended", "critical": False})
            resources.append({"type": "network", "level": "standard", "critical": False})
        if category == "technology":
            resources.append({"type": "development_tools", "level": "standard", "critical": True})
        if category == "research":
            resources.append({"type": "data_sources", "level": "extended", "critical": True})
        return resources

    # ── Dependency Graph ──

    def _build_dependency_graph(self, tasks: list[dict], milestones: list[dict]) -> dict:
        graph: dict[str, list[str]] = {}
        for i, task in enumerate(tasks):
            task_id = task.get("title", f"task_{i}")
            deps = []
            if i > 0:
                deps.append(tasks[i - 1].get("title", f"task_{i - 1}"))
            graph[task_id] = deps
        return graph

    # ── Tool Orchestration ──

    def decide_tool_orchestration(self, task_description: str, category: str, complexity: str) -> dict:
        text_lower = task_description.lower()
        decisions: dict[str, Any] = {
            "use_open_code": False,
            "use_workflows": False,
            "use_agents": False,
            "use_research": False,
            "use_apis": False,
            "human_approval_required": False,
            "reasoning": [],
        }

        if any(kw in text_lower for kw in ["code", "implement", "build", "develop", "program"]):
            decisions["use_open_code"] = True
            decisions["reasoning"].append("Code-related task detected")

        if complexity in ("high", "very_high"):
            decisions["use_workflows"] = True
            decisions["reasoning"].append("Complex task requires workflow orchestration")

        if complexity in ("medium", "high", "very_high"):
            decisions["use_agents"] = True
            decisions["reasoning"].append("Task benefits from multi-agent coordination")

        if any(kw in text_lower for kw in ["research", "investigate", "analyze", "compare"]):
            decisions["use_research"] = True
            decisions["reasoning"].append("Research capability recommended")

        if any(kw in text_lower for kw in ["api", "integrate", "connect", "fetch"]):
            decisions["use_apis"] = True
            decisions["reasoning"].append("API integration needed")

        if any(kw in text_lower for kw in ["deploy", "production", "security", "delete"]):
            decisions["human_approval_required"] = True
            decisions["reasoning"].append("High-risk operation requires human approval")

        return decisions

    def to_dict(self) -> dict:
        return {
            "role": "governor",
            "status": "active",
            "total_analyses": len(self._analysis_cache),
            "total_decisions": len(self._decision_history),
        }
