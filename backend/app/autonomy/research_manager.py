from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .schemas import ResearchQuery


class ResearchManager:
    def __init__(self) -> None:
        self._queries: dict[str, ResearchQuery] = {}

    def submit_research(self, query: str, depth: str = "standard") -> dict:
        rq = ResearchQuery(query=query, depth=depth)
        self._queries[rq.id] = rq
        return self._query_to_dict(rq)

    def get_research(self, research_id: str) -> dict | None:
        rq = self._queries.get(research_id)
        if rq is None:
            return None
        return self._query_to_dict(rq)

    def complete_research(
        self,
        research_id: str,
        findings: list[dict],
        summary: str,
        confidence: float = 0.8,
    ) -> dict | None:
        rq = self._queries.get(research_id)
        if rq is None:
            return None
        rq.findings = findings
        rq.summary = summary
        rq.confidence = confidence
        return self._query_to_dict(rq)

    def list_research(self, limit: int = 50) -> list[dict]:
        queries = list(self._queries.values())
        return [self._query_to_dict(q) for q in queries[:limit]]

    def _query_to_dict(self, rq: ResearchQuery) -> dict:
        return {
            "id": rq.id,
            "query": rq.query,
            "depth": rq.depth,
            "findings": rq.findings,
            "summary": rq.summary,
            "confidence": rq.confidence,
            "created_at": rq.created_at,
        }

    def to_dict(self) -> dict:
        return {
            "queries": {
                k: self._query_to_dict(v) for k, v in self._queries.items()
            }
        }
