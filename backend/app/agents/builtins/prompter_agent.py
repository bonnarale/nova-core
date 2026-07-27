"""PrompterAgent — 3-level Prompt-Plus improvement pipeline.

Ported from amBotHs OS prompter skill. Kaizen-inspired incremental
precision through 3 progressive instances:
  Level 1: Kaizen Atomic Improvement (expand, fix, structure)
  Level 2: + Cognitive Architecture Audit (thinking, tools, guardrails)
  Level 3: + Final Output Engineering (Constitutional AI, ToT, security)
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="prompter",
    name="Prompter Agent",
    role="prompt-engineering",
    description=(
        "Professional prompt improvement using a 3-instance Pipeline "
        "Prompt-Plus. Kaizen-inspired: atomic improvement, cognitive "
        "architecture audit, and final output engineering."
    ),
    system_prompt=(
        "You are a prompt architect. Your job is to improve prompts through "
        "a 3-instance pipeline called Prompt-Plus, inspired by Kaizen "
        "(continuous improvement, incremental precision, iterative perfection).\n\n"
        "## Pipeline Levels\n"
        "- **Level 1 (Simple):** Kaizen Atomic Improvement — expand intent, fix "
        "ambiguities, establish base structure (role, objectives, steps, output format)\n"
        "- **Level 2 (Medium):** + Cognitive Architecture Audit — analyze thinking "
        "architecture, tool integration, guardrails, structural know-how\n"
        "- **Level 3 (Complex):** + Final Output Engineering — apply advanced "
        "techniques (Constitutional AI, Tree of Thoughts), security guardrails, "
        "production-ready formatting\n\n"
        "## Rules\n"
        "- Level 1 is mandatory for every prompt\n"
        "- Level 2 is mandatory if the prompt has role, context, steps, or multiple objectives\n"
        "- Level 3 is for multi-agent prompts, tools, or complex formats\n"
        "- Every output must be immediately usable — no placeholders\n"
        "- Always preserve the user's original intent"
    ),
    allowed_tools=[],
    memory_scope="session",
    permissions={"can_read_files": False, "can_write_files": False},
    supported_models=["qwen2.5-coder:7b"],
)

# ── Level analysis patterns ──────────────────────────────────────────

LEVEL_1_PATTERNS = [
    ("role", r"(you are|act as|persona|role)"),
    ("objectives", r"(goal|objective|purpose|aim)"),
    ("steps", r"(step|phase|then|first|finally)"),
    ("output_format", r"(format|output|structure|return)"),
]

LEVEL_2_PATTERNS = [
    ("thinking", r"(think|reason|analyze|consider|evaluate)"),
    ("tools", r"(use the .+ tool|invoke|call|execute)"),
    ("guardrails", r"(never|always|must|forbidden|restricted)"),
    ("context", r"(context|background|given|assuming)"),
]


def _analyze_prompt_level(prompt: str) -> dict[str, Any]:
    """Determine which levels are needed based on prompt content."""
    has_level_1 = {}
    has_level_2 = {}

    for name, pattern in LEVEL_1_PATTERNS:
        has_level_1[name] = bool(re.search(pattern, prompt, re.IGNORECASE))

    for name, pattern in LEVEL_2_PATTERNS:
        has_level_2[name] = bool(re.search(pattern, prompt, re.IGNORECASE))

    needs_level_2 = any(has_level_2.values())
    needs_level_3 = len([v for v in has_level_2.values() if v]) >= 2

    return {
        "level_1_signals": has_level_1,
        "level_2_signals": has_level_2,
        "needs_level_2": needs_level_2,
        "needs_level_3": needs_level_3,
        "recommended_level": 3 if needs_level_3 else (2 if needs_level_2 else 1),
    }


class PrompterAgent(BaseAgent):
    """Prompt improvement agent using the 3-instance Prompt-Plus pipeline."""

    def __init__(self) -> None:
        super().__init__(agent_id="prompter")

    @property
    def definition(self) -> AgentDefinition:
        return _DEFINITION

    async def execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute prompt improvement.

        Expected context:
            - prompt: str — the prompt to improve (or use task directly)
            - level: int — 1, 2, or 3 (default: auto-detect)
            - domain: str — optional domain context (e.g., "coding", "analysis")
        """
        prompt = context.get("prompt", task)
        level = context.get("level", 0)  # 0 = auto-detect
        domain = context.get("domain", "general")

        # Auto-detect level if not specified
        analysis = _analyze_prompt_level(prompt)
        if level == 0:
            level = analysis["recommended_level"]

        # Run the pipeline
        result_1 = await self._instance_1_kaizen(prompt, domain)
        result_2 = None
        result_3 = None

        if level >= 2:
            result_2 = await self._instance_2_cognitive_audit(prompt, result_1, domain)

        if level >= 3:
            result_3 = await self._instance_3_output_engineering(
                prompt, result_1, result_2, domain
            )

        # Select final output
        final = result_3 or result_2 or result_1

        return {
            "agent": self.agent_id,
            "status": "completed",
            "level_applied": level,
            "analysis": analysis,
            "instance_1": result_1,
            "instance_2": result_2,
            "instance_3": result_3,
            "improved_prompt": final["prompt"],
            "changes_made": final.get("changes", []),
        }

    async def _instance_1_kaizen(
        self, prompt: str, domain: str
    ) -> dict[str, Any]:
        """Instance 1: Kaizen Atomic Improvement."""
        changes: list[str] = []
        improved = prompt

        # Expand intent if unclear
        if not re.search(r"(you are|act as|role)", prompt, re.IGNORECASE):
            improved = f"You are an expert assistant. {improved}"
            changes.append("Added role/identity statement")

        # Add output format if missing
        if not re.search(r"(format|output|return|respond)", prompt, re.IGNORECASE):
            improved += "\n\nRespond in clear, structured format with headers."
            changes.append("Added output format specification")

        # Fix ambiguities — add specificity markers
        if len(prompt.split()) < 10:
            improved += "\n\nBe specific and provide concrete examples."
            changes.append("Added specificity guidance")

        # Add objectives if missing
        if not re.search(r"(goal|objective|purpose|aim|task)", prompt, re.IGNORECASE):
            improved += "\n\nGoal: Complete the requested task accurately and thoroughly."
            changes.append("Added explicit goal statement")

        return {
            "prompt": improved,
            "changes": changes,
            "instance": 1,
            "name": "Kaizen Atomic Improvement",
        }

    async def _instance_2_cognitive_audit(
        self, original: str, instance_1: dict, domain: str
    ) -> dict[str, Any]:
        """Instance 2: Cognitive Architecture Audit."""
        prompt = instance_1["prompt"]
        changes: list[str] = []

        # Check for thinking architecture
        if not re.search(r"(think|step.by.step|analyze|reason)", prompt, re.IGNORECASE):
            prompt = "Think step-by-step before responding.\n\n" + prompt
            changes.append("Added chain-of-thought instruction")

        # Check for tool awareness
        if domain in ("coding", "analysis", "research"):
            if not re.search(r"(tool|use .+ to|invoke|execute)", prompt, re.IGNORECASE):
                prompt += "\n\nUse available tools when needed for accuracy."
                changes.append("Added tool usage guidance")

        # Add guardrails if missing
        if not re.search(r"(never|always|must|don't|do not)", prompt, re.IGNORECASE):
            prompt += "\n\nAlways verify facts before stating them. Never guess."
            changes.append("Added safety guardrails")

        # Add context placeholder for dynamic injection
        if not re.search(r"(context|given|assuming|background)", prompt, re.IGNORECASE):
            prompt += "\n\nContext: {user_context}"
            changes.append("Added context injection point")

        return {
            "prompt": prompt,
            "changes": changes,
            "instance": 2,
            "name": "Cognitive Architecture Audit",
        }

    async def _instance_3_output_engineering(
        self,
        original: str,
        instance_1: dict,
        instance_2: dict | None,
        domain: str,
    ) -> dict[str, Any]:
        """Instance 3: Final Output Engineering."""
        prompt = (instance_2 or instance_1)["prompt"]
        changes: list[str] = []

        # Add Constitutional AI principles
        if not re.search(r"(principle|value|ethical|respect)", prompt, re.IGNORECASE):
            prompt += (
                "\n\nPrinciples:\n"
                "- Be helpful and harmless\n"
                "- Respect user autonomy\n"
                "- Be honest about uncertainty"
            )
            changes.append("Added Constitutional AI principles")

        # Add error handling
        if not re.search(r"(error|fail|fallback|uncertain)", prompt, re.IGNORECASE):
            prompt += (
                "\n\nIf unsure, say 'I'm not certain about X, but here's what "
                "I know...' rather than guessing."
            )
            changes.append("Added uncertainty handling")

        # Add quality checklist
        prompt += (
            "\n\nQuality Checklist:\n"
            "- [ ] Response directly addresses the prompt\n"
            "- [ ] No hallucinated facts\n"
            "- [ ] Structured and readable\n"
            "- [ ] Appropriate length for the task"
        )
        changes.append("Added quality checklist")

        return {
            "prompt": prompt,
            "changes": changes,
            "instance": 3,
            "name": "Final Output Engineering",
        }
