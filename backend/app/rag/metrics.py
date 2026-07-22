"""RAG metrics — collect performance and usage metrics."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RequestMetric:
    request_id: str
    query: str
    start_time: float
    end_time: Optional[float] = None
    latency_ms: float = 0.0
    chunks_retrieved: int = 0
    chunks_reranked: int = 0
    retrieval_latency_ms: float = 0.0
    rerank_latency_ms: float = 0.0
    embedding_latency_ms: float = 0.0
    cache_hit: bool = False
    success: bool = True
    error: Optional[str] = None

    def complete(self, success: bool = True, error: Optional[str] = None) -> None:
        self.end_time = time.time()
        self.latency_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error = error


class RAGMetrics:
    """Collects and aggregates RAG pipeline metrics."""

    def __init__(self) -> None:
        self._requests: list[RequestMetric] = []
        self._total_queries = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_documents = 0
        self._total_chunks = 0
        self._total_latency_ms = 0.0
        self._total_retrieval_latency_ms = 0.0
        self._total_rerank_latency_ms = 0.0
        self._total_embedding_latency_ms = 0.0

    @property
    def total_queries(self) -> int:
        return self._total_queries

    def record_request(self, metric: RequestMetric) -> None:
        self._requests.append(metric)
        self._total_queries += 1
        self._total_latency_ms += metric.latency_ms
        self._total_retrieval_latency_ms += metric.retrieval_latency_ms
        self._total_rerank_latency_ms += metric.rerank_latency_ms
        self._total_embedding_latency_ms += metric.embedding_latency_ms
        if metric.cache_hit:
            self._cache_hits += 1
        else:
            self._cache_misses += 1
        if len(self._requests) > 1000:
            self._requests = self._requests[-500:]

    def record_document_indexed(self, chunk_count: int = 1) -> None:
        self._total_documents += 1
        self._total_chunks += chunk_count

    def record_document_removed(self, chunk_count: int = 1) -> None:
        self._total_chunks = max(0, self._total_chunks - chunk_count)

    def get_summary(self) -> dict[str, Any]:
        total = self._total_queries
        cache_total = self._cache_hits + self._cache_misses
        return {
            "total_queries": total,
            "average_latency_ms": self._total_latency_ms / max(total, 1),
            "average_retrieval_latency_ms": self._total_retrieval_latency_ms / max(total, 1),
            "average_rerank_latency_ms": self._total_rerank_latency_ms / max(total, 1),
            "average_embedding_latency_ms": self._total_embedding_latency_ms / max(total, 1),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": self._cache_hits / max(cache_total, 1),
            "total_documents": self._total_documents,
            "total_chunks": self._total_chunks,
        }

    def get_recent_requests(self, limit: int = 50) -> list[RequestMetric]:
        return list(self._requests[-limit:])

    def reset(self) -> None:
        self._requests.clear()
        self._total_queries = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_latency_ms = 0.0
        self._total_retrieval_latency_ms = 0.0
        self._total_rerank_latency_ms = 0.0
        self._total_embedding_latency_ms = 0.0


def get_rag_metrics() -> RAGMetrics:
    return RAGMetrics()
