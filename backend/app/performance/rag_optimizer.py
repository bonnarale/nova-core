"""RAG retrieval optimization."""

from __future__ import annotations

import threading
from typing import Any


class RAGOptimizer:
    """Optimizes RAG retrieval pipeline."""

    def __init__(self) -> None:
        self._retrievals: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def record_retrieval(self, query_length: int, chunks_retrieved: int, reranked: bool, duration_ms: float) -> None:
        with self._lock:
            self._retrievals.append({
                "query_length": query_length,
                "chunks_retrieved": chunks_retrieved,
                "reranked": reranked,
                "duration_ms": duration_ms,
            })

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            if not self._retrievals:
                return {"total": 0, "avg_ms": 0}
            times = [r["duration_ms"] for r in self._retrievals]
            reranked = sum(1 for r in self._retrievals if r["reranked"])
            return {
                "total": len(self._retrievals),
                "avg_ms": sum(times) / len(times),
                "max_ms": max(times),
                "reratio_ratio": reranked / len(self._retrievals),
                "avg_chunks": sum(r["chunks_retrieved"] for r in self._retrievals) / len(self._retrievals),
            }

    def get_recommendations(self) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        stats = self.get_stats()
        if stats.get("reratio_ratio", 0) < 0.5 and stats.get("total", 0) > 0:
            recs.append({
                "area": "rag_retrieval",
                "severity": "medium",
                "title": "Low reranking utilization",
                "description": "Consider adding cross-encoder reranking to improve retrieval quality.",
                "expected_improvement": "10-25% retrieval quality improvement",
            })
        if stats.get("avg_ms", 0) > 200 and stats.get("total", 0) > 0:
            recs.append({
                "area": "rag_retrieval",
                "severity": "high",
                "title": "High RAG pipeline latency",
                "description": f"Average RAG latency is {stats['avg_ms']:.1f}ms. Consider caching and early retrieval.",
                "expected_improvement": "20-40% pipeline speedup",
            })
        return recs

    def optimize(self, target: str = "all") -> dict[str, Any]:
        return {"optimized": True, "target": target, "recommendations": self.get_recommendations(), "stats": self.get_stats()}
