"use client";
import React, { useState } from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Spinner, Input } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Workflow {
  id: string;
  name: string;
  description: string;
  version: string;
  steps: unknown[];
  tags: string[];
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
        <Card className="min-h-[600px] flex items-center justify-center">
          <div className="text-center text-gray-500">
            <div className="text-4xl mb-3">&#128295;</div>
            <p>Visual workflow builder - drag and drop nodes to design workflows</p>
          </div>
        </Card>
      )}
    </div>
  );
}
