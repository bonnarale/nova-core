"use client";

import React, { useEffect, useState } from "react";
import { useApi } from "@/hooks";
import { Card, Button, Badge, StatusBadge, Spinner } from "@/components/ui";
import { PageHeader, DataTable } from "@/components/dashboard";

interface Agent {
  id: string;
  name: string;
  role: string;
  status: string;
  capabilities: string[];
  created_at: string;
}

export default function AgentsPage() {
  const { data: agents, loading, error } = useApi<Agent[]>("/api/v1/agents");

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;
  if (error) return <div className="text-center py-20 text-red-400">Error: {error}</div>;

  return (
    <div>
      <PageHeader title="Agents" description="Manage autonomous AI agents" action={<Button>Create Agent</Button>} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(agents || []).map((agent) => (
          <Card key={agent.id}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-200">{agent.name}</h3>
              <StatusBadge status={agent.status} />
            </div>
            <p className="text-sm text-gray-400 mb-3">{agent.role}</p>
            <div className="flex flex-wrap gap-1.5 mb-4">
              {agent.capabilities.map((cap) => <Badge key={cap} variant="info">{cap}</Badge>)}
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="secondary">Activate</Button>
              <Button size="sm" variant="ghost">Configure</Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
