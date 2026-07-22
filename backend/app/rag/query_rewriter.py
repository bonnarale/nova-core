"""RAG query rewriter — transform queries for better retrieval."""

from __future__ import annotations

import re
from typing import Any, Optional

from app.rag.base import QueryRewriter
from app.rag.schemas import QueryRewrite


class PassthroughRewriter(QueryRewriter):
    """No-op rewriter — returns the query unchanged."""

    @property
    def rewriter_id(self) -> str:
        return "passthrough"

    async def rewrite(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> QueryRewrite:
        return QueryRewrite(
            original_query=query,
            rewritten_query=query,
            expansion_terms=[],
            strategy="passthrough",
        )


class KeywordExpansionRewriter(QueryRewriter):
    """Expands query with additional keywords and synonyms."""

    def __init__(self, max_expansion_terms: int = 5) -> None:
        self._max_terms = max_expansion_terms

    @property
    def rewriter_id(self) -> str:
        return "keyword_expansion"

    async def rewrite(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> QueryRewrite:
        words = re.findall(r'\w+', query.lower())
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "can", "shall", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "about", "like",
            "through", "after", "over", "between", "out", "against", "during",
            "without", "before", "under", "around", "among", "what", "which",
            "who", "whom", "this", "that", "these", "those", "how", "when",
            "where", "why", "and", "but", "or", "not", "no", "if",
        }
        content_words = [w for w in words if w not in stop_words and len(w) > 2]
        expansion_terms: list[str] = []
        for word in content_words[:self._max_terms]:
            expanded = self._expand_word(word)
            expansion_terms.extend(expanded)
        expansion_terms = list(dict.fromkeys(expansion_terms))[:self._max_terms]
        boosted_query = query
        if expansion_terms:
            boosted_query = f"{query} {' '.join(expansion_terms)}"
        return QueryRewrite(
            original_query=query,
            rewritten_query=boosted_query,
            expansion_terms=expansion_terms,
            strategy="keyword_expansion",
        )

    def _expand_word(self, word: str) -> list[str]:
        expansions: dict[str, list[str]] = {
            "python": ["programming", "code", "script"],
            "error": ["bug", "issue", "problem", "exception", "fault"],
            "test": ["testing", "specification", "validation", "verification"],
            "data": ["information", "dataset", "records"],
            "model": ["architecture", "framework", "structure"],
            "function": ["method", "procedure", "routine"],
            "class": ["type", "object", "interface"],
            "file": ["document", "resource", "artifact"],
            "server": ["host", "machine", "node"],
            "client": ["user", "consumer", "frontend"],
        }
        return expansions.get(word, [])


class ContextualRewriter(QueryRewriter):
    """Rewrites queries using conversation context for better relevance."""

    @property
    def rewriter_id(self) -> str:
        return "contextual"

    async def rewrite(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> QueryRewrite:
        expanded_terms: list[str] = []
        if context:
            history = context.get("conversation_history", [])
            if history:
                recent = history[-3:]
                for msg in recent:
                    content = msg.get("content", "")
                    if content:
                        words = re.findall(r'\w+', content.lower())
                        key_words = [w for w in words if len(w) > 4][:3]
                        expanded_terms.extend(key_words)
            topics = context.get("topics", [])
            expanded_terms.extend(topics[:3])
        expanded_terms = list(dict.fromkeys(expanded_terms))[:5]
        rewritten = query
        if expanded_terms:
            rewritten = f"{query} context: {' '.join(expanded_terms)}"
        return QueryRewrite(
            original_query=query,
            rewritten_query=rewritten,
            expansion_terms=expanded_terms,
            strategy="contextual",
        )


class HyDEQueryRewriter(QueryRewriter):
    """Hypothetical Document Embedding — generates a hypothetical answer for better retrieval."""

    def __init__(self, prompt_template: str = "") -> None:
        self._template = prompt_template or (
            "Write a detailed paragraph that would answer the following question: {query}\n"
            "Provide specific facts and details."
        )

    @property
    def rewriter_id(self) -> str:
        return "hyde"

    async def rewrite(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> QueryRewrite:
        hypothetical = self._template.format(query=query)
        return QueryRewrite(
            original_query=query,
            rewritten_query=hypothetical,
            expansion_terms=[],
            strategy="hyde",
        )


def get_query_rewriter(strategy: str = "passthrough", **kwargs: Any) -> QueryRewriter:
    mapping: dict[str, type[QueryRewriter]] = {
        "passthrough": PassthroughRewriter,
        "keyword_expansion": KeywordExpansionRewriter,
        "contextual": ContextualRewriter,
        "hyde": HyDEQueryRewriter,
    }
    cls = mapping.get(strategy, PassthroughRewriter)
    return cls(**kwargs) if kwargs else cls()
