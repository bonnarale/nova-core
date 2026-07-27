"use client";

import React from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Spinner } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface Objective {
  id: string;
  title: string;
  status: string;
  priority: string;
  progress: number;
}

interface AutonomyResponse {
  success: boolean;
  data: Objective[];
}

export default function PlanningPage() {
  const { data: raw, loading } = useApi<AutonomyResponse>("/api/v1/autonomy/objectives");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  const objectives: Objective[] = raw?.data || (Array.isArray(raw) ? raw : []);

  return (
    <div>
      <PageHeader title="Planning" description="Autonomous planning and decomposition" action={<Button>New Plan</Button>} />
      <div className="space-y-4">
        {objectives.length === 0 && (
          <div className="text-center text-gray-500 py-12">No objectives yet. Create one from the chat or dashboard.</div>
        )}
        {objectives.map((obj) => (
          <Card key={obj.id}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-200">{obj.title}</h3>
              <Badge variant={obj.status === "completed" ? "success" : obj.status === "in_progress" ? "info" : "default"}>{obj.status}</Badge>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={obj.priority === "high" ? "error" : obj.priority === "medium" ? "warning" : "default"}>{obj.priority}</Badge>
              <div className="flex-1 bg-gray-700 rounded-full h-2">
                <div className="bg-indigo-500 h-2 rounded-full" style={{ width: `${obj.progress}%` }} />
              </div>
              <span className="text-sm text-gray-400">{obj.progress}%</span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
