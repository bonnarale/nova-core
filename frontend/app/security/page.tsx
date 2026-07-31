"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Spinner, StatusBadge } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface SecurityItem {
  id: string;
  type: string;
  title: string;
  severity: string;
  status: string;
  description: string;
  detected_at: string;
}

interface SecurityStatistics {
  active_sessions: number;
  failed_logins: number;
  security_score: string;
}

export default function SecurityPage() {
  const { data: items, loading } = useApi<SecurityItem[]>("/api/v1/security/audit");
  const { data: stats } = useApi<SecurityStatistics>("/api/v1/security/statistics");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader title="Security" description="Security audit and compliance" action={<Button>Run Audit</Button>} />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card title="Active Sessions"><div className="text-3xl font-bold text-gray-200">{stats?.active_sessions ?? 0}</div></Card>
        <Card title="Failed Logins (24h)"><div className="text-3xl font-bold text-gray-200">{stats?.failed_logins ?? 0}</div></Card>
        <Card title="Security Score"><div className="text-3xl font-bold text-green-400">{stats?.security_score ?? "-"}</div></Card>
      </div>
      <Card title="Audit Log">
        <div className="space-y-2">
          {(items || []).map((item) => (
            <div key={item.id} className="flex items-center gap-3 p-3 bg-gray-900/50 rounded-lg">
              <Badge variant={item.severity === "critical" ? "error" : item.severity === "high" ? "error" : item.severity === "medium" ? "warning" : "default"}>{item.severity}</Badge>
              <StatusBadge status={item.status} />
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-300">{item.title}</div>
                <div className="text-xs text-gray-500">{item.description}</div>
              </div>
              <span className="text-xs text-gray-500">{new Date(item.detected_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
