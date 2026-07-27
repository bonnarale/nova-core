"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Spinner } from "@/components/ui";
import { PageHeader, StatBar } from "@/components/dashboard";

interface ScalingHealth {
  status: string;
  current_instances: number;
  max_instances: number;
  cpu_percent: number;
  memory_percent: number;
}

export default function ScalingPage() {
  const { data, loading } = useApi<ScalingHealth>("/api/v1/scaling/health");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader title="Scaling" description="Auto-scaling and resource management" action={<Button>Scale Up</Button>} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <Card title="Current Resources">
          <div className="space-y-3">
            <StatBar label="CPU" value={data?.cpu_percent || 0} max={100} color={(data?.cpu_percent || 0) > 80 ? "bg-red-500" : "bg-indigo-500"} />
            <StatBar label="Memory" value={data?.memory_percent || 0} max={100} color={(data?.memory_percent || 0) > 80 ? "bg-red-500" : "bg-indigo-500"} />
          </div>
        </Card>
        <Card title="Scaling Config">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-gray-400"><span>Status</span><span className="text-gray-200">{data?.status || "unknown"}</span></div>
            <div className="flex justify-between text-gray-400"><span>Instances</span><span className="text-gray-200">{data?.current_instances || 0} / {data?.max_instances || 0}</span></div>
          </div>
        </Card>
      </div>
    </div>
  );
}
