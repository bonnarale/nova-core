"use client";
import React, { useState, useEffect } from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Spinner, Input } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";
import { useAppStore } from "@/stores";

interface Goal {
  id: string;
  title: string;
  description: string | null;
  status: string;
  priority: number;
  progress: number;
}

const FILTERS = [
  { key: "all", label: "All" },
  { key: "active", label: "Active" },
  { key: "completed", label: "Completed" },
  { key: "blocked", label: "Blocked" },
];

function priorityVariant(priority: number): "error" | "warning" | "default" {
  if (priority >= 4) return "error";
  if (priority === 3) return "warning";
  return "default";
}

function priorityLabel(priority: number): string {
  if (priority >= 4) return "High";
  if (priority === 3) return "Medium";
  return "Low";
}

export default function GoalsPage() {
  const { user } = useAppStore();
  const effectiveUserId = user?.user_id;

  const { data: goals, loading, error, refetch } = useApi<Goal[]>(
    effectiveUserId ? `/api/v1/goals/${effectiveUserId}` : "",
    [effectiveUserId]
  );
  const [filter, setFilter] = useState("all");
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newPriority, setNewPriority] = useState(3);
  const [creating, setCreating] = useState(false);

  const goalsList = Array.isArray(goals) ? goals : [];
  const filtered = goalsList.filter((g) => filter === "all" || g.status === filter);

  async function handleCreate() {
    if (!newTitle.trim() || !effectiveUserId) return;
    setCreating(true);
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_BASE}/api/v1/goals/${effectiveUserId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle.trim(), description: newDesc.trim() || null, priority: newPriority }),
      });
      if (res.ok) {
        setNewTitle("");
        setNewDesc("");
        setNewPriority(3);
        setShowCreate(false);
        refetch();
      }
    } finally {
      setCreating(false);
    }
  }

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader
        title="Goals"
        description="Track and manage strategic objectives"
        action={<Button onClick={() => setShowCreate(!showCreate)}>{showCreate ? "Cancel" : "Create Goal"}</Button>}
      />

      {showCreate && (
        <Card className="mb-6">
          <div className="space-y-3">
            <Input placeholder="Goal title" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
            <Input placeholder="Description (optional)" value={newDesc} onChange={(e) => setNewDesc(e.target.value)} />
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-400">Priority:</span>
              {[1, 2, 3, 4, 5].map((p) => (
                <Button key={p} size="sm" variant={newPriority === p ? "primary" : "ghost"} onClick={() => setNewPriority(p)}>
                  {p}
                </Button>
              ))}
            </div>
            <Button onClick={handleCreate} disabled={creating || !newTitle.trim()}>
              {creating ? "Creating..." : "Save Goal"}
            </Button>
          </div>
        </Card>
      )}

      <div className="flex gap-2 mb-6">
        {FILTERS.map((f) => (
          <Button key={f.key} size="sm" variant={filter === f.key ? "primary" : "ghost"} onClick={() => setFilter(f.key)}>{f.label}</Button>
        ))}
      </div>

      {error && (
        <Card className="mb-4 border-red-800/50">
          <p className="text-sm text-red-400">Error loading goals: {error}</p>
        </Card>
      )}

      {filtered.length === 0 && !error && (
        <div className="text-center text-gray-500 py-12">
          {goalsList.length === 0
            ? "No goals yet. Create one to start tracking your objectives."
            : "No goals match the selected filter."}
        </div>
      )}

      <div className="space-y-4">
        {filtered.map((goal) => (
          <Card key={goal.id}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-gray-200">{goal.title}</h3>
                  <Badge variant={priorityVariant(goal.priority)}>{priorityLabel(goal.priority)}</Badge>
                  <Badge variant="default">{goal.status}</Badge>
                </div>
                {goal.description && <p className="text-sm text-gray-400 mb-3">{goal.description}</p>}
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-gray-700 rounded-full h-2">
                    <div className="bg-indigo-500 h-2 rounded-full" style={{ width: `${goal.progress}%` }} />
                  </div>
                  <span className="text-sm text-gray-400">{goal.progress}%</span>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
