"use client";
import React, { useState } from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Spinner, Input } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";
import Link from "next/link";
import { WorkflowCanvas } from "@/components/workflow";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface WorkflowStep {
  id?: string;
  name?: string;
  step_type?: string;
  depends_on?: string[];
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

function WorkflowMiniCanvas({ workflow }: { workflow: Workflow }) {
  const nodes = (workflow.steps || []).slice(0, 8).map((step, i) => ({
    id: step.id || `step-${i}`,
    type: step.step_type || "TASK",
    label: step.name || `Step ${i + 1}`,
    x: 20 + (i % 3) * 140,
    y: 20 + Math.floor(i / 3) * 70,
  }));

  const edges = (workflow.steps || []).slice(0, 8).flatMap((step) =>
    (step.depends_on || []).map((depId) => ({
      from: depId,
      to: step.id || "",
    }))
  );

  if (nodes.length === 0) {
    return (
      <div className="h-[120px] flex items-center justify-center text-gray-600 text-xs">
        No steps defined
      </div>
    );
  }

  return (
    <div className="scale-[0.65] origin-top-left" style={{ width: "154%", height: "154%" }}>
      <WorkflowCanvas nodes={nodes} edges={edges} />
    </div>
  );
}

export default function WorkflowsPage() {
  const { data: workflows, loading, refetch } = useApi<Workflow[]>("/api/v1/workflows");
  const [viewMode, setViewMode] = useState<"list" | "visual">("list");
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/workflows`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), description: description.trim() }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      setName("");
      setDescription("");
      setShowModal(false);
      refetch();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create workflow");
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader
        title="Workflows"
        description="Design and manage autonomous workflows"
        action={
          <div className="flex gap-2">
            <Button variant={viewMode === "list" ? "primary" : "ghost"} size="sm" onClick={() => setViewMode("list")}>List</Button>
            <Button variant={viewMode === "visual" ? "primary" : "ghost"} size="sm" onClick={() => setViewMode("visual")}>Visual</Button>
            <Button onClick={() => setShowModal(true)}>Create Workflow</Button>
          </div>
        }
      />

      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-200">Create Workflow</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-200">&#10005;</button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-gray-400 mb-1 block">Workflow Name</label>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Enter workflow name" />
              </div>
              <div>
                <label className="text-sm text-gray-400 mb-1 block">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Enter workflow description"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 min-h-[80px]"
                />
              </div>
              {createError && <p className="text-sm text-red-400">Error: {createError}</p>}
              <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={() => setShowModal(false)}>Cancel</Button>
                <Button onClick={handleCreate} disabled={creating || !name.trim()}>{creating ? "Creating..." : "Create"}</Button>
              </div>
            </div>
          </Card>
        </div>
      )}

      {viewMode === "list" ? (
        <div className="space-y-3">
          {(workflows || []).length === 0 && (
            <div className="text-center text-gray-500 py-12">No hay workflows todavía. Creá uno para empezar.</div>
          )}
          {(workflows || []).map((wf) => (
            <Card key={wf.id}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-200">{wf.name}</h3>
                    <Badge>v{wf.version}</Badge>
                  </div>
                  <p className="text-sm text-gray-400 mt-1">{wf.description}</p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge>{wf.steps.length} steps</Badge>
                  <Link href={`/workflows/${wf.id}`}><Button size="sm" variant="ghost">View</Button></Link>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {(workflows || []).length === 0 && (
            <div className="text-center text-gray-500 py-12">No hay workflows todav&iacute;a. Cre&aacute; uno para empezar.</div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(workflows || []).map((wf) => (
              <Link key={wf.id} href={`/workflows/${wf.id}`}>
                <Card className="cursor-pointer hover:border-indigo-500/50 transition-colors h-full">
                  <div className="mb-3">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-200">{wf.name}</h3>
                      <Badge>v{wf.version}</Badge>
                    </div>
                    <p className="text-xs text-gray-500 mt-1 line-clamp-1">{wf.description}</p>
                  </div>
                  <div className="overflow-hidden rounded-lg bg-gray-900/30 border border-gray-700/30">
                    <WorkflowMiniCanvas workflow={wf} />
                  </div>
                  <div className="flex items-center justify-between mt-3">
                    <Badge>{wf.steps.length} steps</Badge>
                    <span className="text-xs text-gray-500">{wf.tags.length > 0 ? wf.tags.join(", ") : "no tags"}</span>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
