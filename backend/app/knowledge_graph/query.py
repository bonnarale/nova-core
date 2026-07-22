"""Graph traversal — neighborhood, shortest path, and connectivity queries."""

from __future__ import annotations

import logging
from collections import deque
from typing import Any

from app.knowledge_graph.base import GraphTraverser
from app.knowledge_graph.models import (
    Entity,
    GraphPath,
    Neighborhood,
    Relationship,
    RelationshipStatus,
    RelationshipType,
)

logger = logging.getLogger(__name__)


class DefaultGraphTraverser(GraphTraverser):
    """BFS-based graph traverser for neighborhood and path queries."""

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._outgoing: dict[str, list[Relationship]] = {}
        self._incoming: dict[str, list[Relationship]] = {}

    def set_data(
        self,
        entities: dict[str, Entity],
        outgoing: dict[str, list[Relationship]],
        incoming: dict[str, list[Relationship]],
    ) -> None:
        self._entities = entities
        self._outgoing = outgoing
        self._incoming = incoming

    async def find_neighborhood(
        self, entity_id: str, depth: int = 1, max_entities: int = 100
    ) -> Neighborhood:
        center = self._entities.get(entity_id)
        if not center:
            return Neighborhood(depth=depth)

        visited_entities: set[str] = {entity_id}
        visited_rels: set[str] = set()
        result_entities: list[Entity] = []
        result_rels: list[Relationship] = []
        queue: deque[tuple[str, int]] = deque([(entity_id, 0)])

        while queue and len(result_entities) < max_entities:
            current_id, current_depth = queue.popleft()

            for rel in self._outgoing.get(current_id, []):
                if rel.status == RelationshipStatus.DELETED or rel.status == RelationshipStatus.EXPIRED:
                    continue
                if rel.id in visited_rels:
                    continue
                visited_rels.add(rel.id)
                result_rels.append(rel)

                if rel.target_id not in visited_entities and current_depth < depth:
                    visited_entities.add(rel.target_id)
                    target = self._entities.get(rel.target_id)
                    if target and target.status.value != "DELETED":
                        result_entities.append(target)
                        if current_depth + 1 < depth:
                            queue.append((rel.target_id, current_depth + 1))

            for rel in self._incoming.get(current_id, []):
                if rel.status == RelationshipStatus.DELETED or rel.status == RelationshipStatus.EXPIRED:
                    continue
                if rel.id in visited_rels:
                    continue
                visited_rels.add(rel.id)
                result_rels.append(rel)

                if rel.source_id not in visited_entities and current_depth < depth:
                    visited_entities.add(rel.source_id)
                    source = self._entities.get(rel.source_id)
                    if source and source.status.value != "DELETED":
                        result_entities.append(source)
                        if current_depth + 1 < depth:
                            queue.append((rel.source_id, current_depth + 1))

        return Neighborhood(
            center=center,
            entities=result_entities[:max_entities],
            relationships=result_rels,
            depth=depth,
        )

    async def find_shortest_path(
        self, source_id: str, target_id: str, max_depth: int = 5
    ) -> GraphPath | None:
        if source_id not in self._entities or target_id not in self._entities:
            return None
        if source_id == target_id:
            return GraphPath(
                nodes=[self._entities[source_id]], edges=[], total_cost=0.0
            )

        visited: set[str] = {source_id}
        parent: dict[str, tuple[str | None, Relationship | None]] = {source_id: (None, None)}
        queue: deque[str] = deque([source_id])

        while queue:
            current = queue.popleft()
            depth = self._path_depth(parent, current)
            if depth >= max_depth:
                continue

            for rel in self._outgoing.get(current, []):
                if rel.status == RelationshipStatus.DELETED or rel.status == RelationshipStatus.EXPIRED:
                    continue
                if rel.target_id not in visited:
                    visited.add(rel.target_id)
                    parent[rel.target_id] = (current, rel)
                    if rel.target_id == target_id:
                        return self._reconstruct_path(parent, target_id)
                    queue.append(rel.target_id)

            for rel in self._incoming.get(current, []):
                if rel.status == RelationshipStatus.DELETED or rel.status == RelationshipStatus.EXPIRED:
                    continue
                if rel.source_id not in visited:
                    visited.add(rel.source_id)
                    parent[rel.source_id] = (current, rel)
                    if rel.source_id == target_id:
                        return self._reconstruct_path(parent, target_id)
                    queue.append(rel.source_id)

        return None

    async def find_connected_entities(
        self,
        entity_id: str,
        relationship_types: list[RelationshipType] | None = None,
        direction: str = "both",
        max_depth: int = 2,
        limit: int = 100,
    ) -> list[Entity]:
        if entity_id not in self._entities:
            return []

        visited: set[str] = {entity_id}
        result: list[Entity] = []
        queue: deque[tuple[str, int]] = deque([(entity_id, 0)])

        while queue and len(result) < limit:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            rels: list[Relationship] = []
            if direction in ("outgoing", "both"):
                rels.extend(self._outgoing.get(current_id, []))
            if direction in ("incoming", "both"):
                rels.extend(self._incoming.get(current_id, []))

            for rel in rels:
                if rel.status == RelationshipStatus.DELETED or rel.status == RelationshipStatus.EXPIRED:
                    continue
                if relationship_types and rel.type not in relationship_types:
                    continue

                neighbor_id = rel.target_id if rel.source_id == current_id else rel.source_id
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    neighbor = self._entities.get(neighbor_id)
                    if neighbor and neighbor.status.value != "DELETED":
                        result.append(neighbor)
                        if len(result) >= limit:
                            break
                        queue.append((neighbor_id, depth + 1))

        return result[:limit]

    def _path_depth(
        self, parent: dict[str, tuple[str | None, Relationship | None]], node: str
    ) -> int:
        d = 0
        while parent.get(node, (None, None))[0] is not None:
            node = parent[node][0]
            d += 1
        return d

    def _reconstruct_path(
        self, parent: dict[str, tuple[str | None, Relationship | None]], target: str
    ) -> GraphPath:
        nodes: list[Entity] = []
        edges: list[Relationship] = []
        current = target
        while parent.get(current, (None, None))[0] is not None:
            prev, rel = parent[current]
            if prev is not None:
                nodes.append(self._entities.get(current))
                if rel is not None:
                    edges.append(rel)
                current = prev
            else:
                break
        nodes.append(self._entities.get(current, self._entities.get(target)))
        nodes.reverse()
        edges.reverse()
        total_cost = sum(1.0 - (e.weight or 0.5) for e in edges)
        return GraphPath(
            nodes=[n for n in nodes if n is not None],
            edges=[e for e in edges if e is not None],
            total_cost=total_cost,
        )
