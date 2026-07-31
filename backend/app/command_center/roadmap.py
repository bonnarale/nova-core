from __future__ import annotations

from .schemas import Roadmap, RoadmapPhase


class RoadmapManager:
    def __init__(self) -> None:
        self.roadmaps: dict[str, Roadmap] = {}

    def create(
        self,
        name: str,
        description: str = "",
        duration_years: int = 1,
        start_year: int = 0,
        end_year: int = 0,
    ) -> Roadmap:
        if start_year and end_year:
            duration_years = max(1, end_year - start_year)
        elif start_year and not end_year:
            end_year = start_year + duration_years
        elif end_year and not start_year:
            start_year = end_year - duration_years
        roadmap = Roadmap(
            name=name,
            description=description,
            start_year=start_year,
            end_year=end_year,
            duration_years=duration_years,
            phases=self._generate_phases(name, duration_years),
        )
        self.roadmaps[roadmap.id] = roadmap
        return roadmap

    def update(self, roadmap_id: str, **kwargs: object) -> Roadmap | None:
        roadmap = self.roadmaps.get(roadmap_id)
        if roadmap is None:
            return None
        for key, value in kwargs.items():
            if hasattr(roadmap, key):
                setattr(roadmap, key, value)
        return roadmap

    def get(self, roadmap_id: str) -> Roadmap | None:
        return self.roadmaps.get(roadmap_id)

    def list_all(self, status: str | None = None) -> list[Roadmap]:
        roadmaps = list(self.roadmaps.values())
        if status:
            roadmaps = [r for r in roadmaps if r.status == status]
        return roadmaps

    def add_phase(self, roadmap_id: str, phase: dict) -> RoadmapPhase | None:
        roadmap = self.roadmaps.get(roadmap_id)
        if roadmap is None:
            return None
        roadmap_phase = RoadmapPhase(
            title=phase.get("title", ""),
            description=phase.get("description", ""),
            order=phase.get("order", len(roadmap.phases) + 1),
            duration_months=phase.get("duration_months", 3),
        )
        roadmap.phases.append(roadmap_phase.__dict__)
        return roadmap_phase

    def complete_phase(self, roadmap_id: str, phase_id: str) -> bool:
        roadmap = self.roadmaps.get(roadmap_id)
        if roadmap is None:
            return False
        for phase in roadmap.phases:
            if phase.get("id") == phase_id:
                phase["status"] = "completed"
                return True
        return False

    def _generate_phases(self, name: str, duration_years: int) -> list[dict]:
        total_months = duration_years * 12
        default_phases = [
            {"title": "Foundation", "duration_months": 3},
            {"title": "Core Development", "duration_months": 4},
            {"title": "Advanced Features", "duration_months": 3},
            {"title": "Polish & Launch", "duration_months": 2},
        ]
        if duration_years > 1:
            default_phases = [
                {"title": "Planning & Research", "duration_months": 6},
                {"title": "Foundation", "duration_months": 6},
                {"title": "Core Development", "duration_months": 12},
                {"title": "Advanced Features", "duration_months": 6},
                {"title": "Testing & QA", "duration_months": 6},
                {"title": "Launch & Optimization", "duration_months": max(6, total_months - 36)},
            ]
        phases: list[dict] = []
        for idx, dp in enumerate(default_phases):
            phase = RoadmapPhase(
                title=dp["title"],
                description=f"{dp['title']} phase of {name}",
                order=idx + 1,
                duration_months=dp["duration_months"],
            )
            phases.append(phase.__dict__)
        return phases

    def to_dict(self) -> dict:
        return {k: v.__dict__ for k, v in self.roadmaps.items()}
