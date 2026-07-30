"use client";

import React from "react";
import { Card, Badge, Spinner } from "@/components/ui";
import type { ActivityEntry } from "@/lib/nova-api";

interface ActivityCardProps {
  entries: ActivityEntry[];
  loading?: boolean;
}

function formatTimestamp(iso: string): string {
  if (!iso) return "";
  try {
    const date = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch {
    return iso;
  }
}

function getStatusVariant(status: string): "success" | "warning" | "error" | "info" | "default" {
  switch (status.toLowerCase()) {
    case "executed":
    case "completed":
      return "success";
    case "pending_approval":
    case "pending":
      return "warning";
    case "failed":
    case "blocked":
      return "error";
    case "skipped":
      return "info";
    default:
      return "default";
  }
}

function getActionLabel(action: string): string {
  switch (action.toLowerCase()) {
    case "reviewed":
      return "Reviewed";
    case "executed":
      return "Executed";
    case "skipped":
      return "Skipped";
    case "blocked":
      return "Blocked";
    case "failed":
      return "Failed";
    default:
      return action;
  }
}

export function ActivityCard({ entries, loading = false }: ActivityCardProps) {
  if (loading) {
    return (
      <Card title="Recent Activity">
        <div className="flex items-center justify-center py-8">
          <Spinner size="md" />
        </div>
      </Card>
    );
  }

  if (entries.length === 0) {
    return (
      <Card title="Recent Activity">
        <div className="text-center py-8">
          <div className="w-12 h-12 bg-gray-700/50 rounded-xl flex items-center justify-center mx-auto mb-3">
            <span className="text-2xl text-gray-500">&#9776;</span>
          </div>
          <p className="text-sm text-gray-500">No recent activity</p>
          <p className="text-xs text-gray-600 mt-1">Activity will appear here when autonomous actions are performed</p>
        </div>
      </Card>
    );
  }

  return (
    <Card title={`Recent Activity (${entries.length})`}>
      <div className="space-y-2">
        {entries.slice(0, 5).map((entry) => (
          <div key={entry.id} className="flex items-center justify-between bg-gray-900/50 rounded-lg p-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-300 font-medium truncate">
                  {entry.goal_title || "Unknown Goal"}
                </span>
                <Badge variant={getStatusVariant(entry.status)}>
                  {entry.status}
                </Badge>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-gray-500">{getActionLabel(entry.action)}</span>
                {entry.reason && (
                  <>
                    <span className="text-xs text-gray-600">&middot;</span>
                    <span className="text-xs text-gray-500 truncate">{entry.reason}</span>
                  </>
                )}
              </div>
            </div>
            <span className="text-xs text-gray-500 ml-3 whitespace-nowrap">
              {formatTimestamp(entry.created_at)}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
