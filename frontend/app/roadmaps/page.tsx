"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, Button, Badge, Input, Spinner, Modal, StatusBadge } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";
import { novaWeb, type Roadmap } from "@/lib/nova-api";

export default function RoadmapsPage() {
  const [roadmaps, setRoadmaps] = useState<Roadmap[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<Roadmap | null>(null);
  const [form, setForm] = useState({ name: "", description: "", start_year: new Date().getFullYear(), end_year: new Date().getFullYear() + 1 });
  const [creating, setCreating] = useState(false);

  const fetchRoadmaps = useCallback(async () => {
    try {
      const data = await novaWeb.roadmaps();
      setRoadmaps(data);
    } catch {
      // keep previous
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchRoadmaps(); }, [fetchRoadmaps]);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    setCreating(true);
    try {
      await novaWeb.createRoadmap(form);
      setShowCreate(false);
      setForm({ name: "", description: "", start_year: new Date().getFullYear(), end_year: new Date().getFullYear() + 1 });
      fetchRoadmaps();
    } catch {
      // handle silently
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader
        title="Roadmaps"
        description="Plan and visualize multi-year roadmaps"
        action={<Button onClick={() => setShowCreate(true)}>Create Roadmap</Button>}
      />

      {selected ? (
        <div>
          <Button size="sm" variant="ghost" onClick={() => setSelected(null)} className="mb-4">&larr; Back to list</Button>
          <Card>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-gray-200">{selected.name}</h2>
                <p className="text-sm text-gray-400 mt-1">{selected.description}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge>{selected.start_year} - {selected.end_year}</Badge>
                <StatusBadge status={selected.status} />
              </div>
            </div>

            {selected.phases && selected.phases.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-medium text-gray-400 mb-4">Timeline</h3>
                <div className="relative">
                  <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-700" />
                  <div className="space-y-4">
                    {selected.phases.map((phase) => (
                      <div key={phase.id} className="relative pl-10">
                        <div className={`absolute left-2.5 top-1 w-3 h-3 rounded-full border-2 ${
                          phase.status === "completed" ? "bg-green-500 border-green-500" :
                          phase.status === "active" ? "bg-indigo-500 border-indigo-500" :
                          "bg-gray-700 border-gray-600"
                        }`} />
                        <div className="bg-gray-900/50 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium text-gray-200">{phase.name}</span>
                            <StatusBadge status={phase.status} />
                          </div>
                          <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                            <span>{new Date(phase.start_date).toLocaleDateString()}</span>
                            <span>&rarr;</span>
                            <span>{new Date(phase.end_date).toLocaleDateString()}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-gray-700 rounded-full h-1.5">
                              <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${phase.progress}%` }} />
                            </div>
                            <span className="text-xs text-gray-500">{phase.progress}%</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </Card>
        </div>
      ) : (
        <div className="space-y-3">
          {roadmaps.length === 0 ? (
            <Card>
              <div className="text-center py-8 text-gray-500">No roadmaps found. Create one to get started.</div>
            </Card>
          ) : (
            roadmaps.map((rm) => (
              <div key={rm.id} className="cursor-pointer hover:bg-gray-800/70 transition-colors rounded-xl" onClick={() => setSelected(rm)}>
                <Card>
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-200">{rm.name}</h3>
                      <StatusBadge status={rm.status} />
                    </div>
                    <p className="text-sm text-gray-400 mt-1">{rm.description}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                      <Badge>{rm.start_year} - {rm.end_year}</Badge>
                      <span>{rm.phases.length} phases</span>
                    </div>
                  </div>
                </div>
              </Card>
              </div>
            ))
          )}
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Roadmap">
        <div className="space-y-4">
          <Input label="Roadmap Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Enter roadmap name" />
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-gray-300">Description</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Enter roadmap description"
              rows={3}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Start Year" type="number" value={form.start_year} onChange={(e) => setForm({ ...form, start_year: parseInt(e.target.value) || new Date().getFullYear() })} />
            <Input label="End Year" type="number" value={form.end_year} onChange={(e) => setForm({ ...form, end_year: parseInt(e.target.value) || new Date().getFullYear() + 1 })} />
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
