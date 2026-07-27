"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, Spinner, StatusBadge } from "@/components/ui";
import { MetricCard, PageHeader } from "@/components/dashboard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ObservabilityData {
  metrics: {
    counters: Record<string, number>;
    gauges: Record<string, number>;
    histograms: Record<string, unknown>;
  };
  traces: {
    total_spans: number;
    total_traces: number;
    traces: Record<string, unknown>;
  };
  health: {
    phase: string;
    uptime: number;
    events_count: number;
    phase_history: Array<{ phase: string; timestamp: string }>;
  };
}

export default function ObservabilityPage() {
  const [data, setData] = useState<ObservabilityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/nova-web/observability`);
      if (!res.ok) throw new Error(`${res.status}`);
      const result = await res.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;
  if (error || !data) return <div className="text-center py-20 text-gray-500">Unable to load observability data{error ? `: ${error}` : ""}</div>;

  const counterEntries = Object.entries(data.metrics.counters || {});
  const gaugeEntries = Object.entries(data.metrics.gauges || {});
  const uptimeHours = Math.floor(data.health.uptime / 3600);
  const uptimeMinutes = Math.floor((data.health.uptime % 3600) / 60);

  return (
    <div>
      <PageHeader title="Observability" description="System health, metrics, and traces" />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <MetricCard title="Phase" value={data.health.phase} icon="&#9889;" />
        <MetricCard title="Uptime" value={`${uptimeHours}h ${uptimeMinutes}m`} icon="&#128337;" />
        <MetricCard title="Total Spans" value={data.traces.total_spans} icon="&#128200;" />
        <MetricCard title="Total Traces" value={data.traces.total_traces} icon="&#128269;" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <Card title="System Health">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Phase</span>
              <StatusBadge status={data.health.phase === "running" ? "healthy" : "degraded"} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Events</span>
              <span className="text-sm text-gray-200">{data.health.events_count}</span>
            </div>
            {data.health.phase_history.length > 0 && (
              <div className="space-y-1.5 mt-3">
                <span className="text-xs text-gray-500 uppercase">Phase History</span>
                {data.health.phase_history.map((p, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="text-gray-400">{p.phase}</span>
                    <span className="text-gray-600">{new Date(p.timestamp).toLocaleTimeString()}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        <Card title="Metrics">
          {counterEntries.length === 0 && gaugeEntries.length === 0 ? (
            <div className="text-sm text-gray-500 py-4 text-center">No metrics recorded yet</div>
          ) : (
            <div className="space-y-3">
              {counterEntries.map(([key, val]) => (
                <div key={key} className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">{key}</span>
                  <span className="text-gray-200">{val}</span>
                </div>
              ))}
              {gaugeEntries.map(([key, val]) => (
                <div key={key} className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">{key}</span>
                  <span className="text-gray-200">{val}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
