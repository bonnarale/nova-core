"use client";
import React from "react";
import { useParams, useRouter } from "next/navigation";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Spinner } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface WorkflowStep {
  id?: string;
  name?: string;
  type?: string;
  [key: string]: unknown;
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  version: string;
  steps: WorkflowStep[];
  tags: string[];
}

export default function WorkflowDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;
  const { data: workflow, loading, error } = useApi<Workflow>(`/api/v1/workflows/${id}`, [id]);

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;
  if (error || !workflow) return <div className="text-center py-20 text-gray-500">Workflow not found{error ? `: ${error}` : ""}</div>;

  return (
    <div>
      <PageHeader
        title={workflow.name}
        description={workflow.description || "No description"}
        action={<Button variant="ghost" onClick={() => router.push("/workflows")}>Back to Workflows</Button>}
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card>
          <span className="text-sm text-gray-400">Version</span>
          <div className="text-lg font-semibold text-gray-200 mt-1">{workflow.version}</div>
        </Card>
        <Card>
          <span className="text-sm text-gray-400">Steps</span>
          <div className="text-lg font-semibold text-gray-200 mt-1">{workflow.steps.length}</div>
        </Card>
        <Card>
          <span className="text-sm text-gray-400">Tags</span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {workflow.tags.length === 0 ? (
              <span className="text-sm text-gray-500">None</span>
            ) : (
              workflow.tags.map((t) => <Badge key={t}>{t}</Badge>)
            )}
          </div>
        </Card>
      </div>

      <Card title={`Steps (${workflow.steps.length})`}>
        {workflow.steps.length === 0 ? (
          <div className="text-sm text-gray-500 py-4 text-center">This workflow has no steps defined yet.</div>
        ) : (
          <div className="space-y-2">
            {workflow.steps.map((step, i) => (
              <div key={step.id || i} className="p-3 bg-gray-900/50 rounded-lg text-sm text-gray-300">
                <div className="flex items-center gap-2">
                  <Badge>{i + 1}</Badge>
                  <span className="font-medium">{step.name || `Step ${i + 1}`}</span>
                  {step.type && <span className="text-gray-500 text-xs">({step.type})</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
