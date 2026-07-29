"""Observability exporters — export metrics and traces in multiple formats."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from app.observability.models import ExportFormat


class PrometheusExporter:
    """Export metrics in Prometheus text exposition format."""

    def export(self, metrics: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for m in metrics:
            name = m.get("name", "unknown")
            value = m.get("value", 0.0)
            metric_type = m.get("type", "counter")
            labels = m.get("labels", {})
            label_str = ""
            if labels:
                pairs = ",".join(f'{k}="{v}"' for k, v in labels.items())
                label_str = f"{{{pairs}}}"
            prom_type = {
                "counter": "counter",
                "gauge": "gauge",
                "histogram": "gauge",
                "summary": "gauge",
            }.get(metric_type, "gauge")
            lines.append(f"# HELP {name} {name} metric")
            lines.append(f"# TYPE {name} {prom_type}")
            lines.append(f"{name}{label_str} {value}")
        return "\n".join(lines)


class JSONExporter:
    """Export metrics and traces as JSON."""

    def export_metrics(self, metrics: list[dict[str, Any]]) -> str:
        return json.dumps({"metrics": metrics}, indent=2)

    def export_traces(self, traces: list[dict[str, Any]]) -> str:
        return json.dumps({"traces": traces}, indent=2)


class CSVExporter:
    """Export metrics as CSV."""

    def export(self, metrics: list[dict[str, Any]]) -> str:
        if not metrics:
            return ""
        output = io.StringIO()
        fieldnames = ["name", "type", "value", "timestamp"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for m in metrics:
            writer.writerow({
                "name": m.get("name", ""),
                "type": m.get("type", ""),
                "value": m.get("value", 0),
                "timestamp": m.get("timestamp", 0),
            })
        return output.getvalue()


class OpenTelemetryExporter:
    """Export traces in OpenTelemetry-compatible JSON format."""

    def export(self, traces: list[dict[str, Any]]) -> str:
        spans = []
        for t in traces:
            span = {
                "traceId": t.get("trace_id", ""),
                "spanId": t.get("span_id", ""),
                "name": t.get("name", ""),
                "startTimeUnixNano": int(t.get("start_time", 0) * 1e9),
                "endTimeUnixNano": int(t.get("end_time", 0) * 1e9),
                "status": {"code": "STATUS_CODE_OK" if t.get("status") == "ok" else "STATUS_CODE_ERROR"},
                "attributes": [
                    {"key": k, "value": {"stringValue": str(v)}}
                    for k, v in t.get("attributes", {}).items()
                ],
            }
            if t.get("parent_id"):
                span["parentSpanId"] = t["parent_id"]
            spans.append(span)
        return json.dumps({"resourceSpans": [{"spans": spans}]}, indent=2)


class ExportManager:
    """Manages multiple export formats."""

    def __init__(self) -> None:
        self._prometheus = PrometheusExporter()
        self._json = JSONExporter()
        self._csv = CSVExporter()
        self._opentelemetry = OpenTelemetryExporter()

    def export_metrics(self, metrics: list[dict[str, Any]], format: str = "json") -> str:
        if format == "prometheus":
            return self._prometheus.export(metrics)
        elif format == "csv":
            return self._csv.export(metrics)
        else:
            return self._json.export_metrics(metrics)

    def export_traces(self, traces: list[dict[str, Any]], format: str = "json") -> str:
        if format == "opentelemetry":
            return self._opentelemetry.export(traces)
        else:
            return self._json.export_traces(traces)
