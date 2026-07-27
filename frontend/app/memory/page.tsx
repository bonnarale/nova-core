"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, Spinner, StatusBadge } from "@/components/ui";
import { MetricCard } from "@/components/dashboard";
import { PageHeader } from "@/components/dashboard";

interface MemoryData {
  learning?: Record<string, unknown>;
  vector_memory?: Record<string, unknown>;
  knowledge_graph?: Record<string, unknown>;
  command_center_memory?: Record<string, unknown>;
}

export default function MemoryPage() {
  const [data, setData] = useState<MemoryData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/nova-web/memory`);
      if (res.ok) {
        setData(await res.json());
      }
    } catch {
      // keep previous
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;
  if (!data) return <div className="text-center py-20 text-gray-500">Unable to load memory status</div>;

  const learning = (data.learning || {}) as Record<string, unknown>;
  const vectorMem = (data.vector_memory || {}) as Record<string, unknown>;
  const kg = (data.knowledge_graph || {}) as Record<string, unknown>;
  const ccMemory = (data.command_center_memory || {}) as Record<string, unknown>;
  const activeObjectives = (ccMemory.active || {}) as Record<string, unknown>;

  return (
    <div>
      <PageHeader title="Memory" description="Monitor learning, vector memory, and knowledge graph" />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <MetricCard title="Improvements" value={(learning.total_improvements as number) || 0} icon="&#128218;" />
        <MetricCard title="Patterns" value={(learning.total_patterns as number) || 0} icon="&#128200;" />
        <MetricCard title="Metrics" value={(learning.total_metrics as number) || 0} icon="&#128202;" />
        <MetricCard title="Active Objectives" value={Object.keys(activeObjectives).length} icon="&#128279;" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Self-Improvement Engine">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Status</span>
              <StatusBadge status={learning.enabled ? "healthy" : "down"} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Total Improvements</span>
              <span className="text-sm text-gray-200">{(learning.total_improvements as number) || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Detected Patterns</span>
              <span className="text-sm text-gray-200">{(learning.total_patterns as number) || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Metrics Recorded</span>
              <span className="text-sm text-gray-200">{(learning.total_metrics as number) || 0}</span>
            </div>
            {Array.isArray(learning.categories) && (
              <div className="mt-2">
                <span className="text-xs text-gray-500">Categories:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {(learning.categories as string[]).map((cat) => (
                    <span key={cat} className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded">{cat}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>

        <Card title="Vector Memory">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Status</span>
              <StatusBadge status={vectorMem.status === "module_present" ? "healthy" : "unknown"} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Module</span>
              <span className="text-sm text-gray-200">{vectorMem.status === "module_present" ? "Available" : "Unavailable"}</span>
            </div>
          </div>
        </Card>

        <Card title="Knowledge Graph">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Status</span>
              <StatusBadge status={kg.status === "module_present" ? "healthy" : "unknown"} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Module</span>
              <span className="text-sm text-gray-200">{kg.status === "module_present" ? "Available" : "Unavailable"}</span>
            </div>
          </div>
        </Card>

        <Card title="Command Center Memory">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Active Objectives</span>
              <span className="text-sm text-gray-200">{Object.keys(activeObjectives).length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Backlog Items</span>
              <span className="text-sm text-gray-200">{Object.keys(ccMemory.backlog || {}).length}</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
