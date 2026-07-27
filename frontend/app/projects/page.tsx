"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, Button, Badge, Input, Spinner, Modal, StatusBadge } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";
import { novaWeb, type Project } from "@/lib/nova-api";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<Project | null>(null);
  const [form, setForm] = useState({ name: "", description: "" });
  const [creating, setCreating] = useState(false);

  const fetchProjects = useCallback(async () => {
    try {
      const data = await novaWeb.projects();
      setProjects(data);
    } catch {
      // keep previous
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    setCreating(true);
    try {
      await novaWeb.createProject(form);
      setShowCreate(false);
      setForm({ name: "", description: "" });
      fetchProjects();
    } catch {
      // handle silently
    } finally {
      setCreating(false);
    }
  };

  const filtered = projects.filter((p) => filter === "all" || p.status === filter);

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader
        title="Projects"
        description="Manage and track projects"
        action={<Button onClick={() => setShowCreate(true)}>Create Project</Button>}
      />

      <div className="flex gap-2 mb-6">
        {["all", "active", "planning", "completed", "paused"].map((f) => (
          <Button key={f} size="sm" variant={filter === f ? "primary" : "ghost"} onClick={() => setFilter(f)}>
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </Button>
        ))}
      </div>

      {selected ? (
        <div>
          <Button size="sm" variant="ghost" onClick={() => setSelected(null)} className="mb-4">&larr; Back to list</Button>
          <Card>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-gray-200">{selected.name}</h2>
                <p className="text-sm text-gray-400 mt-1">{selected.description}</p>
              </div>
              <StatusBadge status={selected.status} />
            </div>

            <div className="flex items-center gap-3 mb-4">
              <div className="flex-1 bg-gray-700 rounded-full h-2.5">
                <div className="bg-green-500 h-2.5 rounded-full transition-all" style={{ width: `${selected.progress}%` }} />
              </div>
              <span className="text-sm text-gray-300">{selected.progress}%</span>
            </div>

            {selected.phases && selected.phases.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-medium text-gray-400 mb-3">Phases</h3>
                <div className="space-y-2">
                  {selected.phases.map((phase, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <StatusBadge status={phase.status} />
                      <span className="text-sm text-gray-300 flex-1">{phase.name}</span>
                      <div className="w-32 bg-gray-700 rounded-full h-1.5">
                        <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${phase.progress}%` }} />
                      </div>
                      <span className="text-xs text-gray-500">{phase.progress}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selected.milestones && selected.milestones.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-3">Milestones</h3>
                <div className="space-y-2">
                  {selected.milestones.map((m) => (
                    <div key={m.id} className="flex items-center justify-between bg-gray-900/50 rounded-lg p-3">
                      <div className="flex items-center gap-3">
                        <StatusBadge status={m.status} />
                        <span className="text-sm text-gray-300">{m.title}</span>
                      </div>
                      {m.due_date && <span className="text-xs text-gray-500">{new Date(m.due_date).toLocaleDateString()}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selected.tasks_count !== undefined && (
              <div className="mt-4 text-sm text-gray-400">
                Tasks: {selected.completed_tasks || 0} / {selected.tasks_count}
              </div>
            )}
          </Card>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.length === 0 ? (
            <Card>
              <div className="text-center py-8 text-gray-500">No projects found</div>
            </Card>
          ) : (
            filtered.map((project) => (
              <div key={project.id} className="cursor-pointer hover:bg-gray-800/70 transition-colors rounded-xl" onClick={() => setSelected(project)}>
                <Card>
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-200">{project.name}</h3>
                      <StatusBadge status={project.status} />
                      {project.phase && <Badge>{project.phase}</Badge>}
                    </div>
                    <p className="text-sm text-gray-400 mt-1 truncate">{project.description}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <div className="flex-1 bg-gray-700 rounded-full h-1.5 max-w-xs">
                        <div className="bg-green-500 h-1.5 rounded-full" style={{ width: `${project.progress}%` }} />
                      </div>
                      <span className="text-xs text-gray-500">{project.progress}%</span>
                    </div>
                  </div>
                </div>
                </Card>
              </div>
            ))
          )}
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Project">
        <div className="space-y-4">
          <Input label="Project Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Enter project name" />
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-gray-300">Description</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Enter project description"
              rows={3}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate} loading={creating}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
