"""Performance API routes for the Performance Optimization subsystem."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["performance"])

_engine: Any = None


def set_dependencies(engine: Any = None) -> None:
    global _engine
    _engine = engine


@router.get("/performance/health", summary="Performance health check")
async def performance_health() -> dict[str, Any]:
    if _engine:
        return {"success": True, "data": _engine.get_health()}
    return {"success": True, "data": {"status": "unknown", "message": "No performance engine"}}


@router.get("/performance/profile", summary="Get profiling sessions")
async def performance_profile() -> dict[str, Any]:
    if _engine:
        active = _engine.profiler.get_active_sessions()
        completed = _engine.profiler.get_completed_sessions()
        return {"success": True, "data": {"active": active, "completed": completed, "total": len(active) + len(completed)}}
    return {"success": True, "data": {"active": [], "completed": [], "total": 0}}


@router.get("/performance/benchmarks", summary="Get benchmark results")
async def performance_benchmarks(category: str | None = None) -> dict[str, Any]:
    if _engine:
        results = _engine.benchmark.get_results(category)
        summary = _engine.benchmark.summary()
        return {"success": True, "data": {"results": results, "summary": summary, "total": len(results)}}
    return {"success": True, "data": {"results": [], "summary": {}, "total": 0}}


@router.get("/performance/diagnostics", summary="Performance diagnostics")
async def performance_diagnostics() -> dict[str, Any]:
    if _engine:
        report = _engine.run_diagnostics()
        return {"success": True, "data": report.to_dict()}
    return {"success": True, "data": {}}


@router.get("/performance/recommendations", summary="Optimization recommendations")
async def performance_recommendations() -> dict[str, Any]:
    if _engine:
        recs = _engine.get_recommendations()
        summary = {"total": len(recs)}
        for r in recs:
            sev = r.get("severity", "low")
            summary[sev] = summary.get(sev, 0) + 1
        return {"success": True, "data": {"recommendations": recs, "total": len(recs), "summary": summary}}
    return {"success": True, "data": {"recommendations": [], "total": 0, "summary": {}}}


@router.get("/performance/metrics", summary="Performance metrics")
async def performance_metrics() -> dict[str, Any]:
    if _engine:
        m = _engine.get_metrics()
        return {"success": True, "data": m.to_dict()}
    return {"success": True, "data": {}}


@router.get("/performance/traces", summary="Performance traces")
async def performance_traces(limit: int = 50) -> dict[str, Any]:
    if _engine:
        traces = _engine.get_traces(limit)
        return {"success": True, "data": {"traces": traces, "total": len(traces)}}
    return {"success": True, "data": {"traces": [], "total": 0}}


@router.post("/performance/profile/start", summary="Start profiling session")
async def performance_profile_start(profile_type: str = "comprehensive", target: str | None = None) -> dict[str, Any]:
    if _engine:
        session_id = _engine.profiler.start_session(profile_type, target)
        return {"success": True, "data": {"session_id": session_id, "state": "collecting"}}
    return {"success": True, "data": {"session_id": None, "state": "idle", "message": "No performance engine"}}


@router.post("/performance/profile/stop", summary="Stop profiling session")
async def performance_profile_stop(session_id: str) -> dict[str, Any]:
    if _engine:
        session = _engine.profiler.stop_session(session_id)
        if session:
            return {"success": True, "data": session.to_dict()}
        return {"success": True, "data": {"error": "Session not found"}}
    return {"success": True, "data": {"error": "No performance engine"}}


@router.post("/performance/benchmark/run", summary="Run benchmark")
async def performance_benchmark_run(category: str = "execution", iterations: int = 100) -> dict[str, Any]:
    if _engine:
        async def noop() -> None:
            pass

        result = await _engine.benchmark.run_async(
            name=f"api_overhead_{category}",
            func=noop,
            category=category,
            iterations=min(iterations, 1000),
        )
        return {"success": True, "data": result.to_dict()}
    return {"success": True, "data": {"category": category, "iterations": iterations, "message": "No performance engine"}}
