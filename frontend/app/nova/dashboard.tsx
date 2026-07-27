"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, Badge, StatusBadge, Spinner } from "@/components/ui";
import { MetricCard } from "@/components/dashboard";
import { novaWeb, type NovaDashboardData } from "@/lib/nova-api";

export function NovaDashboard({ refreshKey }: { refreshKey?: number }) {
  const [data, setData] = useState<NovaDashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const dash = await novaWeb.dashboard();
      setData(dash);
    } catch {
      // keep previous data
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData, refreshKey]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Unable to load dashboard data
      </div>
    );
  }

  const objectives = data.objectives?.items || [];
  const projects = data.projects?.items || [];
  const approvals = data.approvals?.items || [];
  const recommendations = data.recommendations?.items || [];
  const backlogCount = data.backlog?.count || 0;
  const lifecycle = data.lifecycle || {};
  const statusPhase = String(lifecycle.phase || "unknown");

  return (
    <div className="space-y-4 overflow-y-auto h-full p-4">
      <div className="grid grid-cols-2 gap-3">
        <MetricCard title="Objectives" value={objectives.length} icon="&#9733;" />
        <MetricCard title="Projects" value={projects.length} icon="&#9783;" />
        <MetricCard title="Backlog" value={backlogCount} icon="&#9776;" />
        <MetricCard title="Approvals" value={approvals.length} icon="&#9745;" />
      </div>

      <Card title="System Status">
        <div className="flex items-center gap-3">
          <StatusBadge status={statusPhase === "running" ? "healthy" : statusPhase} />
          <span className="text-xs text-gray-400">
            Phase: {statusPhase}
          </span>
        </div>
      </Card>

      {objectives.length > 0 && (
        <Card title={`Active Objectives (${objectives.length})`}>
          <div className="space-y-2">
            {objectives.slice(0, 4).map((obj) => (
              <div key={obj.id} className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-gray-300 truncate">{obj.title}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 bg-gray-700 rounded-full h-1.5">
                      <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${(obj.progress || 0) * 100}%` }} />
                    </div>
                    <span className="text-xs text-gray-500">{Math.round((obj.progress || 0) * 100)}%</span>
                  </div>
                </div>
                <Badge variant={obj.priority <= 1 ? "error" : obj.priority <= 2 ? "warning" : "default"}>
                  {obj.category}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

      {projects.length > 0 && (
        <Card title={`Active Projects (${projects.length})`}>
          <div className="space-y-2">
            {projects.slice(0, 4).map((proj) => (
              <div key={proj.id} className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-gray-300 truncate">{proj.name}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 bg-gray-700 rounded-full h-1.5">
                      <div className="bg-green-500 h-1.5 rounded-full" style={{ width: `${(proj.progress || 0) * 100}%` }} />
                    </div>
                    <span className="text-xs text-gray-500">{Math.round((proj.progress || 0) * 100)}%</span>
                  </div>
                </div>
                <Badge>{proj.status}</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

      {approvals.length > 0 && (
        <Card title={`Pending Approvals (${approvals.length})`}>
          <div className="space-y-3">
            {approvals.slice(0, 3).map((appr) => (
              <div key={appr.id} className="bg-gray-900/50 rounded-lg p-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-300 font-medium">{appr.description || appr.action_type}</span>
                      {appr.risk_level === "critical" && <Badge variant="error">Critical</Badge>}
                    </div>
                    <span className="text-xs text-gray-500">{appr.action_type} &middot; {appr.risk_level}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {recommendations.length > 0 && (
        <Card title={`Recommendations (${recommendations.length})`}>
          <div className="space-y-2">
            {recommendations.slice(0, 3).map((rec) => (
              <div key={rec.id} className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-gray-300 truncate">{rec.title}</div>
                  <span className="text-xs text-gray-500">{rec.category}</span>
                </div>
                <Badge variant={rec.priority === "high" ? "error" : rec.priority === "medium" ? "warning" : "info"}>
                  {rec.priority}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

      {objectives.length === 0 && projects.length === 0 && approvals.length === 0 && (
        <Card>
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-indigo-600/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl text-indigo-400">N</span>
            </div>
            <h3 className="text-lg font-semibold text-gray-200 mb-2">Welcome to NOVA</h3>
            <p className="text-sm text-gray-400 max-w-md mx-auto">
              Start by telling NOVA what you want to build, create, or learn.
              NOVA will analyze your objective and create a plan.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
