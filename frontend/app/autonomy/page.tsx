"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Badge, Spinner, StatusBadge } from "@/components/ui";
import { PageHeader, StatBar } from "@/components/dashboard";

interface AutonomyData {
  level: string;
  capabilities: string[];
  completed_tasks: number;
  failed_tasks: number;
}

export default function AutonomyPage() {
  const { data, loading } = useApi<AutonomyData>("/api/v1/autonomy/status");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader title="Autonomy" description="Agent autonomy configuration" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card title="Autonomy Settings">
          <div className="space-y-3">
            <div className="flex justify-between"><span className="text-sm text-gray-400">Level</span><Badge variant="info">{data?.level || "supervised"}</Badge></div>
            {(data?.capabilities || []).map((cap) => (
              <div key={cap} className="flex justify-between items-center">
                <span className="text-sm text-gray-400 capitalize">{cap.replace(/_/g, " ")}</span>
                <StatusBadge status="active" />
              </div>
            ))}
          </div>
        </Card>
        <Card title="Performance">
          <div className="space-y-3">
            <StatBar label="Completed" value={data?.completed_tasks || 0} color="bg-green-500" />
            <StatBar label="Failed" value={data?.failed_tasks || 0} color="bg-red-500" />
          </div>
        </Card>
      </div>
    </div>
  );
}
