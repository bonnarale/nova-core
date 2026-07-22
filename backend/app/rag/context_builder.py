"""RAG context builder — assemble retrieval results into optimized prompts."""

from __future__ import annotations

from typing import Any, Optional

from app.rag.base import ContextBuilder
from app.rag.schemas import ContextPackage, RetrievedChunk


class DefaultContextBuilder(ContextBuilder):
    """Default context builder — assembles retrieved chunks into a context string."""

    def __init__(
        self,
        max_context_tokens: int = 4000,
        separator: str = "\n\n---\n\n",
        include_sources: bool = True,
    ) -> None:
        self._max_tokens = max_context_tokens
        self._separator = separator
        self._include_sources = include_sources

    @property
    def builder_id(self) -> str:
        return "default"

    async def build(
        self,
        query: str,
        retrieved_chunks: list[RetrievedChunk],
        user_context: Optional[dict[str, Any]] = None,
        conversation_history: Optional[list[dict[str, str]]] = None,
        goal_context: Optional[list[dict[str, Any]]] = None,
        task_context: Optional[list[dict[str, Any]]] = None,
        knowledge_context: Optional[list[dict[str, Any]]] = None,
        execution_context: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ContextPackage:
        context_parts: list[str] = []
        if user_context:
            profile_text = self._format_user_context(user_context)
            if profile_text:
                context_parts.append(f"[User Profile]\n{profile_text}")
        if conversation_history:
            conv_text = self._format_conversation(conversation_history)
            if conv_text:
                context_parts.append(f"[Conversation History]\n{conv_text}")
        if goal_context:
            goal_text = self._format_goals(goal_context)
            if goal_text:
                context_parts.append(f"[Active Goals]\n{goal_text}")
        if task_context:
            task_text = self._format_tasks(task_context)
            if task_text:
                context_parts.append(f"[Active Tasks]\n{task_text}")
        if knowledge_context:
            kg_text = self._format_knowledge(knowledge_context)
            if kg_text:
                context_parts.append(f"[Knowledge Graph]\n{kg_text}")
        retrieved_text = self._format_retrieved(retrieved_chunks)
        if retrieved_text:
            context_parts.append(f"[Retrieved Knowledge]\n{retrieved_text}")
        if execution_context:
            exec_text = self._format_execution(execution_context)
            if exec_text:
                context_parts.append(f"[Execution Context]\n{exec_text}")
        context_text = self._separator.join(context_parts)
        return ContextPackage(
            query=query,
            context_text=context_text,
            retrieved_chunks=retrieved_chunks,
            user_context=user_context or {},
            conversation_context=conversation_history or [],
            goal_context=goal_context or [],
            task_context=task_context or [],
            knowledge_context=knowledge_context or [],
            execution_context=execution_context or {},
            metadata={"parts_count": len(context_parts)},
        )

    def _format_user_context(self, ctx: dict[str, Any]) -> str:
        parts: list[str] = []
        if ctx.get("name"):
            parts.append(f"Name: {ctx['name']}")
        if ctx.get("role"):
            parts.append(f"Role: {ctx['role']}")
        if ctx.get("preferences"):
            parts.append(f"Preferences: {ctx['preferences']}")
        if ctx.get("facts"):
            facts = ctx["facts"]
            if isinstance(facts, list):
                parts.append("Facts: " + "; ".join(str(f) for f in facts[:5]))
        return "\n".join(parts)

    def _format_conversation(self, history: list[dict[str, str]]) -> str:
        lines: list[str] = []
        for msg in history[-5:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _format_goals(self, goals: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for g in goals[:3]:
            name = g.get("name", "unnamed")
            status = g.get("status", "unknown")
            lines.append(f"- {name} [{status}]")
        return "\n".join(lines)

    def _format_tasks(self, tasks: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for t in tasks[:3]:
            title = t.get("title", "untitled")
            status = t.get("status", "unknown")
            lines.append(f"- {title} [{status}]")
        return "\n".join(lines)

    def _format_knowledge(self, knowledge: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for k in knowledge[:5]:
            name = k.get("name", "")
            desc = k.get("description", "")[:100]
            if name:
                lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    def _format_retrieved(self, chunks: list[RetrievedChunk]) -> str:
        parts: list[str] = []
        token_budget = self._max_tokens
        for rc in chunks:
            content = rc.chunk.content
            if self._include_sources:
                title = rc.chunk.metadata.title
                source = rc.chunk.metadata.source
                if title or source:
                    source_label = title or source
                    content = f"[Source: {source_label}] {content}"
            est_tokens = len(content.split())
            if est_tokens > token_budget:
                words = content.split()[:token_budget]
                content = " ".join(words) + "..."
                parts.append(content)
                break
            parts.append(content)
            token_budget -= est_tokens
        return self._separator.join(parts)

    def _format_execution(self, ctx: dict[str, Any]) -> str:
        parts: list[str] = []
        if ctx.get("current_task"):
            parts.append(f"Current task: {ctx['current_task']}")
        if ctx.get("active_agent"):
            parts.append(f"Active agent: {ctx['active_agent']}")
        return "\n".join(parts)


class CompactContextBuilder(ContextBuilder):
    """Compact context builder — minimizes context size for token-constrained scenarios."""

    def __init__(self, max_tokens: int = 2000) -> None:
        self._max_tokens = max_tokens

    @property
    def builder_id(self) -> str:
        return "compact"

    async def build(
        self,
        query: str,
        retrieved_chunks: list[RetrievedChunk],
        user_context: Optional[dict[str, Any]] = None,
        conversation_history: Optional[list[dict[str, str]]] = None,
        goal_context: Optional[list[dict[str, Any]]] = None,
        task_context: Optional[list[dict[str, Any]]] = None,
        knowledge_context: Optional[list[dict[str, Any]]] = None,
        execution_context: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ContextPackage:
        parts: list[str] = []
        budget = self._max_tokens
        for rc in retrieved_chunks:
            text = rc.chunk.content[:200]
            tokens = len(text.split())
            if tokens > budget:
                break
            parts.append(text)
            budget -= tokens
        context_text = "\n".join(parts)
        return ContextPackage(
            query=query,
            context_text=context_text,
            retrieved_chunks=retrieved_chunks[:len(parts)],
            user_context=user_context or {},
            conversation_context=conversation_history or [],
            metadata={"builder": "compact", "budget_remaining": budget},
        )


def get_context_builder(builder_type: str = "default", **kwargs: Any) -> ContextBuilder:
    mapping: dict[str, type[ContextBuilder]] = {
        "default": DefaultContextBuilder,
        "compact": CompactContextBuilder,
    }
    cls = mapping.get(builder_type, DefaultContextBuilder)
    return cls(**kwargs) if kwargs else cls()
