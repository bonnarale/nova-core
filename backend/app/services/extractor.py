"""Memory extractor service.

Analyzes conversation messages and detects persistable user information
(name, preferences, goals, facts) using rule-based patterns.

Can be replaced later with an LLM-based extractor without changing the
orchestration layer.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Pattern sets (expandable) ─────────────────────────────────────────────

_NAME_PATTERNS = [
    re.compile(r"(?:me\s+llamo|mi\s+nombre\s+es|soy)\s+([A-Za-zÀ-ÿ]+)", re.IGNORECASE),
    re.compile(r"(?:my\s+name\s+is|i'?m\s+called|i\s+am)\s+([A-Za-zÀ-ÿ]+)", re.IGNORECASE),
]

_GOAL_PATTERNS = [
    re.compile(r"(?:estoy|quiero|voy\s+a|necesito)\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
    re.compile(r"(?:i\s+am|i'?m|i\s+want\s+to|i\s+need\s+to)\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
]

_PREFERENCE_PATTERNS = [
    re.compile(r"(?:me\s+gusta|prefiero|me\s+encanta)\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
    re.compile(r"(?:i\s+like|i\s+love|i\s+prefer)\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
]

_FACT_PATTERNS = [
    re.compile(r"(?:trabajo\s+en|soy\s+de|vivo\s+en|estudio)\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
    re.compile(r"(?:i\s+work\s+(?:at|for|on)|i'?m\s+from|i\s+live\s+in)\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
    re.compile(r"(?:estoy\s+creando|estoy\s+desarrollando|creé|desarrollé|hice)\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
    re.compile(r"(?:i\s+(?:created|built|made|developed))\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
]


class MemoryExtractor:
    """Analyze messages and extract persistable user information."""

    def extract(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """Scan user messages for information worth persisting.

        Returns a dict with optional keys: ``name``, ``goals``,
        ``preferences``, ``facts``.
        """
        user_messages = [m for m in messages if m.get("role") == "user"]
        result: dict[str, Any] = {}

        name = self._extract_name(user_messages)
        if name:
            result["name"] = name

        goals = self._extract_goals(user_messages)
        if goals:
            result["goals"] = goals

        preferences = self._extract_preferences(user_messages)
        if preferences:
            result["preferences"] = preferences

        facts = self._extract_facts(user_messages)
        if facts:
            result["facts"] = facts

        return result

    # ── Internal helpers ──────────────────────────────────────────────

    def _extract_name(self, messages: list[dict[str, str]]) -> str | None:
        for msg in messages:
            content = msg.get("content", "")
            for pattern in _NAME_PATTERNS:
                match = pattern.search(content)
                if match:
                    return match.group(1).strip()
        return None

    def _extract_goals(self, messages: list[dict[str, str]]) -> list[str]:
        found: list[str] = []
        for msg in messages:
            content = msg.get("content", "")
            for pattern in _GOAL_PATTERNS:
                for match in pattern.finditer(content):
                    goal = match.group(1).strip()
                    if goal and goal not in found:
                        found.append(goal)
        return found

    def _extract_preferences(self, messages: list[dict[str, str]]) -> list[str]:
        found: list[str] = []
        for msg in messages:
            content = msg.get("content", "")
            for pattern in _PREFERENCE_PATTERNS:
                for match in pattern.finditer(content):
                    pref = match.group(1).strip()
                    if pref and pref not in found:
                        found.append(pref)
        return found

    def _extract_facts(self, messages: list[dict[str, str]]) -> list[str]:
        found: list[str] = []
        for msg in messages:
            content = msg.get("content", "")
            for pattern in _FACT_PATTERNS:
                for match in pattern.finditer(content):
                    fact = match.group(1).strip()
                    if fact and fact not in found:
                        found.append(fact)
        return found
