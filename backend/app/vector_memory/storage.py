"""Vector storage backends — concrete implementations of the storage layer."""

from __future__ import annotations

import logging
import math
from typing import Any, Optional

from app.vector_memory.schemas import MemoryCategory, VectorRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# InMemoryVectorStorage
# ---------------------------------------------------------------------------

class InMemoryVectorStorage:
    """In-memory vector storage — no external dependencies."""

    def __init__(self) -> None:
        self._vectors: dict[str, VectorRecord] = {}
        self._index: dict[str, list[str]] = {}
        self._user_index: dict[str, list[str]] = {}
        self._session_index: dict[str, list[str]] = {}
        self._tag_index: dict[str, list[str]] = {}
        self._category_index: dict[str, list[str]] = {}
        self._storage_usage: int = 0

    async def add(self, records: list[VectorRecord]) -> int:
        count = 0
        for record in records:
            if not record.vector_id:
                continue
            self._vectors[record.vector_id] = record
            self._index_vector(record)
            self._storage_usage += len(record.content) + len(record.embedding) * 4
            count += 1
        return count

    async def update(self, records: list[VectorRecord]) -> int:
        count = 0
        for record in records:
            if record.vector_id not in self._vectors:
                continue
            old = self._vectors[record.vector_id]
            self._deindex_vector(old)
            self._vectors[record.vector_id] = record
            self._index_vector(record)
            count += 1
        return count

    async def delete(self, vector_ids: list[str]) -> int:
        count = 0
        for vid in vector_ids:
            if vid in self._vectors:
                self._deindex_vector(self._vectors[vid])
                del self._vectors[vid]
                count += 1
        return count

    async def get(self, vector_id: str) -> Optional[VectorRecord]:
        return self._vectors.get(vector_id)

    async def list_by_user(
        self,
        user_id: str,
        memory_category: Optional[MemoryCategory] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        ids = self._user_index.get(user_id, [])
        return self._filter_and_slice(ids, memory_category, limit, offset)

    async def list_by_session(
        self,
        session_id: str,
        memory_category: Optional[MemoryCategory] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        ids = self._session_index.get(session_id, [])
        return self._filter_and_slice(ids, memory_category, limit, offset)

    async def list_by_category(
        self,
        memory_category: MemoryCategory,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        ids = self._category_index.get(memory_category.value, [])
        result = [self._vectors[vid] for vid in ids if vid in self._vectors]
        return result[offset:offset + limit]

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[VectorRecord]:
        all_records = list(self._vectors.values())
        return all_records[offset:offset + limit]

    async def count(self) -> int:
        return len(self._vectors)

    async def count_by_category(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for vid, rec in self._vectors.items():
            cat = rec.memory_type.value
            result[cat] = result.get(cat, 0) + 1
        return result

    async def get_all_ids(self) -> list[str]:
        return list(self._vectors.keys())

    async def search_by_tags(self, tags: list[str], limit: int = 50) -> list[VectorRecord]:
        matched_ids: set[str] = set()
        for tag in tags:
            tagged = self._tag_index.get(tag, [])
            matched_ids.update(tagged)
        result = [self._vectors[vid] for vid in matched_ids if vid in self._vectors]
        return result[:limit]

    async def search_all(self, query_embedding: list[float], top_k: int = 10, threshold: Optional[float] = None) -> list[VectorRecord]:
        scored: list[tuple[float, VectorRecord]] = []
        for vid, rec in self._vectors.items():
            if not rec.embedding:
                continue
            sim = _cosine_similarity(query_embedding, rec.embedding)
            if threshold is None or sim >= threshold:
                scored.append((sim, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        for s, rec in scored[:top_k]:
            rec.score = s
        return [rec for _, rec in scored[:top_k]]

    async def search_with_filters(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        threshold: Optional[float] = None,
        memory_category: Optional[MemoryCategory] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> list[VectorRecord]:
        candidates = list(self._vectors.values())

        if memory_category:
            candidates = [r for r in candidates if r.memory_type == memory_category]
        if user_id:
            candidates = [r for r in candidates if r.user_id == user_id]
        if session_id:
            candidates = [r for r in candidates if r.session_id == session_id]
        if tags:
            tag_set = set(tags)
            candidates = [r for r in candidates if tag_set.intersection(r.tags)]

        scored: list[tuple[float, VectorRecord]] = []
        for rec in candidates:
            if not rec.embedding:
                continue
            sim = _cosine_similarity(query_embedding, rec.embedding)
            if threshold is None or sim >= threshold:
                scored.append((sim, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        for s, rec in scored[:top_k]:
            rec.score = s
        return [rec for _, rec in scored[:top_k]]

    async def health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "type": "in_memory",
            "total_vectors": len(self._vectors),
            "storage_usage_bytes": self._storage_usage,
        }

    def get_storage_usage(self) -> int:
        return self._storage_usage

    def _index_vector(self, record: VectorRecord) -> None:
        if record.user_id:
            self._user_index.setdefault(record.user_id, []).append(record.vector_id)
        if record.session_id:
            self._session_index.setdefault(record.session_id, []).append(record.vector_id)
        if record.memory_type:
            self._category_index.setdefault(record.memory_type.value, []).append(record.vector_id)
        for tag in record.tags:
            self._tag_index.setdefault(tag, []).append(record.vector_id)

    def _deindex_vector(self, record: VectorRecord) -> None:
        if record.user_id and record.vector_id in self._user_index.get(record.user_id, []):
            self._user_index[record.user_id].remove(record.vector_id)
        if record.session_id and record.vector_id in self._session_index.get(record.session_id, []):
            self._session_index[record.session_id].remove(record.vector_id)
        if record.memory_type and record.vector_id in self._category_index.get(record.memory_type.value, []):
            self._category_index[record.memory_type.value].remove(record.vector_id)
        for tag in record.tags:
            if record.vector_id in self._tag_index.get(tag, []):
                self._tag_index[tag].remove(record.vector_id)

    def _filter_and_slice(
        self,
        ids: list[str],
        memory_category: Optional[MemoryCategory],
        limit: int,
        offset: int,
    ) -> list[VectorRecord]:
        result = []
        for vid in ids:
            rec = self._vectors.get(vid)
            if rec is None:
                continue
            if memory_category and rec.memory_type != memory_category:
                continue
            result.append(rec)
        return result[offset:offset + limit]


# ---------------------------------------------------------------------------
# ChromaVectorStorage
# ---------------------------------------------------------------------------

class ChromaVectorStorage:
    """Vector storage backed by ChromaDB."""

    def __init__(self, chroma_client: Any = None) -> None:
        self._client = chroma_client
        self._collections: dict[str, Any] = {}
        self._collection_name = "nova_vector_memory"

    async def _get_or_create_collection(self) -> Any:
        if self._collection_name not in self._collections:
            if self._client is None:
                raise RuntimeError("ChromaDB client not initialized")
            self._collections[self._collection_name] = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[self._collection_name]

    async def add(self, records: list[VectorRecord]) -> int:
        col = await self._get_or_create_collection()
        ids = [r.vector_id for r in records]
        documents = [r.content for r in records]
        metadatas = [self._record_to_metadata(r) for r in records]
        embeddings = [r.embedding for r in records if r.embedding]
        valid = [i for i, e in enumerate(embeddings) if e]
        if not valid:
            return 0
        col.add(
            ids=[ids[i] for i in valid],
            embeddings=[embeddings[i] for i in valid],
            metadatas=[metadatas[i] for i in valid],
            documents=[documents[i] for i in valid],
        )
        return len(valid)

    async def update(self, records: list[VectorRecord]) -> int:
        col = await self._get_or_create_collection()
        for record in records:
            col.update(
                ids=[record.vector_id],
                documents=[record.content] if record.content else None,
                metadatas=[self._record_to_metadata(record)],
                embeddings=[record.embedding] if record.embedding else None,
            )
        return len(records)

    async def delete(self, vector_ids: list[str]) -> int:
        col = await self._get_or_create_collection()
        col.delete(ids=vector_ids)
        return len(vector_ids)

    async def get(self, vector_id: str) -> Optional[VectorRecord]:
        col = await self._get_or_create_collection()
        result = col.get(ids=[vector_id])
        if not result or not result.get("ids"):
            return None
        return self._metadata_to_record(
            vector_id=result["ids"][0],
            document=result["documents"][0] if result.get("documents") else "",
            metadata=result["metadatas"][0] if result.get("metadatas") else {},
        )

    async def list_by_user(
        self,
        user_id: str,
        memory_category: Optional[MemoryCategory] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        where: dict[str, Any] = {"user_id": user_id}
        if memory_category:
            where["memory_type"] = memory_category.value
        col = await self._get_or_create_collection()
        result = col.get(where=where, limit=limit, offset=offset)
        return self._chroma_result_to_records(result)

    async def list_by_session(
        self,
        session_id: str,
        memory_category: Optional[MemoryCategory] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        where: dict[str, Any] = {"session_id": session_id}
        if memory_category:
            where["memory_type"] = memory_category.value
        col = await self._get_or_create_collection()
        result = col.get(where=where, limit=limit, offset=offset)
        return self._chroma_result_to_records(result)

    async def list_by_category(
        self,
        memory_category: MemoryCategory,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VectorRecord]:
        col = await self._get_or_create_collection()
        result = col.get(where={"memory_type": memory_category.value}, limit=limit, offset=offset)
        return self._chroma_result_to_records(result)

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[VectorRecord]:
        col = await self._get_or_create_collection()
        result = col.get(limit=limit, offset=offset)
        return self._chroma_result_to_records(result)

    async def count(self) -> int:
        col = await self._get_or_create_collection()
        return col.count()

    async def count_by_category(self) -> dict[str, int]:
        col = await self._get_or_create_collection()
        result = col.get()
        counts: dict[str, int] = {}
        if result.get("metadatas"):
            for meta in result["metadatas"]:
                cat = meta.get("memory_type", "unknown")
                counts[cat] = counts.get(cat, 0) + 1
        return counts

    async def get_all_ids(self) -> list[str]:
        col = await self._get_or_create_collection()
        result = col.get()
        return result.get("ids", [])

    async def search_by_tags(self, tags: list[str], limit: int = 50) -> list[VectorRecord]:
        col = await self._get_or_create_collection()
        results = []
        for tag in tags:
            result = col.get(where={"tags": tag}, limit=limit)
            results.extend(self._chroma_result_to_records(result))
        return results[:limit]

    async def search_with_filters(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        threshold: Optional[float] = None,
        memory_category: Optional[MemoryCategory] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> list[VectorRecord]:
        col = await self._get_or_create_collection()
        where: dict[str, Any] = {}
        if memory_category:
            where["memory_type"] = memory_category.value
        if user_id:
            where["user_id"] = user_id
        if session_id:
            where["session_id"] = session_id

        results = col.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where if where else None,
        )
        records = self._chroma_result_to_records(results)
        if tags:
            tag_set = set(tags)
            records = [r for r in records if tag_set.intersection(r.tags)]
        if threshold is not None:
            records = [r for r in records if r.score >= threshold]
        return records[:top_k]

    async def health(self) -> dict[str, Any]:
        try:
            col = await self._get_or_create_collection()
            count = col.count()
            return {"status": "healthy", "type": "chroma", "total_vectors": count}
        except Exception as e:
            return {"status": "unhealthy", "type": "chroma", "error": str(e)}

    def _record_to_metadata(self, record: VectorRecord) -> dict[str, Any]:
        return {
            "source_id": record.source_id,
            "document_id": record.document_id,
            "memory_type": record.memory_type.value,
            "user_id": record.user_id,
            "session_id": record.session_id,
            "tags": ",".join(record.tags),
            "timestamp": record.timestamp.isoformat(),
            "confidence": record.confidence,
            "importance": record.importance,
            "embedding_provider": record.embedding_provider,
            **record.metadata,
        }

    @staticmethod
    def _chroma_result_to_records(result: dict[str, Any]) -> list[VectorRecord]:
        records: list[VectorRecord] = []
        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        distances = result.get("distances", [])

        for i, vid in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) else {}
            doc = documents[i] if i < len(documents) else ""
            distance = distances[0][i] if distances and distances[0] and i < len(distances[0]) else 0.0
            record = ChromaVectorStorage._metadata_to_record(vid, doc, meta)
            record.distance = distance
            record.score = 1.0 - distance if distance else 0.0
            records.append(record)
        return records

    @staticmethod
    def _metadata_to_record(vector_id: str, document: str, metadata: dict[str, Any]) -> VectorRecord:
        tags_str = metadata.pop("tags", "")
        tags = tags_str.split(",") if tags_str else []
        memory_type_str = metadata.pop("memory_type", "knowledge")
        try:
            memory_type = MemoryCategory(memory_type_str)
        except ValueError:
            memory_type = MemoryCategory.KNOWLEDGE

        return VectorRecord(
            vector_id=vector_id,
            source_id=metadata.pop("source_id", ""),
            document_id=metadata.pop("document_id", ""),
            memory_type=memory_type,
            user_id=metadata.pop("user_id", ""),
            session_id=metadata.pop("session_id", ""),
            tags=tags,
            confidence=float(metadata.pop("confidence", 1.0)),
            importance=float(metadata.pop("importance", 0.5)),
            embedding_provider=metadata.pop("embedding_provider", ""),
            content=document,
            metadata=metadata,
        )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
