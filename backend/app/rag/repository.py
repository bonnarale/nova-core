"""RAG repository — storage abstraction for chunks and embeddings."""

from __future__ import annotations

import logging
import math
from typing import Any, Optional

from app.rag.base import VectorRepository
from app.rag.schemas import Chunk, FilterCondition, FilterOperator, RetrievedChunk

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _matches_filter(meta: dict[str, Any], fc: FilterCondition) -> bool:
    val = meta.get(fc.field)
    if val is None:
        return False
    op = fc.operator
    if op == FilterOperator.EQ:
        return val == fc.value
    if op == FilterOperator.NEQ:
        return val != fc.value
    if op == FilterOperator.IN:
        return val in fc.value if isinstance(fc.value, (list, set)) else False
    if op == FilterOperator.NIN:
        return val not in fc.value if isinstance(fc.value, (list, set)) else True
    if op == FilterOperator.GT:
        return val > fc.value
    if op == FilterOperator.GTE:
        return val >= fc.value
    if op == FilterOperator.LT:
        return val < fc.value
    if op == FilterOperator.LTE:
        return val <= fc.value
    if op == FilterOperator.CONTAINS:
        return fc.value in str(val)
    if op == FilterOperator.STARTS_WITH:
        return str(val).startswith(str(fc.value))
    return True


class InMemoryRepository(VectorRepository):
    """In-memory vector repository — no external dependencies."""

    def __init__(self) -> None:
        self._collections: dict[str, list[dict[str, Any]]] = {}

    @property
    def repository_id(self) -> str:
        return "in_memory"

    async def add(
        self,
        collection: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> int:
        if collection not in self._collections:
            self._collections[collection] = []
        count = 0
        for chunk, emb in zip(chunks, embeddings):
            entry = {
                "id": chunk.id,
                "content": chunk.content,
                "metadata": chunk.metadata.model_dump(),
                "embedding": emb,
            }
            self._collections[collection].append(entry)
            count += 1
        return count

    async def search(
        self,
        collection: str,
        embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.0,
        filters: Optional[list[FilterCondition]] = None,
    ) -> list[RetrievedChunk]:
        entries = self._collections.get(collection, [])
        scored: list[tuple[float, dict[str, Any]]] = []
        for entry in entries:
            if filters:
                meta = entry.get("metadata", {})
                if not all(_matches_filter(meta, fc) for fc in filters):
                    continue
            score = _cosine_similarity(embedding, entry.get("embedding", []))
            if score >= threshold:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[RetrievedChunk] = []
        for score, entry in scored[:top_k]:
            from app.rag.schemas import ChunkMetadata, RetrievalMethod
            meta_dict = entry.get("metadata", {})
            chunk_meta = ChunkMetadata(**meta_dict) if meta_dict else ChunkMetadata()
            chunk = Chunk(id=entry["id"], content=entry["content"], metadata=chunk_meta, embedding=entry.get("embedding"))
            results.append(RetrievedChunk(chunk=chunk, score=score, retrieval_method=RetrievalMethod.VECTOR))
        return results

    async def delete(self, collection: str, ids: list[str]) -> int:
        entries = self._collections.get(collection, [])
        id_set = set(ids)
        before = len(entries)
        self._collections[collection] = [e for e in entries if e["id"] not in id_set]
        return before - len(self._collections.get(collection, []))

    async def count(self, collection: str) -> int:
        return len(self._collections.get(collection, []))

    async def get_all_ids(self, collection: str) -> list[str]:
        return [e["id"] for e in self._collections.get(collection, [])]

    async def health(self) -> dict[str, Any]:
        total = sum(len(v) for v in self._collections.values())
        return {
            "status": "healthy",
            "repository": self.repository_id,
            "collections": len(self._collections),
            "total_entries": total,
        }


class ChromaRepository(VectorRepository):
    """ChromaDB-backed vector repository."""

    def __init__(self, client: Any = None) -> None:
        self._client = client
        self._collections: dict[str, Any] = {}

    @property
    def repository_id(self) -> str:
        return "chroma"

    async def _get_or_create(self, collection: str) -> Any:
        if collection not in self._collections:
            if self._client is None:
                raise RuntimeError("ChromaDB client not initialized")
            self._collections[collection] = self._client.get_or_create_collection(
                name=collection, metadata={"hnsw:space": "cosine"}
            )
        return self._collections[collection]

    async def add(
        self,
        collection: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> int:
        col = await self._get_or_create(collection)
        ids = [c.id for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [c.metadata.model_dump() for c in chunks]
        col.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        return len(chunks)

    async def search(
        self,
        collection: str,
        embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.0,
        filters: Optional[list[FilterCondition]] = None,
    ) -> list[RetrievedChunk]:
        col = await self._get_or_create(collection)
        where = None
        if filters and len(filters) == 1:
            fc = filters[0]
            where = {fc.field: fc.value}
        results = col.query(query_embeddings=[embedding], n_results=top_k, where=where)
        chunks_out: list[RetrievedChunk] = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        for i, doc_id in enumerate(ids):
            score = 1.0 - distances[i] if i < len(distances) else 0.0
            if score < threshold:
                continue
            meta_dict = metadatas[i] if i < len(metadatas) else {}
            from app.rag.schemas import ChunkMetadata, RetrievalMethod
            chunk_meta = ChunkMetadata(**meta_dict) if meta_dict else ChunkMetadata()
            chunk = Chunk(id=doc_id, content=documents[i] if i < len(documents) else "", metadata=chunk_meta)
            chunks_out.append(RetrievedChunk(chunk=chunk, score=score, retrieval_method=RetrievalMethod.VECTOR))
        return chunks_out

    async def delete(self, collection: str, ids: list[str]) -> int:
        col = await self._get_or_create(collection)
        col.delete(ids=ids)
        return len(ids)

    async def count(self, collection: str) -> int:
        col = await self._get_or_create(collection)
        return col.count()

    async def get_all_ids(self, collection: str) -> list[str]:
        col = await self._get_or_create(collection)
        result = col.get()
        return result.get("ids", [])

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy" if self._client else "uninitialized", "repository": self.repository_id}


def get_repository(repository_type: str = "in_memory", **kwargs: Any) -> VectorRepository:
    repos = {
        "in_memory": lambda kw: InMemoryRepository(),
        "chroma": lambda kw: ChromaRepository(client=kw.get("client")),
    }
    factory = repos.get(repository_type)
    if not factory:
        raise ValueError(f"Unknown repository type: {repository_type}")
    return factory(kwargs)
