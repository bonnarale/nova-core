"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Badge, Spinner, StatusBadge } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface Job {
  id: string;
  name: string;
  status: string;
  scheduled_at: string;
  duration_ms?: number;
  agent?: string;
}

export default function ExecutionPage() {
  const { data: jobs, loading } = useApi<Job[]>("/api/v1/scheduler/jobs");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader title="Execution" description="Task execution history" />
      <div className="space-y-2">
        {(jobs || []).map((job) => (
          <Card key={job.id} className="p-3">
            <div className="flex items-center gap-4">
              <StatusBadge status={job.status} />
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-300">{job.name}</div>
                {job.agent && <div className="text-xs text-gray-500">Agent: {job.agent}</div>}
              </div>
              {job.duration_ms && <Badge>{job.duration_ms}ms</Badge>}
              <span className="text-xs text-gray-500">{new Date(job.scheduled_at).toLocaleString()}</span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
