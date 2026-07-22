"""Memory summarization — generates concise summaries for long-term memories.

Uses simple extractive-summarization heuristics by default.
Can be extended with an LLM-based summarizer.
"""

from __future__ import annotations

import logging
import re

from app.long_term_memory.base import MemorySummarizer

logger = logging.getLogger(__name__)


class ExtractiveMemorySummarizer(MemorySummarizer):
    """Extractive summarizer using sentence scoring heuristics.

    Scores sentences by:
    - Position in text (first sentences weighted higher)
    - Length (sentences between 20-200 chars preferred)
    - Keyword density (sentences with more nouns/keywords score higher)
    """

    def __init__(self, default_max_length: int = 200) -> None:
        self._default_max_length = default_max_length

    async def summarize(self, content: str, max_length: int = 200) -> str:
        if not content or not content.strip():
            return ""

        max_len = max_length or self._default_max_length

        if len(content) <= max_len:
            return content.strip()

        sentences = self._split_sentences(content)
        if len(sentences) <= 1:
            return content[:max_len].rsplit(" ", 1)[0] + "..."

        scored = self._score_sentences(sentences)
        scored.sort(key=lambda x: x[1], reverse=True)

        selected: list[str] = []
        total_len = 0
        seen = set()

        for sentence, _score in scored:
            stripped = sentence.strip()
            if stripped in seen:
                continue
            seen.add(stripped)

            candidate_len = len(stripped) + (1 if selected else 0)
            if total_len + candidate_len > max_len:
                continue

            selected.append(stripped)
            total_len += len(stripped)

        if not selected:
            return content[:max_len].rsplit(" ", 1)[0] + "..."

        # Reorder selected sentences by original position
        position_map = {
            s.strip(): i for i, s in enumerate(sentences) if s.strip()
        }
        selected.sort(key=lambda s: position_map.get(s, 0))

        return " ".join(selected)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        raw = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in raw if s.strip()]

    @staticmethod
    def _score_sentences(sentences: list[str]) -> list[tuple[str, float]]:
        total = len(sentences)
        scored: list[tuple[str, float]] = []
        for i, sentence in enumerate(sentences):
            score = 0.0
            length = len(sentence)

            if length < 10 or length > 500:
                score -= 2.0

            if 20 <= length <= 200:
                score += 2.0

            position_factor = 1.0 - (i / max(total, 1)) * 0.5
            score += position_factor * 3.0

            keywords = len(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", sentence))
            score += min(keywords * 0.5, 3.0)

            digit_count = len(re.findall(r"\d+", sentence))
            score += min(digit_count * 0.3, 2.0)

            scored.append((sentence, score))

        return scored


class TruncationSummarizer(MemorySummarizer):
    """Simple summarizer that truncates content to a maximum length."""

    def __init__(self, default_max_length: int = 200) -> None:
        self._default_max_length = default_max_length

    async def summarize(self, content: str, max_length: int = 200) -> str:
        max_len = max_length or self._default_max_length
        if not content or len(content) <= max_len:
            return (content or "").strip()
        return content[:max_len].rsplit(" ", 1)[0] + "..."
