"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, Button, Badge, Spinner, Input } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";
import { novaWeb, type Approval } from "@/lib/nova-api";

export default function ApprovalsPage() {
  const [pending, setPending] = useState<Approval[]>([]);
  const [history, setHistory] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"pending" | "history">("pending");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState<Record<string, string>>({});

  const fetchData = useCallback(async () => {
    try {
      const [p, h] = await Promise.all([novaWeb.approvals(), novaWeb.approvalHistory()]);
      setPending(p);
      setHistory(h);
    } catch {
      // keep previous
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleApprove = async (id: string) => {
    setActionLoading(id);
    try {
      await novaWeb.approve(id);
      fetchData();
    } catch {
      // handle silently
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (id: string) => {
    setActionLoading(id);
    try {
      await novaWeb.reject(id, rejectReason[id] || "Rejected");
      setRejectReason((prev) => { const n = { ...prev }; delete n[id]; return n; });
      fetchData();
    } catch {
      // handle silently
    } finally {
      setActionLoading(null);
    }
  };

  const items = view === "pending" ? pending : history;

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div>
      <PageHeader
        title="Approvals"
        description="Review and manage pending approvals"
        action={
          <div className="flex gap-2">
            <Badge variant={pending.length > 0 ? "warning" : "default"}>{pending.length} pending</Badge>
          </div>
        }
      />

      <div className="flex gap-2 mb-6">
        <Button size="sm" variant={view === "pending" ? "primary" : "ghost"} onClick={() => setView("pending")}>
          Pending ({pending.length})
        </Button>
        <Button size="sm" variant={view === "history" ? "primary" : "ghost"} onClick={() => setView("history")}>
          History ({history.length})
        </Button>
      </div>

      <div className="space-y-3">
        {items.length === 0 ? (
          <Card>
            <div className="text-center py-8 text-gray-500">
              {view === "pending" ? "No pending approvals" : "No approval history"}
            </div>
          </Card>
        ) : (
          items.map((appr) => (
            <Card key={appr.id}>
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-gray-200">{appr.title}</h3>
                    {appr.mandatory && <Badge variant="error">Mandatory</Badge>}
                    <Badge>{appr.category}</Badge>
                    <Badge variant={appr.priority === "high" ? "error" : appr.priority === "medium" ? "warning" : "default"}>
                      {appr.priority}
                    </Badge>
                  </div>
                  {appr.description && <p className="text-sm text-gray-400 mt-1">{appr.description}</p>}
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                    {appr.requested_by && <span>Requested by: {appr.requested_by}</span>}
                    <span>{new Date(appr.created_at).toLocaleString()}</span>
                    {view === "history" && (
                      <span className={`px-2 py-0.5 rounded-full text-xs ${
                        appr.status === "approved" ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400"
                      }`}>{appr.status}</span>
                    )}
                  </div>
                </div>
                {view === "pending" && (
                  <div className="flex flex-col gap-2 ml-4">
                    <Button size="sm" onClick={() => handleApprove(appr.id)} disabled={actionLoading === appr.id}>
                      Approve
                    </Button>
                    <div className="flex gap-1">
                      <Input
                        value={rejectReason[appr.id] || ""}
                        onChange={(e) => setRejectReason((prev) => ({ ...prev, [appr.id]: e.target.value }))}
                        placeholder="Reason..."
                        className="w-32 text-xs"
                      />
                      <Button size="sm" variant="danger" onClick={() => handleReject(appr.id)} disabled={actionLoading === appr.id}>
                        Reject
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
