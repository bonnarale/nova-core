"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, Badge, Spinner, StatusBadge } from "@/components/ui";
import { MetricCard, PageHeader } from "@/components/dashboard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ToolsData {
  orchestrator: {
    active_orchestrations: number;
    executions_completed: number;
    governor: {
      role: string;
      status: string;
      total_analyses: number;
      total_decisions: number;
    };
  };
  autonomy: {
    level: number;
    capabilities: string[];
    policies: Record<string, unknown>;
  };
  optimization: unknown[];
}

export default function ToolsPage() {
  const [data, setData] = useState<ToolsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/nova-web/tools`);
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
  if (error || !data) return <div className="text-center py-20 text-gray-500">Unable to load tools data{error ? `: ${error}` : ""}</div>;

  return (
    <div>
      <PageHeader title="Tools" description="Orchestration, autonomy, and optimization status" />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <MetricCard title="Active Orchestrations" value={data.orchestrator.active_orchestrations} icon="&#128295;" />
        <MetricCard title="Executions Completed" value={data.orchestrator.executions_completed} icon="&#9989;" />
        <MetricCard title="Governor Analyses" value={data.orchestrator.governor.total_analyses} icon="&#128200;" />
        <MetricCard title="Autonomy Level" value={`${(data.autonomy.level * 100).toFixed(0)}%`} icon="&#9889;" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Governor">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Role</span>
              <span className="text-sm text-gray-200">{data.orchestrator.governor.role}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Status</span>
              <StatusBadge status={data.orchestrator.governor.status === "active" ? "healthy" : "degraded"} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Total Analyses</span>
              <span className="text-sm text-gray-200">{data.orchestrator.governor.total_analyses}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Total Decisions</span>
              <span className="text-sm text-gray-200">{data.orchestrator.governor.total_decisions}</span>
            </div>
          </div>
        </Card>

        <Card title="Autonomy Capabilities">
          {data.autonomy.capabilities.length === 0 ? (
            <div className="text-sm text-gray-500 py-4 text-center">No capabilities registered</div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {data.autonomy.capabilities.map((cap) => (
                <Badge key={cap}>{cap}</Badge>
              ))}
            </div>
          )}
        </Card>
      </div>

      {data.optimization && data.optimization.length > 0 && (
        <Card title={`Optimizations (${data.optimization.length})`} className="mt-4">
          <pre className="text-xs text-gray-400 overflow-x-auto">{JSON.stringify(data.optimization, null, 2)}</pre>
        </Card>
      )}
    </div>
  );
}
