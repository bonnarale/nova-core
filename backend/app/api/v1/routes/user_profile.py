"""User profile system API routes."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException
from app.profile.profile import ProfileManager
from app.profile.preferences import PreferencesManager
from app.profile.projects import ProjectsManager
from app.profile.objectives import ObjectivesManager
from app.profile.priorities import PrioritiesManager
from app.profile.history import HistoryManager
from app.profile.roadmap import RoadmapManager

router = APIRouter(prefix="/profile", tags=["profile"])
_pm = None
_pref = None
_proj = None
_obj = None
_pri = None
_hist = None
_rm = None

def _get():
    global _pm, _pref, _proj, _obj, _pri, _hist, _rm
    if _pm is None:
        _pm = ProfileManager()
        _pref = PreferencesManager()
        _proj = ProjectsManager()
        _obj = ObjectivesManager()
        _pri = PrioritiesManager()
        _hist = HistoryManager()
        _rm = RoadmapManager()
    return {"profile": _pm, "preferences": _pref, "projects": _proj, "objectives": _obj, "priorities": _pri, "history": _hist, "roadmap": _rm}

@router.get("/status")
async def get_status() -> dict[str, Any]:
    m = _get()
    return {"profiles": len(m["profile"].list_profiles()), "projects": len(m["proj"].list_projects()), "objectives": len(m["obj"].list_objectives()), "roadmaps": len(m["rm"].list_roadmaps())}

@router.post("/users")
async def create_user(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["profile"].create_profile(data.get("user_id", ""), data.get("username", ""), data.get("email", ""), data.get("display_name", ""), data.get("role", "user"))

@router.get("/users/{user_id}")
async def get_user(user_id: str) -> dict[str, Any]:
    result = _get()["profile"].get_profile(user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result

@router.put("/users/{user_id}")
async def update_user(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    result = _get()["profile"].update_profile(user_id, **data)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result

@router.get("/users/{user_id}/preferences")
async def get_preferences(user_id: str) -> list[dict[str, Any]]:
    return _get()["preferences"].get_all_preferences(user_id)

@router.post("/users/{user_id}/preferences")
async def set_preference(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return _get()["preferences"].set_preference(user_id, data.get("key", ""), data.get("value"), data.get("category", "general"))

@router.get("/projects")
async def get_projects() -> list[dict[str, Any]]:
    return _get()["projects"].list_projects()

@router.post("/projects")
async def create_project(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["projects"].create_project(data.get("name", ""), data.get("description", ""), data.get("owner_id"), data.get("priority", 3), data.get("tags"))

@router.get("/objectives")
async def get_objectives() -> list[dict[str, Any]]:
    return _get()["objectives"].list_objectives()

@router.post("/objectives")
async def create_objective(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["objectives"].create_objective(data.get("title", ""), data.get("description", ""), data.get("project_id"), data.get("priority", 3))

@router.get("/priorities")
async def get_priorities() -> list[dict[str, Any]]:
    return _get()["priorities"].list_priorities()

@router.post("/priorities")
async def create_priority(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["priorities"].create_priority(data.get("name", ""), data.get("level", 3), data.get("description", ""))

@router.get("/history")
async def get_history(limit: int = 50) -> list[dict[str, Any]]:
    return _get()["history"].get_history(limit=limit)

@router.get("/roadmaps")
async def get_roadmaps() -> list[dict[str, Any]]:
    return _get()["roadmap"].list_roadmaps()

@router.post("/roadmaps")
async def create_roadmap(data: dict[str, Any]) -> dict[str, Any]:
    return _get()["roadmap"].create_roadmap(data.get("name", ""), data.get("description", ""), data.get("phases"))
