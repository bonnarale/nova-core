from __future__ import annotations

import uuid
from datetime import datetime, timezone


class RoadmapManager:
    def __init__(self) -> None:
        self._roadmaps: dict[str, dict] = {}

    def create_roadmap(
        self, objective_text: str, duration_years: int = 1
    ) -> dict:
        roadmap_id = str(uuid.uuid4())
        phases = self._generate_phases(objective_text, duration_years)
        roadmap = {
            "id": roadmap_id,
            "objective": objective_text,
            "duration_years": duration_years,
            "phases": phases,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._roadmaps[roadmap_id] = roadmap
        return roadmap

    def get_roadmap(self, roadmap_id: str) -> dict | None:
        return self._roadmaps.get(roadmap_id)

    def update_roadmap(self, roadmap_id: str, **kwargs: object) -> dict | None:
        roadmap = self._roadmaps.get(roadmap_id)
        if roadmap is None:
            return None
        roadmap.update(kwargs)
        roadmap["updated_at"] = datetime.now(timezone.utc).isoformat()
        return roadmap

    def list_roadmaps(self) -> list[dict]:
        return list(self._roadmaps.values())

    def add_phase(
        self,
        roadmap_id: str,
        title: str,
        description: str = "",
        duration_months: int = 3,
    ) -> dict | None:
        roadmap = self._roadmaps.get(roadmap_id)
        if roadmap is None:
            return None
        phase = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": description,
            "duration_months": duration_months,
            "status": "pending",
            "milestones": [],
        }
        roadmap["phases"].append(phase)
        roadmap["updated_at"] = datetime.now(timezone.utc).isoformat()
        return phase

    def complete_phase(self, roadmap_id: str, phase_id: str) -> dict | None:
        roadmap = self._roadmaps.get(roadmap_id)
        if roadmap is None:
            return None
        for phase in roadmap["phases"]:
            if phase["id"] == phase_id:
                phase["status"] = "completed"
                phase["completed_at"] = datetime.now(timezone.utc).isoformat()
                roadmap["updated_at"] = datetime.now(timezone.utc).isoformat()
                return phase
        return None

    def _generate_phases(
        self, objective_text: str, duration_years: int
    ) -> list[dict]:
        total_months = duration_years * 12
        phase_defs = [
            ("Discovery & Research", "Initial analysis and planning", 2),
            ("Foundation", "Core infrastructure and architecture", 3),
            ("Core Development", "Primary feature implementation", max(3, total_months - 8)),
            ("Refinement", "Polish, optimization, and testing", 2),
            ("Deployment & Review", "Launch and post-launch analysis", 1),
        ]

        phases: list[dict] = []
        for title, desc, months in phase_defs:
            if months <= 0:
                continue
            phases.append(
                {
                    "id": str(uuid.uuid4()),
                    "title": title,
                    "description": desc,
                    "duration_months": min(months, total_months),
                    "status": "pending",
                    "milestones": [],
                }
            )
        return phases

    def to_dict(self) -> dict:
        return {"roadmaps": dict(self._roadmaps)}
