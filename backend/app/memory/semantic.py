"""SemanticMemory — orchestrator for the Semantic Memory (RAG) layer.

Builds on top of pluggable ``EmbeddingProvider`` and
``VectorStoreProvider`` strategies to:
1. Store messages, profile facts, goals, and tasks as vector embeddings.
2. Retrieve the most semantically relevant entries for a query.
3. Filter results by a configurable relevance threshold.
4. Auto-index newly created profile data, goals, and tasks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

_UNSET = object()

from app.memory.embeddings import OllamaEmbeddingProvider
from app.memory.providers import EmbeddingProvider, VectorEntry, VectorStoreProvider
from app.memory.vector_store import ChromaDBVectorStore

logger = logging.getLogger(__name__)

COLLECTION_NAME = "nova_semantic_memory"


@dataclass
class SemanticMemoryConfig:
    """Configuration for semantic memory behavior.

    Attributes:
        top_k: Default number of results returned by ``search()``.
        relevance_threshold: Maximum cosine distance (0 = identical,
            2 = opposite). Results farther than this are filtered out.
            ``None`` disables filtering.
        auto_index: Whether to automatically index profile facts, goals,
            and tasks when they are provided to ``auto_index()``.
    """

    top_k: int = 3
    relevance_threshold: float | None = 0.85
    auto_index: bool = True


class SemanticMemory:
    """Vector-based semantic memory with pluggable providers.

    Backward-compatible with the v1 API::

        sm = SemanticMemory(chroma_client, ollama_service, top_k=3)
        await sm.store(session_id, content)
        results = await sm.search(query)

    New v2 features::

        config = SemanticMemoryConfig(top_k=5, relevance_threshold=0.75)
        sm = SemanticMemory(embedder=..., vector_store=..., config=config)

        await sm.index_profile_facts(profile_data)
        await sm.index_goals(goals)
        await sm.index_tasks(tasks)
        await sm.auto_index(profile=..., goals=..., tasks=...)
    """

    def __init__(
        self,
        chroma_client: Any = None,  # backward-compat: old-style (chroma, ollama, top_k)
        ollama: Any = None,  # backward-compat shim (OllamaService)
        *,
        embedder: EmbeddingProvider | None = None,
        vector_store: VectorStoreProvider | None = None,
        top_k: int = 3,
        config: SemanticMemoryConfig | None = None,
    ) -> None:
        self._config = config or SemanticMemoryConfig(top_k=top_k)

        # New-style: explicit providers
        if embedder is not None and vector_store is not None:
            self._embedder = embedder
            self._vector_store = vector_store
        # Backward-compat: (chroma_client, ollama)
        elif chroma_client is not None and ollama is not None:
            from app.memory.embeddings import OllamaEmbeddingProvider
            from app.memory.vector_store import ChromaDBVectorStore

            self._embedder = OllamaEmbeddingProvider(ollama)
            self._vector_store = ChromaDBVectorStore(chroma_client)
        else:
            raise TypeError(
                "SemanticMemory requires either (embedder, vector_store) "
                "or (chroma_client, ollama)"
            )

        self._collection_ref = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> SemanticMemoryConfig:
        return self._config

    @config.setter
    def config(self, value: SemanticMemoryConfig) -> None:
        self._config = value

    @property
    def embedder(self) -> EmbeddingProvider:
        return self._embedder

    @property
    def vector_store(self) -> VectorStoreProvider:
        return self._vector_store

    # ------------------------------------------------------------------
    # Collection (lazy init)
    # ------------------------------------------------------------------

    async def _collection(self):
        if self._collection_ref is None:
            self._collection_ref = await self._vector_store.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection_ref

    # ------------------------------------------------------------------
    # Core API (backward-compatible)
    # ------------------------------------------------------------------

    async def store(self, session_id: UUID | str, content: str) -> None:
        """Embed *content* and store it in the vector collection."""
        if not content or not content.strip():
            logger.debug("Skipping store for session=%s: empty content", session_id)
            return
        embedding = await self._embedder.embed(content)
        if not embedding:
            logger.warning("Skipping store for session=%s: empty embedding", session_id)
            return

        doc_id = f"{session_id}::{hash(content)}"
        col = await self._collection()
        entry = VectorEntry(
            id=doc_id,
            document=content,
            metadata={"session_id": str(session_id), "source": "message"},
            embedding=embedding,
        )
        await self._vector_store.add(col, [entry])
        logger.debug("Stored semantic memory: session=%s id=%s", session_id, doc_id)

    async def search(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None | object = _UNSET,
    ) -> list[dict[str, Any]]:
        """Retrieve memories semantically similar to *query*.

        Returns a list of dicts with keys ``content``, ``session_id``,
        ``source``, ``distance``.

        If *top_k* is ``None``, the config's ``top_k`` is used.
        If *threshold* is not passed (or passed explicitly as the sentinel),
        the config's ``relevance_threshold`` is used.
        Pass ``threshold=None`` to disable threshold filtering entirely.
        """
        k = top_k if top_k is not None else self._config.top_k
        t = self._config.relevance_threshold if threshold is _UNSET else threshold

        query_embedding = await self._embedder.embed(query)
        if not query_embedding:
            return []

        col = await self._collection()
        entries = await self._vector_store.search(
            col,
            query_embedding=query_embedding,
            top_k=k,
            threshold=t,
        )

        results: list[dict[str, Any]] = []
        for e in entries:
            results.append({
                "content": e.document,
                "session_id": e.metadata.get("session_id", ""),
                "source": e.metadata.get("source", "message"),
                "distance": e.distance,
            })

        logger.debug(
            "Semantic search returned %d results for query (len=%d) threshold=%s",
            len(results), len(query), t,
        )
        return results

    # ------------------------------------------------------------------
    # Multi-source indexing (v2)
    # ------------------------------------------------------------------

    async def index_profile_facts(self, profile_data: dict[str, Any] | None) -> None:
        """Index user profile facts as semantic memories."""
        if not profile_data:
            return

        entries: list[VectorEntry] = []
        facts: list[str] = list(profile_data.get("facts") or [])
        name = profile_data.get("name")

        if name:
            facts.append(f"User name is {name}")

        preferences = profile_data.get("preferences") or {}
        for key, val in preferences.items():
            facts.append(f"User preference: {key}={val}")

        for i, fact in enumerate(facts):
            embedding = await self._embedder.embed(fact)
            if not embedding:
                continue
            entries.append(
                VectorEntry(
                    id=f"profile_fact::{hash(fact)}",
                    document=fact,
                    metadata={"source": "profile_fact", "index": i},
                    embedding=embedding,
                )
            )

        if entries:
            col = await self._collection()
            await self._vector_store.add(col, entries)
            logger.debug("Indexed %d profile facts", len(entries))

    async def index_goals(self, goals: list[dict[str, Any]] | None) -> None:
        """Index goals as semantic memories."""
        if not goals:
            return

        entries: list[VectorEntry] = []
        for goal in goals:
            title = goal.get("title", "") or goal.get("name", "")
            description = goal.get("description", "")
            text = f"Goal: {title}" + (f" — {description}" if description else "")
            embedding = await self._embedder.embed(text)
            if not embedding:
                continue
            entries.append(
                VectorEntry(
                    id=f"goal::{hash(text)}",
                    document=text,
                    metadata={
                        "source": "goal",
                        "goal_id": goal.get("id", ""),
                        "status": goal.get("status", ""),
                    },
                    embedding=embedding,
                )
            )

        if entries:
            col = await self._collection()
            await self._vector_store.add(col, entries)
            logger.debug("Indexed %d goals", len(entries))

    async def index_tasks(self, tasks: list[dict[str, Any]] | None) -> None:
        """Index completed tasks as semantic memories."""
        if not tasks:
            return

        entries: list[VectorEntry] = []
        for task in tasks:
            status = task.get("status", "")
            if status not in ("COMPLETED", "DONE", "SUCCEEDED", "completed", "done"):
                continue

            goal_text = task.get("goal", "") or task.get("description", "")
            if not goal_text:
                continue

            text = f"Completed task: {goal_text}"
            embedding = await self._embedder.embed(text)
            if not embedding:
                continue
            entries.append(
                VectorEntry(
                    id=f"task::{hash(text)}",
                    document=text,
                    metadata={
                        "source": "completed_task",
                        "task_id": task.get("id", ""),
                        "status": status,
                    },
                    embedding=embedding,
                )
            )

        if entries:
            col = await self._collection()
            await self._vector_store.add(col, entries)
            logger.debug("Indexed %d completed tasks", len(entries))

    async def auto_index(
        self,
        profile: dict[str, Any] | None = None,
        goals: list[dict[str, Any]] | None = None,
        tasks: list[dict[str, Any]] | None = None,
    ) -> None:
        """Convenience: index all sources at once (respects ``auto_index`` flag)."""
        if not self._config.auto_index:
            return
        if profile:
            await self.index_profile_facts(profile)
        if goals:
            await self.index_goals(goals)
        if tasks:
            await self.index_tasks(tasks)

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    async def clear(self) -> None:
        """Delete all entries in the collection."""
        col = await self._collection()
        all_ids = await self._vector_store.get_all_ids(col)
        if all_ids:
            await self._vector_store.delete(col, all_ids)

    async def count(self) -> int:
        col = await self._collection()
        return await self._vector_store.count(col)
