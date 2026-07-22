"""ChromaDBVectorStore — concrete VectorStoreProvider using ChromaDB."""

from __future__ import annotations

import logging
from typing import Any

from app.memory.providers import VectorEntry, VectorStoreProvider

logger = logging.getLogger(__name__)


class ChromaDBVectorStore(VectorStoreProvider):
    """Vector store backed by ChromaDB.

    Wraps the synchronous ChromaDB ``Collection`` API with an async
    interface so consumers stay async throughout.
    """

    def __init__(self, chroma_client: Any) -> None:
        self._client = chroma_client
        self._collections: dict[str, Any] = {}

    async def get_or_create_collection(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> Any:
        if name in self._collections:
            return self._collections[name]
        col = self._client.get_or_create_collection(name=name, metadata=metadata)
        self._collections[name] = col
        return col

    async def add(self, collection: Any, entries: list[VectorEntry]) -> None:
        ids = [e.id for e in entries]
        documents = [e.document for e in entries]
        metadatas = [e.metadata for e in entries]
        embeddings = [e.embedding for e in entries]

        # Filter out entries without embeddings
        valid_ids: list[str] = []
        valid_docs: list[str] = []
        valid_meta: list[dict[str, Any]] = []
        valid_embs: list[list[float]] = []

        for i, emb in enumerate(embeddings):
            if emb:
                valid_ids.append(ids[i])
                valid_docs.append(documents[i])
                valid_meta.append(metadatas[i])
                valid_embs.append(emb)

        if not valid_ids:
            logger.warning("No valid embeddings to add — skipping")
            return

        collection.add(
            ids=valid_ids,
            embeddings=valid_embs,
            metadatas=valid_meta,
            documents=valid_docs,
        )

    async def search(
        self,
        collection: Any,
        query_embedding: list[float],
        top_k: int = 5,
        threshold: float | None = None,
    ) -> list[VectorEntry]:
        if not query_embedding:
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        entries: list[VectorEntry] = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 0.0
                if threshold is not None and distance > threshold:
                    continue
                entries.append(
                    VectorEntry(
                        id=doc_id,
                        document=results["documents"][0][i],
                        metadata=results["metadatas"][0][i],
                        distance=distance,
                    )
                )
        return entries

    async def delete(self, collection: Any, ids: list[str]) -> None:
        if ids:
            collection.delete(ids=ids)

    async def count(self, collection: Any) -> int:
        return collection.count()

    async def get_all_ids(self, collection: Any) -> list[str]:
        return collection.get()["ids"]
