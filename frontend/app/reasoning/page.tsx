"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Badge, Spinner } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface ReasoningTrace {
  trace_id: string;
  name: string;
  duration_ms: number;
  status: string;
}

export default function ReasoningPage() {
  const { data: traces, loading } = useApi<ReasoningTrace[]>("/api/v1/observability/traces");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader title="Reasoning" description="Chain-of-thought reasoning traces" />
      <div className="space-y-4">
        {(traces || []).map((trace) => (
          <Card key={trace.trace_id}>
            <div className="mb-3">
              <div className="text-sm font-medium text-gray-300 mb-1">{trace.name}</div>
              <div className="flex items-center gap-2">
                <Badge>{trace.duration_ms}ms</Badge>
                <Badge variant={trace.status === "completed" ? "success" : trace.status === "failed" ? "error" : "info"}>{trace.status}</Badge>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
