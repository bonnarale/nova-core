"""Similarity engines — compute similarity between vector embeddings."""

from __future__ import annotations

import math
from typing import Optional

from app.vector_memory.base import SimilarityEngine


def _validate_vectors(a: list[float], b: list[float]) -> None:
    if len(a) != len(b):
        raise ValueError(f"Vector dimension mismatch: {len(a)} vs {len(b)}")


class CosineSimilarity(SimilarityEngine):
    """Cosine similarity — measures the cosine of the angle between vectors."""

    @property
    def name(self) -> str:
        return "cosine"

    def compute(self, a: list[float], b: list[float]) -> float:
        _validate_vectors(a, b)
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def batch_compute(self, query: list[float], candidates: list[list[float]]) -> list[float]:
        return [self.compute(query, c) for c in candidates]


class DotProductSimilarity(SimilarityEngine):
    """Dot product similarity — simple dot product of vectors."""

    @property
    def name(self) -> str:
        return "dot_product"

    def compute(self, a: list[float], b: list[float]) -> float:
        _validate_vectors(a, b)
        return sum(x * y for x, y in zip(a, b))

    def batch_compute(self, query: list[float], candidates: list[list[float]]) -> list[float]:
        return [self.compute(query, c) for c in candidates]


class EuclideanSimilarity(SimilarityEngine):
    """Euclidean similarity — inverse of Euclidean distance (1 / (1 + distance))."""

    @property
    def name(self) -> str:
        return "euclidean"

    def compute(self, a: list[float], b: list[float]) -> float:
        _validate_vectors(a, b)
        dist = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        return 1.0 / (1.0 + dist)

    def batch_compute(self, query: list[float], candidates: list[list[float]]) -> list[float]:
        return [self.compute(query, c) for c in candidates]


def get_similarity_engine(engine_type: str = "cosine", **kwargs: Optional[dict]) -> SimilarityEngine:
    engines = {
        "cosine": CosineSimilarity(),
        "dot_product": DotProductSimilarity(),
        "euclidean": EuclideanSimilarity(),
    }
    engine = engines.get(engine_type)
    if not engine:
        raise ValueError(f"Unknown similarity engine: {engine_type}")
    return engine
