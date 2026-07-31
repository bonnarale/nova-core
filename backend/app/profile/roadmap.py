from __future__ import annotations

from datetime import datetime, timezone

from .schemas import Roadmap, RoadmapPhase


class RoadmapManager:
    def __init__(self) -> None:
        self.roadmaps: dict[str, Roadmap] = {}

    def create_roadmap(
        self,
        name: str,
        description: str = "",
        phases: list[RoadmapPhase] | None = None,
    ) -> dict:
        roadmap = Roadmap(
            name=name,
            description=description,
            phases=phases if phases is not None else [],
        )
        self.roadmaps[roadmap.id] = roadmap
        return roadmap.to_dict()

    def get_roadmap(self, roadmap_id: str) -> dict | None:
        roadmap = self.roadmaps.get(roadmap_id)
        return roadmap.to_dict() if roadmap else None

    def update_roadmap(self, roadmap_id: str, **kwargs) -> dict | None:
        roadmap = self.roadmaps.get(roadmap_id)
        if not roadmap:
            return None
        for key, value in kwargs.items():
            if hasattr(roadmap, key) and key not in ("id", "created_at", "phases"):
                setattr(roadmap, key, value)
        roadmap.updated_at = datetime.now(timezone.utc)
        return roadmap.to_dict()

    def delete_roadmap(self, roadmap_id: str) -> bool:
        if roadmap_id in self.roadmaps:
            del self.roadmaps[roadmap_id]
            return True
        return False

    def list_roadmaps(self, status: str | None = None) -> list[dict]:
        result = list(self.roadmaps.values())
        if status:
            result = [r for r in result if r.status == status]
        return [r.to_dict() for r in result]

    def add_phase(
        self,
        roadmap_id: str,
        title: str,
        description: str = "",
        duration_months: int | None = None,
        order: int | None = None,
    ) -> dict | None:
        roadmap = self.roadmaps.get(roadmap_id)
        if not roadmap:
            return None
        if order is None:
            order = len(roadmap.phases)
        phase = RoadmapPhase(
            title=title,
            description=description,
            duration_months=duration_months,
            order=order,
        )
        roadmap.phases.append(phase)
        roadmap.phases.sort(key=lambda p: p.order)
        roadmap.updated_at = datetime.now(timezone.utc)
        return roadmap.to_dict()

    def update_phase(self, roadmap_id: str, phase_id: str, **kwargs) -> dict | None:
        roadmap = self.roadmaps.get(roadmap_id)
        if not roadmap:
            return None
        for phase in roadmap.phases:
            if phase.id == phase_id:
                for key, value in kwargs.items():
                    if hasattr(phase, key) and key != "id":
                        setattr(phase, key, value)
                roadmap.updated_at = datetime.now(timezone.utc)
                return roadmap.to_dict()
        return None

    def complete_phase(self, roadmap_id: str, phase_id: str) -> dict | None:
        roadmap = self.roadmaps.get(roadmap_id)
        if not roadmap:
            return None
        for phase in roadmap.phases:
            if phase.id == phase_id:
                phase.status = "completed"
                roadmap.updated_at = datetime.now(timezone.utc)
                return roadmap.to_dict()
        return None

    def to_dict(self) -> dict:
        return {rid: r.to_dict() for rid, r in self.roadmaps.items()}
