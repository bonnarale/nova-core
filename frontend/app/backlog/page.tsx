"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, Button, Badge, Input, Spinner, Modal } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";
import { novaWeb, type BacklogItem } from "@/lib/nova-api";

export default function BacklogPage() {
  const [items, setItems] = useState<BacklogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [sortBy, setSortBy] = useState<"priority" | "created">("priority");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", priority: "medium", category: "general" });
  const [creating, setCreating] = useState(false);

  const fetchItems = useCallback(async () => {
    try {
      const data = await novaWeb.backlog();
      setItems(data);
    } catch {
      // keep previous
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const handleCreate = async () => {
    if (!form.title.trim()) return;
    setCreating(true);
    try {
      await novaWeb.createBacklogItem(form);
      setShowCreate(false);
      setForm({ title: "", description: "", priority: "medium", category: "general" });
      fetchItems();
    } catch {
      // handle silently
    } finally {
      setCreating(false);
    }
  };

  const priorityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

  const filtered = items
    .filter((i) => filter === "all" || i.status === filter)
    .filter((i) => categoryFilter === "all" || i.category === categoryFilter)
    .sort((a, b) => {
      if (sortBy === "priority") return (priorityOrder[a.priority] ?? 4) - (priorityOrder[b.priority] ?? 4);
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

  const categories = [...new Set(items.map((i) => i.category))];
  const statuses = [...new Set(items.map((i) => i.status))];

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader
        title="Backlog"
        description="Manage and prioritize backlog items"
        action={<Button onClick={() => setShowCreate(true)}>Add Item</Button>}
      />

      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex gap-2">
          <span className="text-sm text-gray-400 self-center">Status:</span>
          {["all", ...statuses].map((f) => (
            <Button key={f} size="sm" variant={filter === f ? "primary" : "ghost"} onClick={() => setFilter(f)}>
              {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
            </Button>
          ))}
        </div>
        <div className="flex gap-2">
          <span className="text-sm text-gray-400 self-center">Category:</span>
          {["all", ...categories].map((c) => (
            <Button key={c} size="sm" variant={categoryFilter === c ? "primary" : "ghost"} onClick={() => setCategoryFilter(c)}>
              {c === "all" ? "All" : c.charAt(0).toUpperCase() + c.slice(1)}
            </Button>
          ))}
        </div>
        <div className="flex gap-2">
          <span className="text-sm text-gray-400 self-center">Sort:</span>
          <Button size="sm" variant={sortBy === "priority" ? "primary" : "ghost"} onClick={() => setSortBy("priority")}>Priority</Button>
          <Button size="sm" variant={sortBy === "created" ? "primary" : "ghost"} onClick={() => setSortBy("created")}>Newest</Button>
        </div>
      </div>

      <div className="space-y-2">
        {filtered.length === 0 ? (
          <Card>
            <div className="text-center py-8 text-gray-500">No backlog items found</div>
          </Card>
        ) : (
          filtered.map((item) => (
            <Card key={item.id}>
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium text-gray-200 text-sm">{item.title}</h3>
                    <Badge variant={item.priority === "critical" || item.priority === "high" ? "error" : item.priority === "medium" ? "warning" : "default"}>
                      {item.priority}
                    </Badge>
                    <Badge>{item.category}</Badge>
                  </div>
                  {item.description && <p className="text-xs text-gray-400 mt-1 truncate">{item.description}</p>}
                </div>
                <div className="flex items-center gap-3 ml-4">
                  {item.estimated_effort && <span className="text-xs text-gray-500">{item.estimated_effort}</span>}
                  <span className="text-xs text-gray-500">{new Date(item.created_at).toLocaleDateString()}</span>
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                    item.status === "approved" ? "bg-green-900/50 text-green-400" :
                    item.status === "pending" ? "bg-yellow-900/50 text-yellow-400" :
                    item.status === "rejected" ? "bg-red-900/50 text-red-400" :
                    "bg-gray-700 text-gray-300"
                  }`}>{item.status}</span>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Add Backlog Item">
        <div className="space-y-4">
          <Input label="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Enter item title" />
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-gray-300">Description</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Enter description"
              rows={3}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-300">Priority</label>
              <select
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-gray-300">Category</label>
              <input
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                placeholder="e.g., feature, bug, infra"
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate} loading={creating}>Add Item</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
