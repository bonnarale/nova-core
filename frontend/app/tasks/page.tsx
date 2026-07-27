"use client";

import React, { useState } from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Input, Spinner, StatusBadge } from "@/components/ui";
import { PageHeader, DataTable } from "@/components/dashboard";

interface Task {
  id: string;
  title: string;
  status: string;
  priority: string;
  assigned_agent?: string;
  goal_id?: string;
  created_at: string;
  due_date?: string;
}

export default function TasksPage() {
  const { data: tasks, loading } = useApi<Task[]>("/api/v1/tasks");
  const [viewMode, setViewMode] = useState<"table" | "board">("table");
  const [searchQuery, setSearchQuery] = useState("");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  const filtered = (tasks || []).filter((t) => !searchQuery || t.title.toLowerCase().includes(searchQuery.toLowerCase()));

  const columns = [
    { key: "title", label: "Task" },
    { key: "status", label: "Status", render: (v: unknown) => <StatusBadge status={v as string} /> },
    { key: "priority", label: "Priority", render: (v: unknown) => <Badge variant={v === "high" ? "error" : v === "medium" ? "warning" : "default"}>{v as string}</Badge> },
    { key: "assigned_agent", label: "Agent", render: (v: unknown) => <span className="text-gray-400">{(v as string) || "Unassigned"}</span> },
    { key: "due_date", label: "Due", render: (v: unknown) => <span className="text-gray-400">{v ? new Date(v as string).toLocaleDateString() : "-"}</span> },
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
            <Button disabled title="Not yet implemented">Create Task</Button>
          </div>
        }
      />
      <Input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search tasks..." className="mb-4 max-w-sm" />
      {viewMode === "table" ? (
        <Card><DataTable columns={columns} data={filtered as unknown as Record<string, unknown>[]} /></Card>
      ) : (
        <div className="grid grid-cols-4 gap-4">
          {["pending", "in_progress", "review", "completed"].map((status) => (
            <div key={status}>
              <h3 className="text-sm font-medium text-gray-400 mb-3 capitalize">{status.replace("_", " ")}</h3>
              <div className="space-y-2">
                {filtered.filter((t) => t.status === status).map((t) => (
                  <Card key={t.id} className="p-3">
                    <div className="text-sm font-medium text-gray-300">{t.title}</div>
                    <div className="flex items-center gap-2 mt-2">
                      <Badge variant={t.priority === "high" ? "error" : "default"}>{t.priority}</Badge>
                      {t.assigned_agent && <span className="text-xs text-gray-500">{t.assigned_agent}</span>}
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
