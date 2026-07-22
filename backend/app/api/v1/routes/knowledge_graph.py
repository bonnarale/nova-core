"""Knowledge Graph API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.knowledge_graph.schemas import (
    EntityCreate,
    EntityListResponse,
    EntityResponse,
    EntityUpdate,
    ExtractRequest,
    ExtractResponse,
    GraphQueryRequest,
    MergeRequest,
    MergeResponse,
    NeighborhoodResponse,
    PathResponse,
    RelationshipCreate,
    RelationshipListResponse,
    RelationshipResponse,
    RelationshipUpdate,
    SearchQuery,
    ValidationResponse,
)

router = APIRouter(prefix="/knowledge-graph", tags=["Knowledge Graph"])


def _get_engine(request: Request):
    engine = request.app.state.knowledge_graph_engine
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge Graph engine not available",
        )
    return engine


# ── Entity CRUD ───────────────────────────────────────────────────


@router.post("/entities", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
async def create_entity(body: EntityCreate, request: Request):
    engine = _get_engine(request)
    entity = await engine.create_entity(
        entity_type=body.type,
        name=body.name,
        description=body.description,
        aliases=body.aliases,
        tags=body.tags,
        properties=body.properties,
        source=body.source,
        confidence=body.confidence,
    )
    return EntityResponse(**entity.to_dict())


@router.get("/entities", response_model=EntityListResponse)
async def list_entities(
    request: Request,
    entity_type: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
):
    engine = _get_engine(request)
    tags = [tag] if tag else None
    entities = await engine.list_entities(
        entity_type=entity_type, tags=tags, limit=limit, offset=offset,
    )
    total = await engine.count_entities(entity_type=entity_type)
    return EntityListResponse(
        entities=[EntityResponse(**e.to_dict()) for e in entities],
        total=total,
    )


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(entity_id: str, request: Request):
    engine = _get_engine(request)
    entity = await engine.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return EntityResponse(**entity.to_dict())


@router.put("/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(entity_id: str, body: EntityUpdate, request: Request):
    engine = _get_engine(request)
    entity = await engine.update_entity(
        entity_id=entity_id,
        name=body.name,
        description=body.description,
        aliases=body.aliases,
        tags=body.tags,
        properties=body.properties,
        confidence=body.confidence,
    )
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return EntityResponse(**entity.to_dict())


@router.delete("/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entity(entity_id: str, request: Request):
    engine = _get_engine(request)
    deleted = await engine.delete_entity(entity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entity not found")


# ── Relationship CRUD ─────────────────────────────────────────────


@router.post("/relationships", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
async def create_relationship(body: RelationshipCreate, request: Request):
    engine = _get_engine(request)
    rel = await engine.create_relationship(
        source_id=body.source_id,
        target_id=body.target_id,
        rel_type=body.type,
        properties=body.properties,
        weight=body.weight,
        source=body.source,
        confidence=body.confidence,
    )
    if not rel:
        raise HTTPException(status_code=400, detail="Source or target entity not found")
    return RelationshipResponse(**rel.to_dict())


@router.get("/relationships", response_model=RelationshipListResponse)
async def list_relationships(
    request: Request,
    source_id: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    rel_type: str | None = Query(default=None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
):
    engine = _get_engine(request)
    rels = await engine.list_relationships(
        source_id=source_id, target_id=target_id,
        rel_type=rel_type, limit=limit, offset=offset,
    )
    return RelationshipListResponse(
        relationships=[RelationshipResponse(**r.to_dict()) for r in rels],
        total=len(rels),
    )


@router.get("/relationships/{rel_id}", response_model=RelationshipResponse)
async def get_relationship(rel_id: str, request: Request):
    engine = _get_engine(request)
    rel = await engine.get_relationship(rel_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return RelationshipResponse(**rel.to_dict())


@router.delete("/relationships/{rel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_relationship(rel_id: str, request: Request):
    engine = _get_engine(request)
    deleted = await engine.delete_relationship(rel_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Relationship not found")


# ── Entity Relationships ──────────────────────────────────────────


@router.get("/entities/{entity_id}/relationships", response_model=RelationshipListResponse)
async def get_entity_relationships(
    entity_id: str,
    request: Request,
    direction: str = Query(default="both", pattern="^(outgoing|incoming|both)$"),
):
    engine = _get_engine(request)
    rels = await engine.get_entity_relationships(entity_id, direction=direction)
    return RelationshipListResponse(
        relationships=[RelationshipResponse(**r.to_dict()) for r in rels],
        total=len(rels),
    )


# ── Graph Queries ─────────────────────────────────────────────────


@router.post("/query/neighborhood", response_model=NeighborhoodResponse)
async def query_neighborhood(body: GraphQueryRequest, request: Request):
    engine = _get_engine(request)
    neighborhood = await engine.find_neighborhood(
        entity_id=body.entity_id,
        depth=body.max_depth,
        max_entities=body.limit,
    )
    return NeighborhoodResponse(
        center=EntityResponse(**neighborhood.center.to_dict()) if neighborhood.center else None,
        entities=[EntityResponse(**e.to_dict()) for e in neighborhood.entities],
        relationships=[RelationshipResponse(**r.to_dict()) for r in neighborhood.relationships],
        depth=neighborhood.depth,
    )


@router.post("/query/shortest-path", response_model=PathResponse)
async def query_shortest_path(
    request: Request,
    source_id: str = Query(...),
    target_id: str = Query(...),
    max_depth: int = Query(default=5, le=10),
):
    engine = _get_engine(request)
    path = await engine.find_shortest_path(source_id, target_id, max_depth)
    if not path:
        raise HTTPException(status_code=404, detail="No path found between entities")
    return PathResponse(
        nodes=[EntityResponse(**n.to_dict()) for n in path.nodes],
        edges=[RelationshipResponse(**e.to_dict()) for e in path.edges],
        total_cost=path.total_cost,
    )


@router.post("/query/connected", response_model=EntityListResponse)
async def query_connected(body: GraphQueryRequest, request: Request):
    engine = _get_engine(request)
    entities = await engine.find_connected_entities(
        entity_id=body.entity_id,
        relationship_types=body.relationship_types,
        direction=body.direction,
        max_depth=body.max_depth,
        limit=body.limit,
    )
    return EntityListResponse(
        entities=[EntityResponse(**e.to_dict()) for e in entities],
        total=len(entities),
    )


# ── Search ────────────────────────────────────────────────────────


@router.post("/search", response_model=EntityListResponse)
async def search_graph(body: SearchQuery, request: Request):
    engine = _get_engine(request)
    entities = await engine.search(
        query=body.query,
        entity_types=body.entity_types,
        limit=body.limit,
        offset=body.offset,
    )
    return EntityListResponse(
        entities=[EntityResponse(**e.to_dict()) for e in entities],
        total=len(entities),
    )


# ── Extraction ────────────────────────────────────────────────────


@router.post("/extract", response_model=ExtractResponse)
async def extract_from_text(body: ExtractRequest, request: Request):
    engine = _get_engine(request)
    result = await engine.extract_from_text(text=body.text, source=body.source)
    return ExtractResponse(
        entities=[EntityResponse(**e.to_dict()) for e in result["entities"]],
        relationships=[RelationshipResponse(**r.to_dict()) for r in result["relationships"]],
    )


# ── Merge ─────────────────────────────────────────────────────────


@router.post("/merge", response_model=MergeResponse)
async def merge_entities(body: MergeRequest, request: Request):
    engine = _get_engine(request)
    result = await engine.merge_entities(
        entity_ids=body.entity_ids,
        canonical_id=body.canonical_id or None,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Merge requires at least 2 valid entities")
    return MergeResponse(
        kept_id=result.kept_id,
        merged_ids=result.merged_ids,
        changes=result.changes,
    )


# ── Validation ────────────────────────────────────────────────────


@router.get("/validate", response_model=ValidationResponse)
async def validate_graph(request: Request):
    engine = _get_engine(request)
    result = await engine.validate()
    return ValidationResponse(
        is_valid=result.is_valid,
        issues=result.issues,
        warnings=result.warnings,
    )


# ── Registry ──────────────────────────────────────────────────────


@router.get("/types")
async def list_types(request: Request):
    engine = _get_engine(request)
    return await engine.get_registries()
