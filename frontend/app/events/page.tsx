"use client";

import React, { useState } from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, Input, Spinner } from "@/components/ui";
import { PageHeader } from "@/components/dashboard";

interface Event {
  id: string;
  type: string;
  source: string;
  message: string;
  severity: string;
  timestamp: string;
}

export default function EventsPage() {
  const { data: events, loading } = useApi<Event[]>("/api/v1/events");
  const [filter, setFilter] = useState("all");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  const filtered = (events || []).filter((e) => filter === "all" || e.severity === filter);

  return (
    <div>
      <PageHeader title="Events" description="Real-time system events" action={<Button variant="ghost">Export</Button>} />
      <div className="flex gap-2 mb-4">
        {["all", "info", "warning", "error", "critical"].map((f) => (
          <Button key={f} size="sm" variant={filter === f ? "primary" : "ghost"} onClick={() => setFilter(f)}>{f.charAt(0).toUpperCase() + f.slice(1)}</Button>
        ))}
      </div>
      <div className="space-y-2">
        {filtered.map((event) => (
          <Card key={event.id} className="p-3">
            <div className="flex items-center gap-3">
              <Badge variant={event.severity === "critical" ? "error" : event.severity === "error" ? "error" : event.severity === "warning" ? "warning" : "info"}>
                {event.severity}
              </Badge>
              <span className="text-sm font-medium text-gray-300">{event.type}</span>
              <span className="text-sm text-gray-400 flex-1">{event.message}</span>
              <Badge>{event.source}</Badge>
              <span className="text-xs text-gray-500">{new Date(event.timestamp).toLocaleTimeString()}</span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
