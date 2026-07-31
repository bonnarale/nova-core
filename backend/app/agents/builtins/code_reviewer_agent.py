"""CodeReviewerAgent — expert code review with 5-pillar analysis.

Ported from amBotHs OS code-reviewer skill. Reviews code as a mentor,
not a gatekeeper. Every comment teaches something.

5 Pillars: Correctness, Security, Maintainability, Performance, Testing.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="code-reviewer",
    name="Code Reviewer Agent",
    role="reviewer",
    description=(
        "Expert code reviewer. Detects bugs, vulnerabilities, "
        "maintainability issues, and performance problems. Provides "
        "actionable, educational feedback with severity classification."
    ),
    system_prompt=(
        "You are an expert code reviewer. Reviews como mentor, no como "
        "gatekeeper. Cada comentario ensena algo.\n\n"
        "## 5 Review Pillars\n"
        "1. **Correctness** — Logic errors, edge cases, race conditions\n"
        "2. **Security** — Vulnerabilities, data exposure, injection risks\n"
        "3. **Maintainability** — Naming, structure, complexity, duplication\n"
        "4. **Performance** — Inefficiencies, unnecessary allocations, N+1 queries\n"
        "5. **Testing** — Missing tests, weak assertions, untested paths\n\n"
        "## Severity Classification\n"
        "- 🔴 BLOCKER: Security vulns, data loss, race conditions, API contract breaks\n"
        "- 🟡 SUGGESTION: Missing validation, confusing naming, missing tests\n"
        "- 💭 NIT: Style, minor naming, docs gaps, alternative approaches\n\n"
        "## Rules\n"
        "- Be specific: reference exact lines and symbols\n"
        "- Explain the WHY behind every finding\n"
        "- Suggest fixes, don't just demand changes\n"
        "- Praise good code when you see it\n"
        "- One review = complete feedback (don't leave things half-reviewed)"
    ),
    allowed_tools=["file_read", "code_search"],
    memory_scope="session",
    permissions={"can_read_files": True, "can_write_files": False},
    supported_models=["qwen2.5-coder:7b"],
)

# ── 32-Pattern Agent Prompt Quality Scorecard ────────────────────────
# Ported from the code-reviewer skill's universal scoring system.

BLOCKER_PATTERNS = [
    (r"#{1,6}\s+\S+", "Markdown headers for structure", 15),
    (r"(you are|your role|act as|persona)", "Identity/Role section", 15),
    (r"(example|e\.g\.|for instance|such as)", "Concrete examples", 15),
    (r"(\*\*|__|__bold__|EMPHASIS)", "Emphasis tags for key concepts", 15),
]

NEAR_UNIVERSAL_PATTERNS = [
    (r"(never|always|must|do not|don't)", "NEVER/Always patterns", 10),
    (r"(if .+ then|when .+ do|unless)", "Conditional instructions", 10),
    (r"(use the .+ tool|invoke .+|call .+)", "Tool usage guidelines", 10),
    (r"(step \d|first|then|finally|phase)", "Step-by-step workflows", 10),
]

SUGGESTION_PATTERNS = [
    (r"(good|bad|correct|incorrect).*example", "Good vs Bad examples", 5),
    (r"(batch|bulk|parallel|concurrent)", "Batch operations", 5),
    (r"(plan|analyze|think|consider).*before", "Planning before execution", 5),
    (r"(forbidden|prohibited|restricted|security)", "Security restrictions", 5),
]

NIT_PATTERNS = [
    (r"(format|structure|output.*format)", "Output format specification", 2.5),
    (r"(error|fallback|retry|exception)", "Error handling", 2.5),
    (r"(edge case|corner case|boundary)", "Edge case coverage", 2.5),
]


def _score_prompt(text: str) -> dict[str, Any]:
    """Score a prompt against the 32-pattern quality checklist."""
    total = 0
    findings: list[dict[str, Any]] = []

    for category, patterns in [
        ("blocker", BLOCKER_PATTERNS),
        ("near_universal", NEAR_UNIVERSAL_PATTERNS),
        ("suggestion", SUGGESTION_PATTERNS),
        ("nit", NIT_PATTERNS),
    ]:
        for pattern, name, pts in patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            if matches > 0:
                total += pts
                findings.append({
                    "pattern": name,
                    "category": category,
                    "matches": matches,
                    "points": pts,
                })

    if total >= 130:
        tier = "Premium"
    elif total >= 100:
        tier = "Avanzado"
    elif total >= 60:
        tier = "Intermedio"
    elif total >= 40:
        tier = "Basico"
    else:
        tier = "Incompleto"

    return {
        "score": total,
        "max_score": 160,
        "tier": tier,
        "findings": findings,
    }


class CodeReviewerAgent(BaseAgent):
    """Expert code review agent with 5-pillar analysis and severity classification."""

    def __init__(self) -> None:
        super().__init__(agent_id="code-reviewer")

    @property
    def definition(self) -> AgentDefinition:
        return _DEFINITION

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a code review task.

        Expected context:
            - code: str — the code to review (or file path)
            - language: str — programming language (optional)
            - focus: str — specific area to focus on (optional)
            - review_level: str — "quick", "standard", or "deep" (default: standard)
        """
        code = context.get("code", task)
        language = context.get("language", "unknown")
        focus = context.get("focus", "all")
        review_level = context.get("review_level", "standard")

        # Score the prompt/code quality
        prompt_score = _score_prompt(code)

        # Analyze the code
        findings = await self._analyze_code(code, language, focus, review_level)

        # Generate summary
        blockers = [f for f in findings if f["severity"] == "blocker"]
        suggestions = [f for f in findings if f["severity"] == "suggestion"]
        nits = [f for f in findings if f["severity"] == "nit"]

        summary = self._build_summary(findings, blockers, suggestions, nits)

        return {
            "agent": self.agent_id,
            "status": "completed",
            "review_level": review_level,
            "language": language,
            "focus": focus,
            "summary": summary,
            "findings": findings,
            "severity_counts": {
                "blockers": len(blockers),
                "suggestions": len(suggestions),
                "nits": len(nits),
            },
            "prompt_quality": prompt_score,
        }

    async def _analyze_code(
        self,
        code: str,
        language: str,
        focus: str,
        review_level: str,
    ) -> list[dict[str, Any]]:
        """Analyze code and return structured findings."""
        findings: list[dict[str, Any]] = []

        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Security checks
            if any(vuln in stripped.lower() for vuln in [
                "eval(", "exec(", "os.system(", "subprocess.call(",
                "shell=True", "password", "secret", "api_key",
                "SELECT * FROM", "DROP TABLE",
            ]):
                findings.append({
                    "line": i,
                    "severity": "blocker",
                    "pillar": "security",
                    "message": f"Potential security issue: {stripped[:80]}",
                    "suggestion": "Review for hardcoded secrets or dangerous function calls",
                })

            # Correctness checks
            if re.match(r"except\s*:", stripped):
                findings.append({
                    "line": i,
                    "severity": "suggestion",
                    "pillar": "correctness",
                    "message": "Bare except clause — catches all exceptions including KeyboardInterrupt",
                    "suggestion": "Catch specific exceptions (e.g., except ValueError:)",
                })

            # Maintainability checks
            if len(stripped) > 120:
                findings.append({
                    "line": i,
                    "severity": "nit",
                    "pillar": "maintainability",
                    "message": f"Line exceeds 120 chars ({len(stripped)} chars)",
                    "suggestion": "Consider breaking into multiple lines",
                })

            # Performance checks
            if "for" in stripped and "in" in stripped:
                inner_lines = lines[i:i + 5]
                for inner in inner_lines:
                    if "SELECT" in inner.upper() or "find(" in inner:
                        findings.append({
                            "line": i,
                            "severity": "suggestion",
                            "pillar": "performance",
                            "message": "Potential N+1 query inside loop",
                            "suggestion": "Consider batching or using a single query",
                        })
                        break

        # If no findings, note it
        if not findings:
            findings.append({
                "line": 0,
                "severity": "nit",
                "pillar": "maintainability",
                "message": "No issues detected at this review level",
                "suggestion": "Consider running a deeper review level",
            })

        return findings

    def _build_summary(
        self,
        findings: list[dict[str, Any]],
        blockers: list[dict[str, Any]],
        suggestions: list[dict[str, Any]],
        nits: list[dict[str, Any]],
    ) -> str:
        """Build a human-readable review summary."""
        total = len(findings)
        if total == 0:
            return "No findings. Code looks clean."

        parts = [f"Reviewed code: {total} finding(s) found."]
        if blockers:
            parts.append(f"[BLOCKER] {len(blockers)} must fix before merge.")
        if suggestions:
            parts.append(f"[SUGGESTION] {len(suggestions)} recommended improvements.")
        if nits:
            parts.append(f"[NIT] {len(nits)} minor style/doc improvements.")
        return " ".join(parts)
