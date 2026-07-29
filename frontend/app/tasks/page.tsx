"use client";

import React, { useState, useEffect } from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Input, Spinner, StatusBadge } from "@/components/ui";
import { PageHeader, DataTable } from "@/components/dashboard";

interface Task {
  id: string;
  goal: string;
  status: string;
  assigned_agent?: string;
  created_at: string;
  updated_at: string;
}

interface Agent {
  id: string;
  name: string;
  role: string;
  description: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STATUS_COLUMNS = ["CREATED", "QUEUED", "RUNNING", "COMPLETED"];

function statusColor(s: string) {
  if (s === "COMPLETED") return "default";
  if (s === "RUNNING") return "info";
  if (s === "QUEUED") return "warning";
  return "default";
}

export default function TasksPage() {
  const { data: tasks, loading, refetch } = useApi<Task[]>("/api/v1/tasks");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [viewMode, setViewMode] = useState<"table" | "board">("table");
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newGoal, setNewGoal] = useState("");
  const [newAgent, setNewAgent] = useState("");
  const [creating, setCreating] = useState(false);

  // Fetch available agents
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/agents/available`)
      .then((r) => r.json())
      .then((data) => setAgents(Array.isArray(data) ? data : []))
      .catch(() => setAgents([]));
  }, []);

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  const tasksList = Array.isArray(tasks) ? tasks : [];
  const filtered = tasksList.filter((t) => !searchQuery || t.goal.toLowerCase().includes(searchQuery.toLowerCase()));

  async function handleCreate() {
    if (!newGoal.trim()) return;
    setCreating(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: newGoal.trim(), assigned_agent: newAgent || null }),
      });
      if (res.ok) {
        setNewGoal("");
        setNewAgent("");
        setShowCreate(false);
        refetch();
      }
    } finally {
      setCreating(false);
    }
  }

  function agentName(id: string | null | undefined): string {
    if (!id) return "Unassigned";
    const agent = agents.find((a) => a.id === id);
    return agent ? agent.name : id;
  }

  const columns = [
    { key: "goal", label: "Task" },
    { key: "status", label: "Status", render: (v: unknown) => <Badge variant={statusColor(v as string)}>{v as string}</Badge> },
    { key: "assigned_agent", label: "Agent", render: (v: unknown) => <span className="text-gray-400">{agentName(v as string)}</span> },
    { key: "created_at", label: "Created", render: (v: unknown) => <span className="text-gray-400">{new Date(v as string).toLocaleDateString()}</span> },
  ];

  return (
    <div>
      <PageHeader
        title="Tasks"
        description="Manage and track tasks across agents"
        action={
          <div className="flex gap-2">
            <Button variant={viewMode === "table" ? "primary" : "ghost"} size="sm" onClick={() => setViewMode("table")}>Table</Button>
            <Button variant={viewMode === "board" ? "primary" : "ghost"} size="sm" onClick={() => setViewMode("board")}>Board</Button>
            <Button onClick={() => setShowCreate(!showCreate)}>{showCreate ? "Cancel" : "Create Task"}</Button>
          </div>
        }
      />

      {showCreate && (
        <Card className="mb-6">
          <div className="space-y-3">
            <Input placeholder="Task goal (what needs to be done)" value={newGoal} onChange={(e) => setNewGoal(e.target.value)} />
            <div>
              <label className="block text-sm text-gray-400 mb-1">Assigned Agent</label>
              <select
                value={newAgent}
                onChange={(e) => setNewAgent(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">No agent (unassigned)</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name} — {agent.role}
                  </option>
                ))}
              </select>
              {newAgent && (
                <p className="text-xs text-gray-500 mt-1">
                  {agents.find((a) => a.id === newAgent)?.description || ""}
                </p>
              )}
            </div>
            <Button onClick={handleCreate} disabled={creating || !newGoal.trim()}>
              {creating ? "Creating..." : "Save Task"}
            </Button>
          </div>
        </Card>
      )}

      <Input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search tasks..." className="mb-4 max-w-sm" />
      {viewMode === "table" ? (
        <Card><DataTable columns={columns} data={filtered as unknown as Record<string, unknown>[]} /></Card>
      ) : (
        <div className="grid grid-cols-4 gap-4">
          {STATUS_COLUMNS.map((status) => (
            <div key={status}>
              <h3 className="text-sm font-medium text-gray-400 mb-3">{status}</h3>
              <div className="space-y-2">
                {filtered.filter((t) => t.status === status).map((t) => (
                  <Card key={t.id} className="p-3">
                    <div className="text-sm font-medium text-gray-300">{t.goal}</div>
                    <div className="flex items-center gap-2 mt-2">
                      {t.assigned_agent && (
                        <Badge variant="info">{agentName(t.assigned_agent)}</Badge>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
