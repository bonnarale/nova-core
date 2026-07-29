"use client";
import React, { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Spinner } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";
import { WorkflowCanvas } from "@/components/workflow";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface WorkflowStep {
  id?: string;
  name?: string;
  type?: string;
  step_type?: string;
  depends_on?: string[];
  handler?: string;
  [key: string]: unknown;
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  version: string;
  steps: WorkflowStep[];
  tags: string[];
}

interface StepExecution {
  step_id: string;
  step_name: string;
  step_type: string;
  status: string;
  error?: string;
  duration_ms?: number;
}

interface Execution {
  id: string;
  workflow_id: string;
  workflow_name: string;
  status: string;
  error?: string;
  current_step_id?: string;
  steps: StepExecution[];
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
}

interface WorkflowEvent {
  id: string;
  execution_id: string;
  event_type: string;
  step_id?: string;
  payload?: Record<string, unknown>;
  timestamp?: string;
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: "text-gray-400",
  RUNNING: "text-blue-400",
  COMPLETED: "text-green-400",
  FAILED: "text-red-400",
  CANCELLED: "text-yellow-400",
  PAUSED: "text-yellow-400",
};

const STATUS_BADGE: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
  PENDING: "default",
  RUNNING: "info",
  COMPLETED: "success",
  FAILED: "error",
  CANCELLED: "warning",
  PAUSED: "warning",
};

export default function WorkflowDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;
  const { data: workflow, loading, error } = useApi<Workflow>(`/api/v1/workflows/${id}`, [id]);

  const [executing, setExecuting] = useState(false);
  const [execution, setExecution] = useState<Execution | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [execError, setExecError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll events
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  const handleRun = useCallback(async () => {
    if (!workflow) return;
    setExecuting(true);
    setExecError(null);
    setExecution(null);
    setEvents([]);

    try {
      // 1. Create execution
      const createRes = await fetch(`${API_BASE}/api/v1/workflows/executions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow_id: workflow.id, input: {} }),
      });
      if (!createRes.ok) {
        const errData = await createRes.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${createRes.status}`);
      }
      const execData: Execution = await createRes.json();
      setExecution(execData);

      // 2. Start SSE stream BEFORE starting execution
      const es = new EventSource(`${API_BASE}/api/v1/workflows/executions/${execData.id}/stream`);
      eventSourceRef.current = es;

      es.onmessage = (e) => {
        try {
          const event: WorkflowEvent = JSON.parse(e.data);
          setEvents((prev) => [...prev, event]);
          // Update execution status from events
          if (event.event_type === "COMPLETED" || event.event_type === "FAILED" || event.event_type === "CANCELLED") {
            setExecution((prev) => prev ? { ...prev, status: event.event_type === "COMPLETED" ? "COMPLETED" : "FAILED" } : prev);
            setExecuting(false);
            es.close();
          }
        } catch {}
      };

      es.onerror = () => {
        // SSE disconnected — poll final state
        es.close();
        fetch(`${API_BASE}/api/v1/workflows/executions/${execData.id}`)
          .then((r) => r.json())
          .then((data: Execution) => {
            setExecution(data);
            setExecuting(false);
          })
          .catch(() => setExecuting(false));
      };

      // 3. Start execution in background
      const startRes = await fetch(`${API_BASE}/api/v1/workflows/executions/${execData.id}/start-async`, {
        method: "POST",
      });
      if (!startRes.ok) {
        const errData = await startRes.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${startRes.status}`);
      }
    } catch (err) {
      setExecError(err instanceof Error ? err.message : "Failed to start execution");
      setExecuting(false);
    }
  }, [workflow]);

  const handleCancel = useCallback(async () => {
    if (!execution) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/workflows/executions/${execution.id}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "cancel" }),
      });
      if (res.ok) {
        const data: Execution = await res.json();
        setExecution(data);
      }
    } catch {}
  }, [execution]);

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;
  if (error || !workflow) return <div className="text-center py-20 text-gray-500">Workflow not found{error ? `: ${error}` : ""}</div>;

  // Build canvas nodes/steps from workflow steps
  const canvasNodes = (workflow.steps || []).map((step, i) => ({
    id: step.id || `step-${i}`,
    type: step.step_type || step.type || "TASK",
    label: step.name || `Step ${i + 1}`,
    x: 40 + (i % 3) * 200,
    y: 40 + Math.floor(i / 3) * 100,
    status: execution?.steps?.find((s) => s.step_id === step.id)?.status?.toLowerCase(),
  }));

  const canvasEdges = (workflow.steps || []).flatMap((step) =>
    (step.depends_on || []).map((depId) => ({
      from: depId,
      to: step.id || "",
    }))
  );

  return (
    <div>
      <PageHeader
        title={workflow.name}
        description={workflow.description || "No description"}
        action={
          <div className="flex items-center gap-2">
            <Button
              variant={executing ? "danger" : "primary"}
              onClick={executing ? handleCancel : handleRun}
              loading={executing}
            >
              {executing ? "Cancel" : "Run Workflow"}
            </Button>
            <Button variant="ghost" onClick={() => router.push("/workflows")}>Back</Button>
          </div>
        }
      />

      {/* Metadata cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card>
          <span className="text-sm text-gray-400">Version</span>
          <div className="text-lg font-semibold text-gray-200 mt-1">{workflow.version}</div>
        </Card>
        <Card>
          <span className="text-sm text-gray-400">Steps</span>
          <div className="text-lg font-semibold text-gray-200 mt-1">{workflow.steps.length}</div>
        </Card>
        <Card>
          <span className="text-sm text-gray-400">Tags</span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {workflow.tags.length === 0 ? (
              <span className="text-sm text-gray-500">None</span>
            ) : (
              workflow.tags.map((t) => <Badge key={t}>{t}</Badge>)
            )}
          </div>
        </Card>
      </div>

      {/* Execution error */}
      {execError && (
        <Card className="mb-6 border-red-500/50">
          <div className="text-sm text-red-400">Error: {execError}</div>
        </Card>
      )}

      {/* Workflow Canvas */}
      {workflow.steps.length > 0 && (
        <Card title="Workflow Steps" className="mb-6">
          <WorkflowCanvas
            nodes={canvasNodes}
            edges={canvasEdges}
          />
        </Card>
      )}

      {/* Execution Status */}
      {execution && (
        <Card title={`Execution — ${execution.status}`} className="mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Execution ID</span>
              <div className="text-gray-200 font-mono text-xs mt-1 truncate">{execution.id}</div>
            </div>
            <div>
              <span className="text-gray-400">Status</span>
              <div className="mt-1"><Badge variant={STATUS_BADGE[execution.status] || "default"}>{execution.status}</Badge></div>
            </div>
            <div>
              <span className="text-gray-400">Duration</span>
              <div className="text-gray-200 mt-1">{execution.duration_ms ? `${execution.duration_ms.toFixed(0)}ms` : "—"}</div>
            </div>
            <div>
              <span className="text-gray-400">Steps completed</span>
              <div className="text-gray-200 mt-1">{execution.steps?.length || 0}</div>
            </div>
          </div>

          {/* Step progress */}
          {execution.steps && execution.steps.length > 0 && (
            <div className="mt-4 space-y-2">
              {execution.steps.map((step) => (
                <div key={step.step_id} className="flex items-center gap-3 p-2 bg-gray-900/50 rounded-lg text-sm">
                  <Badge variant={STATUS_BADGE[step.status] || "default"}>{step.status}</Badge>
                  <span className="text-gray-200">{step.step_name || step.step_id}</span>
                  <span className="text-gray-500 text-xs">({step.step_type})</span>
                  {step.duration_ms != null && step.duration_ms > 0 && (
                    <span className="text-gray-500 text-xs ml-auto">{step.duration_ms.toFixed(0)}ms</span>
                  )}
                  {step.error && <span className="text-red-400 text-xs ml-auto truncate max-w-[200px]">{step.error}</span>}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Real-time Events */}
      {events.length > 0 && (
        <Card title={`Events (${events.length})`} className="mb-6">
          <div className="max-h-[400px] overflow-y-auto space-y-1 font-mono text-xs">
            {events.map((event, i) => (
              <div key={event.id || i} className="flex items-start gap-2 py-1 border-b border-gray-700/30">
                <span className="text-gray-500 shrink-0">{event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : ""}</span>
                <Badge variant={STATUS_BADGE[event.event_type] || "default"}>{event.event_type}</Badge>
                {event.step_id && <span className="text-gray-400">step: {event.step_id}</span>}
                {event.payload && Object.keys(event.payload).length > 0 && (
                  <span className="text-gray-500 truncate">{JSON.stringify(event.payload)}</span>
                )}
              </div>
            ))}
            <div ref={eventsEndRef} />
          </div>
        </Card>
      )}

      {/* Steps list (static, from definition) */}
      {workflow.steps.length > 0 && !execution && (
        <Card title={`Steps (${workflow.steps.length})`}>
          <div className="space-y-2">
            {workflow.steps.map((step, i) => (
              <div key={step.id || i} className="p-3 bg-gray-900/50 rounded-lg text-sm text-gray-300">
                <div className="flex items-center gap-2">
                  <Badge>{i + 1}</Badge>
                  <span className="font-medium">{step.name || `Step ${i + 1}`}</span>
                  <span className="text-gray-500 text-xs">({step.step_type || step.type || "TASK"})</span>
                  {step.handler && <span className="text-gray-600 text-xs">handler: {step.handler}</span>}
                </div>
                {step.depends_on && step.depends_on.length > 0 && (
                  <div className="text-xs text-gray-600 mt-1">depends on: {step.depends_on.join(", ")}</div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
