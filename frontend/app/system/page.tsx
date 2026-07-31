"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Spinner, StatusBadge } from "@/components/ui";
import { PageHeader, StatBar } from "@/components/dashboard";

interface IntegrationStatus {
  status: string;
  integrations: Array<{ name: string; status: string; latency_ms?: number }>;
  memory_usage_mb: number;
  cpu_percent: number;
  disk_usage_percent: number;
}

export default function SystemPage() {
  const { data, loading } = useApi<IntegrationStatus>("/api/v1/integration/status");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader title="System" description="System health and infrastructure" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <Card title="Services">
          <div className="space-y-2">
            {(data?.integrations || []).map((intg) => (
              <div key={intg.name} className="flex items-center justify-between p-2 bg-gray-900/50 rounded">
                <span className="text-sm text-gray-300 capitalize">{intg.name}</span>
                <StatusBadge status={intg.status} />
              </div>
            ))}
          </div>
        </Card>
        <Card title="Resources">
          <div className="space-y-3">
            <StatBar label="CPU" value={data?.cpu_percent || 0} color="bg-indigo-500" />
            <StatBar label="Memory" value={data?.memory_usage_mb || 0} max={4096} color="bg-indigo-500" />
            <div className="mt-2 text-xs text-gray-500 text-right">Overall: {data?.status || "unknown"}</div>
            <StatBar label="Disk" value={data?.disk_usage_percent || 0} color="bg-indigo-500" />
          </div>
        </Card>
      </div>
    </div>
  );
}
