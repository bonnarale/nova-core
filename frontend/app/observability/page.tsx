"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, Spinner, StatusBadge, Button } from "@/components/ui";
import { MetricCard, PageHeader } from "@/components/dashboard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface TimelineEntry {
  id: string;
  action: string;
  status: string;
  reason: string | null;
  tool_name: string | null;
  duration_ms: number | null;
  session_id: string | null;
  goal_title: string | null;
  created_at: string;
}

interface ToolMetrics {
  period_hours: number;
  tools: Record<string, {
    executions: number;
    successes: number;
    failures: number;
    success_rate: number;
    avg_duration_ms: number;
    last_used: string | null;
  }>;
  total_executions: number;
}

const STATUS_ICONS: Record<string, string> = {
  success: "✅",
  failed: "❌",
  skipped: "⏭️",
  blocked: "🚫",
  pending_approval: "⏳",
  tool_executed: "🔧",
};

const ACTION_LABELS: Record<string, string> = {
  tool_executed: "Tool ejecutada",
  reviewed: "Revisado",
  executed: "Ejecutado",
  skipped: "Omitido",
  failed: "Falló",
};

function formatTime(iso: string): string {
  try { return new Date(iso).toLocaleTimeString(); } catch { return ""; }
}

function formatDuration(ms: number | null): string {
  if (!ms) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function ObservabilityPage() {
  const [activeTab, setActiveTab] = useState<"overview" | "timeline" | "tools" | "decisions">("overview");
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [toolMetrics, setToolMetrics] = useState<ToolMetrics | null>(null);
  const [decisions, setDecisions] = useState<TimelineEntry[]>([]);
  const [loadingTimeline, setLoadingTimeline] = useState(false);
  const [loadingMetrics, setLoadingMetrics] = useState(false);
  const [loadingDecisions, setLoadingDecisions] = useState(false);

  const fetchTimeline = useCallback(async () => {
    setLoadingTimeline(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/observability/timeline?limit=50`);
      if (res.ok) { const d = await res.json(); setTimeline(d.entries || []); }
    } catch {} finally { setLoadingTimeline(false); }
  }, []);

  const fetchToolMetrics = useCallback(async () => {
    setLoadingMetrics(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/observability/tool-metrics?hours=24`);
      if (res.ok) setToolMetrics(await res.json());
    } catch {} finally { setLoadingMetrics(false); }
  }, []);

  const fetchDecisions = useCallback(async () => {
    setLoadingDecisions(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/observability/decisions?limit=50`);
      if (res.ok) { const d = await res.json(); setDecisions(d.entries || []); }
    } catch {} finally { setLoadingDecisions(false); }
  }, []);

  useEffect(() => {
    if (activeTab === "timeline") fetchTimeline();
    if (activeTab === "tools") fetchToolMetrics();
    if (activeTab === "decisions") fetchDecisions();
  }, [activeTab, fetchTimeline, fetchToolMetrics, fetchDecisions]);

  return (
    <div>
      <PageHeader title="Observability" description="Auditoría, trazabilidad y métricas de NOVA" />

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {[
          { key: "overview", label: "Overview" },
          { key: "timeline", label: "Timeline" },
          { key: "tools", label: "Tool Metrics" },
          { key: "decisions", label: "Decisiones" },
        ].map((t) => (
          <Button key={t.key} size="sm" variant={activeTab === t.key ? "primary" : "ghost"} onClick={() => setActiveTab(t.key as typeof activeTab)}>
            {t.label}
          </Button>
        ))}
      </div>

      {/* ── Overview Tab ─────────────────────────────────── */}
      {activeTab === "overview" && (
        <Card>
          <div className="text-center py-8 text-gray-500">
            <p>Select a tab above to view audit data.</p>
            <p className="text-xs mt-2">Timeline shows all NOVA actions chronologically.</p>
          </div>
        </Card>
      )}

      {/* ── Timeline Tab ─────────────────────────────────── */}
      {activeTab === "timeline" && (
        <Card title="Flujo de Decisión — Qué hizo NOVA y por qué">
          {loadingTimeline ? (
            <div className="flex justify-center py-8"><Spinner size="md" /></div>
          ) : timeline.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No activity recorded yet. Make a chat request to generate entries.</div>
          ) : (
            <div className="space-y-1">
              {timeline.map((entry) => {
                const icon = STATUS_ICONS[entry.status] || "📋";
                const actionLabel = ACTION_LABELS[entry.action] || entry.action;
                return (
                  <div key={entry.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-800/50 transition-colors">
                    <span className="text-lg mt-0.5">{icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500 font-mono">{formatTime(entry.created_at)}</span>
                        <span className="text-sm font-medium text-gray-200">{actionLabel}</span>
                        {entry.tool_name && (
                          <span className="px-1.5 py-0.5 bg-indigo-900/50 text-indigo-300 rounded text-xs">{entry.tool_name}</span>
                        )}
                        {entry.duration_ms != null && (
                          <span className="text-xs text-gray-500">{formatDuration(entry.duration_ms)}</span>
                        )}
                      </div>
                      {entry.reason && (
                        <p className="text-xs text-gray-400 mt-1 italic">&ldquo;{entry.reason}&rdquo;</p>
                      )}
                      {entry.goal_title && (
                        <p className="text-xs text-gray-500 mt-0.5">Goal: {entry.goal_title}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      )}

      {/* ── Tool Metrics Tab ──────────────────────────────── */}
      {activeTab === "tools" && (
        <Card title="Métricas de Herramientas — Últimas 24h">
          {loadingMetrics ? (
            <div className="flex justify-center py-8"><Spinner size="md" /></div>
          ) : !toolMetrics || Object.keys(toolMetrics.tools).length === 0 ? (
            <div className="text-center py-8 text-gray-500">No tool executions recorded yet.</div>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-900/50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-gray-200">{toolMetrics.total_executions}</div>
                  <div className="text-xs text-gray-500">Total Executions</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-400">{Object.keys(toolMetrics.tools).length}</div>
                  <div className="text-xs text-gray-500">Tools Used</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-gray-200">{toolMetrics.period_hours}h</div>
                  <div className="text-xs text-gray-500">Period</div>
                </div>
              </div>
              <div className="space-y-3">
                {Object.entries(toolMetrics.tools).map(([name, m]) => (
                  <div key={name} className="flex items-center gap-4 bg-gray-900/50 rounded-lg p-3">
                    <span className="text-sm font-medium text-gray-200 w-40 truncate">{name}</span>
                    <div className="flex-1 flex items-center gap-4">
                      <div className="text-xs text-gray-400">{m.executions} runs</div>
                      <div className="flex-1 bg-gray-700 rounded-full h-2">
                        <div className="bg-green-500 h-2 rounded-full" style={{ width: `${m.success_rate}%` }} />
                      </div>
                      <div className="text-xs text-gray-400 w-12 text-right">{m.success_rate}%</div>
                      <div className="text-xs text-gray-500 w-16 text-right">~{formatDuration(m.avg_duration_ms)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>
      )}

      {/* ── Decisions Tab ─────────────────────────────────── */}
      {activeTab === "decisions" && (
        <Card title="Decisiones del CognitiveEngine — Razonamiento de NOVA">
          {loadingDecisions ? (
            <div className="flex justify-center py-8"><Spinner size="md" /></div>
          ) : decisions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No decisions recorded yet.</div>
          ) : (
            <div className="space-y-3">
              {decisions.map((d) => (
                <div key={d.id} className="bg-gray-900/50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs text-gray-500 font-mono">{formatTime(d.created_at)}</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      d.status === "success" ? "bg-green-900/50 text-green-300" :
                      d.status === "failed" ? "bg-red-900/50 text-red-300" :
                      "bg-gray-700 text-gray-300"
                    }`}>{d.status}</span>
                    {d.tool_name && <span className="px-1.5 py-0.5 bg-indigo-900/50 text-indigo-300 rounded text-xs">{d.tool_name}</span>}
                    {d.duration_ms != null && <span className="text-xs text-gray-500">{formatDuration(d.duration_ms)}</span>}
                  </div>
                  {d.reason && (
                    <p className="text-sm text-gray-300 italic">&ldquo;{d.reason}&rdquo;</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
