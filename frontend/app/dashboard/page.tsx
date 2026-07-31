"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, StatusBadge, Spinner } from "@/components/ui";
import { HealthGrid, PageHeader } from "@/components/dashboard";

interface HealthData {
  status: string;
  checks: Record<string, boolean>;
}

export default function DashboardPage() {
  const { data, loading, error } = useApi<HealthData>("/api/v1/health");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;
  if (error) return <div className="text-center py-20 text-red-400">Failed to load dashboard: {error}</div>;

  const checks = data?.checks || {};
  const services = Object.entries(checks).map(([name, healthy]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    status: healthy ? "healthy" : "down",
    detail: undefined,
  }));

  return (
    <div>
      <PageHeader title="Dashboard" description="NOVA CORE system overview" />
      {data && (
        <div className="space-y-6">
          <Card title="System Health">
            <div className="flex items-center gap-3 mb-4">
              <StatusBadge status={data.status === "ok" ? "healthy" : "degraded"} />
              <span className="text-sm text-gray-400">Overall status: {data.status}</span>
            </div>
            <HealthGrid items={services} />
          </Card>
        </div>
      )}
    </div>
  );
}
