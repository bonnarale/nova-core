"use client";

import React, { useState } from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Input, Spinner, StatusBadge } from "@/components/ui";
import { PageHeader, DataTable } from "@/components/dashboard";

interface ScheduleItem {
  id: string;
  name: string;
  cron: string;
  task_type: string;
  status: string;
  last_run?: string;
  next_run: string;
  enabled: boolean;
}

export default function SchedulerPage() {
  const { data: schedules, loading } = useApi<ScheduleItem[]>("/api/v1/scheduler/jobs");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader title="Scheduler" description="Manage scheduled tasks and automation" action={<Button>Create Schedule</Button>} />
      <Card>
        <div className="space-y-3">
          {(schedules || []).map((s) => (
            <div key={s.id} className="flex items-center justify-between p-3 bg-gray-900/50 rounded-lg">
              <div className="flex items-center gap-4">
                <StatusBadge status={s.enabled ? "active" : "degraded"} />
                <div>
                  <div className="font-medium text-gray-200">{s.name}</div>
                  <div className="text-xs text-gray-500 font-mono">{s.cron}</div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <Badge variant="info">{s.task_type}</Badge>
                {s.last_run && <span className="text-xs text-gray-500">Last: {new Date(s.last_run).toLocaleString()}</span>}
                <span className="text-xs text-gray-400">Next: {new Date(s.next_run).toLocaleString()}</span>
                <Button size="sm" variant="ghost">{s.enabled ? "Pause" : "Resume"}</Button>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
