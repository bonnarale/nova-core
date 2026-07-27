"""Observability API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.observability.schemas import (
    AlertsResponse,
    CSVExportResponse,
    DiagnosticsResponse,
    HealthResponse,
    JSONExportResponse,
    LivenessResponse,
    LogsResponse,
    MetricsResponse,
    PrometheusResponse,
    ReadinessResponse,
    StatisticsResponse,
    TracesResponse,
)

router = APIRouter(prefix="/observability", tags=["Observability"])


def _get_engine(request: Request):
    engine = request.app.state.observability_engine
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Observability engine not available",
        )
    return engine


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    engine = _get_engine(request)
    data = await engine.check_health()
    return HealthResponse(
        status=data.get("status", "ok"),
        lifecycle_state=data.get("lifecycle_state", ""),
        uptime_seconds=data.get("uptime_seconds", 0.0),
        checks=[data.get("checks", {})],
    )


@router.get("/readiness", response_model=ReadinessResponse)
async def readiness(request: Request):
    engine = _get_engine(request)
    data = await engine.check_readiness()
    return ReadinessResponse(
        status=data.get("status", "ok"),
        ready=data.get("ready", True),
        dependencies=data.get("checks", {}),
    )


@router.get("/liveness", response_model=LivenessResponse)
async def liveness(request: Request):
    engine = _get_engine(request)
    data = await engine.check_liveness()
    return LivenessResponse(
        status=data.get("status", "ok"),
        alive=data.get("alive", True),
        uptime_seconds=data.get("uptime_seconds", 0.0),
    )


@router.get("/metrics", response_model=MetricsResponse)
async def metrics(request: Request):
    engine = _get_engine(request)
    data = await engine.get_metrics()
    return MetricsResponse(
        metrics=data.get("counters", []) if isinstance(data.get("counters"), list) else [],
        total=data.get("total_metric_points", 0),
    )


@router.get("/traces", response_model=TracesResponse)
async def traces(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
):
    engine = _get_engine(request)
    data = await engine.get_traces(limit=limit)
    return TracesResponse(
        traces=data.get("traces", []),
        total=data.get("total", 0),
    )


@router.get("/logs", response_model=LogsResponse)
async def logs(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
    severity: str | None = Query(default=None),
):
    engine = _get_engine(request)
    data = await engine.get_logs(limit=limit)
    log_list = data.get("logs", [])
    if severity:
        log_list = [l for l in log_list if l.get("severity") == severity]
    return LogsResponse(logs=log_list, total=len(log_list))


@router.get("/diagnostics", response_model=DiagnosticsResponse)
async def diagnostics(request: Request):
    engine = _get_engine(request)
    data = await engine.get_diagnostics()
    return DiagnosticsResponse(
        dependencies=data.get("dependencies", {}),
        configuration=data.get("configuration", {}),
        runtime=data.get("runtime", {}),
    )


@router.get("/alerts", response_model=AlertsResponse)
async def alerts(
    request: Request,
    state: str | None = Query(default=None),
):
    engine = _get_engine(request)
    alert_list = engine.get_alerts(state)
    rule_list = engine.get_alert_rules()
    return AlertsResponse(
        alerts=alert_list,
        rules=rule_list,
        total_alerts=len(alert_list),
    )


@router.get("/statistics", response_model=StatisticsResponse)
async def statistics(request: Request):
    engine = _get_engine(request)
    data = await engine.get_statistics()
    return StatisticsResponse(
        total_metrics=data.get("total_metrics", 0),
        total_spans=data.get("total_spans", 0),
        total_logs=data.get("total_logs", 0),
        total_alerts=data.get("total_alerts", 0),
        total_rules=data.get("total_rules", 0),
        uptime_seconds=data.get("uptime_seconds", 0.0),
        lifecycle_state=data.get("lifecycle_state", ""),
    )


@router.get("/export/prometheus", response_model=PrometheusResponse)
async def export_prometheus(request: Request):
    engine = _get_engine(request)
    content = engine.export_metrics("prometheus")
    return PrometheusResponse(content=content)


@router.get("/export/json", response_model=JSONExportResponse)
async def export_json(request: Request):
    engine = _get_engine(request)
    import json
    content = engine.export_metrics("json")
    try:
        data = json.loads(content)
    except Exception:
        data = {}
    return JSONExportResponse(data=data)


@router.get("/export/csv", response_model=CSVExportResponse)
async def export_csv(request: Request):
    engine = _get_engine(request)
    content = engine.export_metrics("csv")
    return CSVExportResponse(content=content)
